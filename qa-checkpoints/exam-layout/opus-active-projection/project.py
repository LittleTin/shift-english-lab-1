#!/usr/bin/env python3
"""Build an active-only proof/Opus site; source inputs are read-only."""
import argparse,copy,concurrent.futures,hashlib,html,json,mimetypes,os,re,shutil,struct,subprocess
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
import numpy as np
RATE=48000; MIME='audio/ogg'; HISTORY=('previousListeningPlan','alternateListeningPlans','legacyQuestions')
RAW={'.mp3','.wav','.ogg','.m4a','.opus','.webm','.flac'}
SAFE=re.compile(r'^(audio|assets)/[A-Za-z0-9_./-]+$')
def jd(b):return json.loads(b)
def dig(b):return hashlib.sha256(b).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def canon(x):return dig(json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False,sort_keys=True).encode())
def wr(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def cmd(*a,data=None):return subprocess.check_output(a,input=data)
def probe(f):return jd(cmd('ffprobe','-v','error','-show_format','-show_streams','-of','json',str(f)))
def dec(f):return cmd('ffmpeg','-nostdin','-v','error','-i',str(f),'-map','0:a:0','-ar',str(RATE),'-c:a','pcm_s16le','-f','s16le','-')
def require(ok,*reason):
 if not ok:raise ValueError(reason)
def safe(rel):
 require(SAFE.fullmatch(rel) and '..' not in Path(rel).parts,rel)
 return rel
def canonical_path(roots,rel):
 safe(rel)
 files=[r/rel for r in roots if (r/rel).is_file()]
 require(files,rel)
 require(not any(dig(f.read_bytes())!=dig(files[0].read_bytes()) for f in files[1:]),'same relative path resolves to different bytes',rel)
 return files[0]
def opus_geometry(b):
 at=0;prev=None;stride=None;seq=0;end=None;skip=None
 while at<len(b):
  require(b[at:at+4]==b'OggS','ogg signature',at)
  sigflags=b[at+5];gn,serial,no=struct.unpack_from('<QII',b,at+6);n=b[at+26];head=at+27+n;tail=head+sum(b[at+27:head])
  require(tail<=len(b) and no==seq and (prev is None or serial==prev),'Ogg page/serial continuity')
  if seq==0:
   require(sigflags&2 and b[head:head+8]==b'OpusHead','OpusHead BOS')
   skip=int.from_bytes(b[head+10:head+12],'little')
  if sigflags&4:end=gn;require(tail==len(b),'bytes after EOS')
  prev=serial;seq+=1;at=tail
 require(skip is not None and 0<skip<=3840 and end is not None and end>skip,'invalid pre-skip/final granule')
 return skip,end,seq
def enc(pcm,channels,mono='40k',stereo='64k'):
 bitrate=mono if channels==1 else stereo
 return cmd('ffmpeg','-nostdin','-v','error','-fflags','+bitexact','-f','s16le','-ar',str(RATE),'-ac',str(channels),'-i','pipe:0','-map_metadata','-1','-c:a','libopus','-application','audio','-b:a',bitrate,'-vbr','constrained','-compression_level','10','-frame_duration','20','-flags:a','+bitexact','-fflags','+bitexact','-f','ogg','pipe:1',data=pcm)
def tosample(x):return int((Decimal(str(x))*RATE).to_integral_value(rounding=ROUND_HALF_UP))
def ratio(a,b):
 x=a.astype(np.float64);y=b.astype(np.float64); ax=float(np.dot(x,x));by=float(np.dot(y,y))
 return float(np.dot(x,y)/(ax*by)**.5) if min(ax,by)>0 else None
def build():
 p=argparse.ArgumentParser()
 p.add_argument('--runtime',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--media-root',action='append',default=[],type=Path);p.add_argument('--pack',action='append',default=[],type=Path)
 p.add_argument('--reuse',type=Path,help='previous proof root; reuse only exact canonical profile/encoded bytes')
 p.add_argument('--profile',choices=('compact','hq'),default='hq');p.add_argument('--jobs',type=int,default=4);p.add_argument('--boundary-tolerance-samples',type=int,default=0,help='permit explicit measured source EOF under-run, default fail closed')
 a=p.parse_args();assert not a.out.exists() and 0<=a.boundary_tolerance_samples<=48
 require(not a.out.resolve().is_relative_to(a.runtime.resolve()),'don’t modify source')
 a.out.mkdir(parents=True);site=a.out/'site';site.mkdir()
 roots=[a.runtime,*a.media_root]; codecBuild=cmd('ffmpeg','-version').decode().splitlines()[0]
 profile=dict(name='ogg-libopus-bitexact-48000-v1',encoderBuild=codecBuild,mono='40k',stereo='64k',frameMs=20,vbr='constrained',nativeType='audio/ogg; codecs="opus"')
 if a.profile=='hq':profile.update(name='ogg-libopus-bitexact-48000-hq-v2',mono='56k',stereo='96k')
 namespace='opus' if a.profile=='compact' else 'opus-hq56-96-v2'
 mime=mimetypes.MimeTypes();mime.add_type(MIME,'.ogg');require(mime.guess_type('x.ogg')[0]==MIME,'MIME registration')
 pooled={};refs={};packs={}
 provided={}
 for f in a.pack:
  key=jd(f.read_bytes())['testId']; require(key not in provided,key);provided[key]=f
 for key in ('test-01','test-02','test-03'):
  f=provided.get(key,a.runtime/'data'/f'{key}.json');before=jd(f.read_bytes()); p=copy.deepcopy(before)
  require(p['testId']==key and len(p['questions'])==200,key)
  removed=[x for x in HISTORY if x in p]
  for x in removed:p.pop(x)
  plan=p['listeningPlan'];fr=plan['frames']
  require(plan['duration']==2700 and len(fr)==284 and sum(x['role']=='answer' for x in fr)==100,key)
  require(abs(fr[-1]['at']+fr[-1]['duration']-2700)<.00005,key)
  packs[key]=(p,dig(f.read_bytes()),removed)
  for i,x in enumerate(fr):
   if x['kind']=='audio':
    require(x['role']!='answer' and 0<=x['start']<x['end'],key,i)
    refs.setdefault(safe(x['src']),[]).append(dict(scope=key,role=x['role'],frame=i,group=x.get('groupId'),start=x['start'],end=x['end']))
  for g in p['groups']:
   if s:=g.get('audio'):
    require(0<=g['audioStart']<g['audioEnd'],g['id'])
    refs.setdefault(safe(s),[]).append(dict(scope=key,role='practice',group=g['id'],start=g['audioStart'],end=g['audioEnd']))
 sample=a.runtime/'語音試聽.html'; samplehtml=sample.read_text()
 pattern=r'(<audio\b[^>]*\bsrc=")([^"]+)(")'
 sample_paths=[safe(s[1]) for s in re.findall(pattern,samplehtml,flags=re.I)]
 require(len(sample_paths)==14 and len(set(sample_paths))==14,'exactly 14 original accent examples')
 for r in sample_paths:refs.setdefault(r,[]).append(dict(scope='accent-preview',role='sample'))
 sourcefiles={r:canonical_path(roots,r) for r in sorted(refs)}
 for r,f in sourcefiles.items():
  b=dig(f.read_bytes());pooled.setdefault(b,[]).append(r)
 reuse=jd((a.reuse/'asset-report.json').read_bytes()) if a.reuse else {}
 if reuse:require(reuse['profile']==profile,'cache profile differs')
 oldcache=reuse.get('assets',{})
 def check_ranges(routes,n):
  for r in routes:
   for a1 in refs[r]:
    if 'start' not in a1:continue
    lo,hi=tosample(a1['start']),tosample(a1['end']); short=max(0,hi-n)
    require(0<=lo<hi and short<=a.boundary_tolerance_samples,'planned source boundary exceeds decoded file',r,a1,n,short)
    a1.update(startSample48k=lo,endSample48k=hi,decodedCoverageSamples=min(hi,n)-lo,inheritedEofRoundingSamples=short,endSampleQuantizationOffset=float(Decimal(str(a1['end']))*RATE-hi),exactOriginalEndOverrunSamples=float(max(Decimal(0),Decimal(str(a1['end']))*RATE-n)))
 def project(unit):
  s,routes=unit; f=sourcefiles[routes[0]]
  path=f'audio/{namespace}/{s[:2]}/{s}.ogg';target=site/path;target.parent.mkdir(parents=True,exist_ok=True)
  if s in oldcache:
   r=copy.deepcopy(oldcache[s]); cached=a.reuse/'site'/r['path']; payload=cached.read_bytes()
   require(r['path']==path and dig(payload)==r['encodedSha256'] and len(payload)==r['encodedBytes'],'cache asset mismatch',s)
   pre,end,pages=opus_geometry(payload)
   require((pre,end,pages)==(r['preSkipSamples'],r['finalGranule'],r['oggPages']) and end-pre==r['decodedSamples'],'cached exact Opus geometry',s)
   try:os.link(cached,target)
   except OSError:shutil.copyfile(cached,target)
   check_ranges(routes,r['decodedSamples']);r.update(sourcePaths=routes,reused=True)
   return s,r
  info=probe(f);streams=info['streams'];require(len(streams)==1 and streams[0]['codec_type']=='audio','non-single audio stream',f)
  channels=streams[0]['channels'];require(channels in (1,2),f)
  pcm=dec(f);require(len(pcm)%(2*channels)==0,f); n=len(pcm)//(2*channels)
  target.write_bytes(enc(pcm,channels,profile['mono'],profile['stereo']))
  opus=target.read_bytes();pre,end,pages=opus_geometry(opus)
  o=probe(target);st=o['streams'];require(len(st)==1 and st[0]['codec_name']=='opus' and st[0]['sample_rate']=='48000' and st[0]['channels']==channels and o['format']['format_name']=='ogg',path)
  decoded=dec(target);require(len(decoded)==len(pcm) and len(decoded)//(2*channels)==end-pre==n,'duration/preskip mismatch',f,n,len(decoded)//(2*channels),end,pre)
  x=np.frombuffer(pcm,dtype='<i2');y=np.frombuffer(decoded,dtype='<i2')
  similarity=ratio(x,y);require(similarity is not None and similarity>.90,'unexpected decoded shape/lag',f,similarity)
  check_ranges(routes,n)
  return s,dict(path=path,sourcePaths=routes,sourceCodec=streams[0]['codec_name'],sourceContainer=info['format']['format_name'],sourceBytes=f.stat().st_size,encodedBytes=target.stat().st_size,encodedSha256=dig(opus),sourcePcmSha256=dig(pcm),decodedPcmSha256=dig(decoded),decodedSamples=n,durationSeconds=n/RATE,preSkipSamples=pre,finalGranule=end,ch=channels,oggPages=pages,pcmShapeCorrelation=round(similarity,6),mime=MIME,byteRangeStart=0,byteRangeEnd=len(opus)-1,reused=False)
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as ex:
  units=dict(ex.map(project,sorted(pooled.items())))
 mapping={r:units[s]['path'] for s,routes in pooled.items() for r in routes}
 proof={}
 audio_count=0
 for key,(p,idh,removed) in packs.items():
  baseline=copy.deepcopy(p)
  for g in p['groups']:
   if g.get('audio'):g['audio']=mapping[g['audio']];audio_count+=1
  for f in p['listeningPlan']['frames']:
   if f['kind']=='audio':f['src']=mapping[f['src']];audio_count+=1
  rev={mapping[r]:r for r in mapping}
  normalized=copy.deepcopy(p)
  for g,t0 in zip(normalized['groups'],baseline['groups'],strict=True):
   if g.get('audio'): require(g['audio']==mapping[t0['audio']],key);g['audio']=t0['audio']
  for f,t0 in zip(normalized['listeningPlan']['frames'],baseline['listeningPlan']['frames'],strict=True):
   if f['kind']=='audio':require(f['src']==mapping[t0['src']],key);f['src']=t0['src']
  require(normalized==baseline,'non-path active metadata drift',key)
  f=site/'data'/f'{key}.json';wr(f,p)
  b=js(p).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
  f.with_suffix('.js').write_text('window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('+b+');\n')
  proof[key]=dict(sourcePackSha256=idh,opusPackSha256=dig(f.read_bytes()),beforePlanSha256=canon(baseline['listeningPlan']),opusPlanSha256=canon(p['listeningPlan']),duration=2700,frames=284,answerWindows=100,unchangedNonPathFields=True,omittedPreReleaseFields=removed)
 for f in sorted(a.runtime.glob('*.html')):
  if f.name==sample.name:
   b=re.sub(pattern,lambda m:m[1]+mapping[m[2]]+m[3],samplehtml,flags=re.I);(site/f.name).write_text(b)
  else:shutil.copyfile(f,site/f.name)
 for f in sorted((a.runtime/'assets').rglob('*')):
  if f.is_file() and f.suffix.lower() not in RAW:
   o=site/f.relative_to(a.runtime);o.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,o)
 # Include assets of all actual packs, including an image provided by a separate mix media root.
 for key,(p,*_) in packs.items():
  for g in p['groups']:
   if rel:=g.get('image'):
    src=canonical_path(roots,rel);dest=site/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copyfile(src,dest)
 asset_lit=re.compile(r'assets/[A-Za-z0-9_./-]+\.(?:svg|png|jpg|jpeg|webp|css|js)')
 literal_assets=set()
 for f in [*site.glob('*.html'),*site.glob('assets/*.js'),*site.glob('assets/*.css')]:
  literal_assets.update(asset_lit.findall(f.read_text()))
 graphic_checked={}
 for r in sorted(literal_assets):
  s=canonical_path(roots,r);df=site/r;df.parent.mkdir(parents=True,exist_ok=True)
  if not df.exists():shutil.copyfile(s,df)
  require(dig(df.read_bytes())==dig(s.read_bytes()),'static runtime asset mismatch',r)
  graphic_checked[r]=dig(df.read_bytes())
 examples=[r/'data/example-pack.json' for r in roots if (r/'data/example-pack.json').is_file()]
 require(examples,'missing Download Example Format source')
 for f in examples:
  require(dig(f.read_bytes())=='de36c1be445c9f31e7ae59c09ccb7aed9dd3ce242f492d6281a7053beefd47af','example-pack exact source')
 shutil.copyfile(examples[0],site/'data/example-pack.json')
 graphic_checked['data/example-pack.json']=dig(examples[0].read_bytes())
 catalog=(a.runtime/'data/catalog.js').read_text()
 catalog=re.sub(r'(?m)^window\.SHIFT_CATALOG\.resumeSnapshots=[^\n]*;\s*$', '',catalog)
 require('data/resume/' not in catalog,'unexpected archive reference in catalog')
 (site/'data/catalog.js').write_text(catalog)
 app=site/'assets/app.js';b=app.read_text()
 anchor="const player=document.getElementById('audio-player');"
 require(b.count(anchor)==1,'App source guard for native codec probe')
 b=b.replace(anchor,anchor+'\n'+'''const opusPlayable=()=>Boolean(player.canPlayType('audio/ogg; codecs="opus"')||player.canPlayType('audio/ogg'));
const opusRequired=p=>typeof p==='string'&&p.endsWith('.ogg');
const opusUnavailable='This browser does not support Ogg Opus audio. Please use a browser with native Opus playback.';''')
 a1="const frames=groupFrames(g),prior=s.audioUsed?.[g.id];"
 a2="if(!g?.audio){notify('No audio is available for this question.');return}"
 require(b.count(a1)==1 and b.count(a2)==1,'App playback guards not found exactly once')
 b=b.replace(a1,a1+"\n if(frames.some(f=>opusRequired(f.src))&&!opusPlayable()){notify(opusUnavailable);return;}")
 b=b.replace(a2,a2+"if(opusRequired(g.audio)&&!opusPlayable()){notify(opusUnavailable);return}")
 app.write_text(b)
 graphic_checked['assets/app.js']=dig(app.read_bytes())
 doc=Path(__file__).with_name('PUBLIC-AUTHORING.md'); require(doc.is_file(),'missing public Opus authoring guide')
 shutil.copyfile(doc,site/'AUTHORING.md');graphic_checked['AUTHORING.md']=dig(doc.read_bytes())
 class Links(HTMLParser):
  def handle_starttag(self,tag,attrs):
   for k,v in attrs:
    if k not in ('src','href') or not v or v.startswith('#'):continue
    u=urlparse(v)
    if u.scheme or u.netloc:continue
    link=unquote(u.path)
    require(link and not link.startswith('/') and '..' not in Path(link).parts,link)
    require((site/link).is_file(),'broken static runtime link',link)
 for page in site.glob('*.html'):Links().feed(page.read_text())
 for f in [*site.glob('*.html'),*site.glob('data/*'),*site.glob('assets/*.js')]:
  if f.is_file():
   t=f.read_text(); require(not re.search(r'''audio/[A-Za-z0-9_./-]+\.(mp3|wav|m4a|flac|webm|opus)(?=["' ?&<])''',t,re.I),'reachable raw asset literal',f)
 require({f.relative_to(site).as_posix() for f in (site/'audio').rglob('*') if f.is_file()}==set(mapping.values()),'exact active reachable audio closure')
 require(not (site/'data/resume').exists(),'historical archive accidentally published')
 raw=sum(f.stat().st_size for f in sourcefiles.values());unique=sum(u['sourceBytes'] for u in units.values());final=sum(u['encodedBytes'] for u in units.values())
 reference=dict(profile=profile,assets=units,mapping=mapping,boundaries=refs,packs=proof,samples=sample_paths,staticLiteralAssetSha256=graphic_checked)
 wr(a.out/'asset-report.json',reference)
 summary=dict(status='verified-local-opus-projection-not-browser-release',mime=MIME,codec='opus',nativeProbe=profile['nativeType'],activeReferenceCount=audio_count+14,distinctRawPaths=len(refs),distinctSourceHashes=len(units),opusAssets=len(units),reused=sum(u['reused'] for u in units.values()),originalReachableBytes=raw,originalDedupBytes=unique,opusBytes=final,savingsBytes=raw-final,savingsPct=round((raw-final)*100/raw,2),verifiedTimedBoundaries=audio_count,previewSamples=14,minimumShapeCorrelation=min(u['pcmShapeCorrelation'] for u in units.values()),paddedOrTrimmedSamples=0,allowedInheritedSourceRoundingSamples=a.boundary_tolerance_samples,activeOnly=True,externalHttpStatus='not exercised by conversion')
 wr(a.out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':build()
