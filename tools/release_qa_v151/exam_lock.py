#!/usr/bin/env python3
"""Fail-closed whole-exam lock candidate. No signing/approval or deployment."""
from pathlib import Path
from continuous_contract import geometry, role as continuous_role, owner as continuous_owner
from collections import Counter
from group_layout import require_contiguous_groups, require_part7_layout, uses_source_document_count
import argparse, hashlib, json, math, re, struct, subprocess, sys
from decimal import Decimal,ROUND_HALF_UP

EXAM=re.compile(r'test-[0-9]{2,3}\Z')
ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}\Z')
PATH=re.compile(r'[A-Za-z0-9_./-]+\Z')
SHA=re.compile(r'[a-f0-9]{64}\Z')
PARTS={1:6,2:25,3:39,4:30,5:30,6:16,7:54}
GATES={'itemContent','independentReReview','difficultyDistribution','authoringRoundtrip','opusPlaybackAndRanges','nativeBrowserAcceptance','versionParity','releaseSize'}
GROUPS={3:3,4:3,6:4}
REQUIRED_COMMON={'assets/scenes/formal-example.svg'}
WRAPPER=re.compile(rb'window\.SHIFT_PACKS=window\.SHIFT_PACKS\|\|\[\];window\.SHIFT_PACKS\.push\((.*)\);\n?\Z',re.S)
IGNORED={'exam-lock.json'}

class LockError(ValueError): pass
def need(ok,why):
 if not ok:raise LockError(why)
def sha(b):return hashlib.sha256(b).hexdigest()
def is_sha(x):return isinstance(x,str) and bool(SHA.fullmatch(x))
def unique(pairs):
 out={}
 for k,v in pairs:
  need(k not in out,f'duplicate JSON key: {k}');out[k]=v
 return out
def bad_number(s):raise LockError(f'nonfinite JSON value: {s}')
def read_json(b):return json.loads(b.decode('utf-8'),object_pairs_hook=unique,parse_constant=bad_number)
def canonical(o):return (json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
def need_path(rel):
 need(isinstance(rel,str) and PATH.fullmatch(rel) and all(k not in ('','.','..') for k in rel.split('/')),f'unsafe path: {rel!r}')
 return rel
def location(root,rel):
 need_path(rel); x=root
 for c in rel.split('/'):
  x=x/c;need(not x.is_symlink(),f'symlink or alias forbidden: {rel}')
 need(x.is_file(),f'missing file: {rel}')
 return x
def bytes_at(root,rel):return location(root,rel).read_bytes()
def norm(root):
 a=Path(root).absolute();need(a.is_dir() and a==a.resolve(),f'input must be a real directory: {root}');return a
def pinned(p,expected):
 need(is_sha(expected),'required external SHA-256 pin missing/invalid')
 need(p.is_file() and not p.is_symlink(),f'missing or linked pinned input: {p}')
 b=p.read_bytes();need(sha(b)==expected,f'pinned artifact mismatch: {p.name}')
 return read_json(b)
def output(p,b):
 need(not p.exists() and not p.is_symlink(),f'output must be absent: {p}')
 need(p.parent.is_dir() and p.parent.absolute()==p.parent.resolve(),f'output parent is not an established real directory: {p.parent}')
 with p.open('xb') as f:f.write(b)
def text(v):return isinstance(v,str) and bool(v.strip())
def number(v):return type(v) in (int,float) and math.isfinite(v)

def media_refs(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ('audio','src','image','archivedImage') and isinstance(v,str):
    need(v.startswith(('audio/','assets/')),f'non-local media reference: {v!r}'); yield need_path(v)
   elif isinstance(v,(dict,list)):yield from media_refs(v)
 elif isinstance(x,list):
  for z in x:yield from media_refs(z)
def artifact_aliases(entries):
 bycase={}
 for v in entries:
  k=v.casefold();need(k not in bycase or bycase[k]==v,f'case-alias paths: {bycase.get(k)} and {v}');bycase[k]=v
def opus(f):
 b=f.read_bytes();need(b.startswith(b'OggS') and b'OpusHead' in b[:96],f'not an Ogg/Opus stream: {f.name}')
 r=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name,sample_rate,channels:format=format_name','-of','json','pipe:0'],input=b,capture_output=True,check=False)
 need(r.returncode==0,f'ffprobe failed: {f.name}')
 p=read_json(r.stdout);s=p.get('streams',[])
 need(p.get('format',{}).get('format_name')=='ogg' and len(s)==1 and s[0].get('codec_name')=='opus' and s[0].get('sample_rate')=='48000' and s[0].get('channels') in (1,2),f'not single-track 48 kHz Ogg Opus: {f.name}')
 pos=0;page=0;serial=None;pre=None;last=None
 while pos<len(b):
  need(pos+27<=len(b) and b[pos:pos+5]==b'OggS\0','malformed Ogg pages')
  gran,sn,idx=struct.unpack_from('<QII',b,pos+6);flags=b[pos+5];n=b[pos+26]
  begin=pos+27+n
  need(begin<=len(b),'truncated Ogg segment table')
  end=begin+sum(b[pos+27:begin])
  need(end<=len(b) and idx==page and (serial is None or serial==sn),'Ogg media aliases/chains not allowed')
  if page==0:
   need(flags&2 and b[begin:begin+8]==b'OpusHead','missing OpusHead')
   pre=int.from_bytes(b[begin+10:begin+12],'little')
  if flags&4:need(end==len(b),'data follows Ogg EOS');last=gran
  serial=sn;pos=end;page+=1
 need(pre is not None and 0<pre<=3840 and last is not None and last>pre,'invalid Opus playable granule count')
 return last-pre

def inspect_continuous_decode(path,layout):
 # Operate on actual decoded mono signed 16-bit samples, not the duration tag or browser clock.
 import numpy as np
 r=subprocess.run(['ffprobe','-v','error','-select_streams','a','-show_entries','stream=channels','-of','csv=p=0',str(path)],capture_output=True,check=False)
 need(r.returncode==0 and r.stdout.strip()==b'1','formal group Opus must decode natively to mono')
 v=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(path),'-map','0:a:0','-f','s16le','-'],capture_output=True,check=False)
 need(v.returncode==0 and not v.stderr and len(v.stdout)==layout['size']*2,'continuous group decode error or incorrect 48k sample count')
 decoded=np.frombuffer(v.stdout,dtype='<i2'); last=0; edges=[]
 for seg in layout['frames']:
  a,b=seg['start'],seg['end'];need(a==last and b>a and b<=len(decoded),'decoded frame geometry drift')
  abs_pcm=np.abs(decoded[a:b].astype(np.int32)); crossing=np.nonzero(abs_pcm>=33)[0]
  if seg['kind']=='silence':
   need(seg['role']=='answer','unknown decoded silence purpose')
   need(not len(crossing) or (crossing[-1]<960 and abs_pcm.max()<327),'non-silent encoded answer window outside known 20ms codec tail')
   edges.append((seg['index'],'answer',len(crossing),int(crossing[-1])+1 if len(crossing) else 0))
  else:
   need(len(crossing)>0,'wholly silent logical speech frame')
   lead=int(crossing[0]);tail=b-a-1-int(crossing[-1])
   need(lead<96000 and tail<96000,'continuous speech frame has a two-second unplanned leading/trailing gap')
   edges.append((seg['index'],'speech',lead,tail))
  last=b
 need(last==layout['size'],'decoded group has out-of-plan samples')
 return dict(decodedPcmSha256=sha(v.stdout),decodedSamples48k=last,checks=edges)

def validate_pack(p,t):
 need(p.get('testId')==t and p.get('schemaVersion')==1,'pack exam/schema mismatch')
 need(not any(k in p for k in ('legacyQuestions','previousListeningPlan','alternateListeningPlans')),'pre-release archive fields are not active lock inputs')
 q=p['questions']; g=p['groups']; ids=set(); gp={}; rev=p['revision']
 need(type(rev)==int and rev>=1,'invalid exam revision')
 for z in g:
  gid=z['id'];need(isinstance(gid,str) and ID.fullmatch(gid) and gid not in gp and z.get('testId')==t,'invalid group ID/revision')
  gp[gid]=z;need(text(z.get('passage')) and text(z.get('passageZh')),f'missing dual-language passage: {gid}')
  if z['part']==1:need(text(z.get('image')),f'missing Part 1 picture: {gid}')
  if z['part']<=4:need(isinstance(z.get('audio'),str) and number(z.get('audioStart')) and number(z.get('audioEnd')) and 0<=z['audioStart']<z['audioEnd'],f'invalid practice range: {gid}')
 need(len(q)==200 and [z.get('number') for z in q]==list(range(1,201)) and Counter(z.get('part') for z in q)==PARTS,'exam must have 200 ordered questions with exact Part counts')
 groupq=Counter()
 for z in q:
  qid=z['id']; pno=z['part']; gi=z.get('groupId')
  need(z.get('testId')==t and ID.fullmatch(qid) and qid not in ids and type(z.get('revision'))==int and z['revision']>=1,'invalid question identity/revision')
  ids.add(qid);need(gi in gp and gp[gi]['part']==pno or gi is None and pno==5,f'question/group mismatch: {qid}')
  if gi is not None:groupq[gi]+=1
  need(z.get('difficulty') in ('foundation','intermediate','advanced') and all(text(z.get(k)) for k in ('prompt','promptZh','evidence','explanationZh')),f'incomplete bilingual item: {qid}')
  op=z['options']; keys=list('ABC' if pno==2 else 'ABCD')
  need([k.get('id') for k in op]==keys and z.get('answer') in keys and all(text(k.get(f)) for k in op for f in ('text','zh','whyZh')),f'invalid options/key: {qid}')
  need(isinstance(z.get('vocabulary'),list) and z['vocabulary'] and all(text(v.get(k)) for v in z['vocabulary'] for k in ('term','zh','note')),f'incomplete vocabulary: {qid}')
 require_contiguous_groups(q,need)
 need(set(groupq)==set(gp),'unreferenced group')
 for gid,n in groupq.items():
  part=gp[gid]['part']
  need(part not in GROUPS or n==GROUPS[part],f'incomplete group: {gid}')
 plan=p['listeningPlan'];fr=plan['frames']; ans=set()
 need(plan.get('duration')==2700 and plan.get('testId')==t and bool(fr),'invalid 2700s formal plan')
 next_at=0.0; secs_tol=.00006
 for x in fr:
  d=x.get('duration');at=x.get('at');kind=x.get('kind');role=x.get('role')
  need(kind in ('audio','silence') and number(d) and d>0 and number(at) and abs(at-next_at)<=secs_tol,'gap/overlap or invalid formal frame')
  next_at=at+d;need(x.get('groupId') in gp and gp[x['groupId']]['part']==x.get('part') and x['part']<=4,'unknown formal group/part')
  if kind=='audio':
   lo,hi=x.get('start'),x.get('end')
   need(number(lo) and number(hi) and 0<=lo<hi and abs((hi-lo)-d)<=secs_tol and isinstance(x.get('src'),str),'invalid audio window')
  if role=='answer':
   qi=x.get('questionId'); need(kind=='silence' and qi not in ans,'duplicate or non-silence answer')
   ans.add(qi)
 need(abs(next_at-2700)<=secs_tol and ans=={x['id'] for x in q[:100]},'formal timing or answer slot coverage drift')
 return q,g,plan

def frames48(x):
 return int((Decimal(str(x))*48000).to_integral_value(rounding=ROUND_HALF_UP))
def check_question_sidecar(index,q,g,p,test,declared,continuous=None):
 need(index['question']==q['id'] and index['groupSource']==(f"{test}/groups/{g['id']}/group.json" if g else None),'question sidecar points to another record')
 roles=index['roles']; need(isinstance(roles,list) and all(isinstance(r,dict) for r in roles),'bad question role records')
 expected=[]
 for u in sorted(set(media_refs(q))):expected.append(dict(url=u,role='question-asset',question=q['id']))
 if g:
  if continuous and g['id'] in continuous:
   rr=continuous_role(continuous[g['id']],g['id'])
   need(declared.get(rr['url'])==continuous_owner(test,g['id'],rr['url']),'formal group audio sidecar has the wrong canonical owner')
   expected.append(rr)
  for u in sorted(set(media_refs(g))):
   if u==g.get('audio'):
    a,b=g['audioStart'],g['audioEnd'];expected.append(dict(url=u,role='practice-audio',group=g['id'],start=a,end=b,startSample48k=frames48(a),endSample48k=frames48(b)))
   else:expected.append(dict(url=u,role='group-visual',group=g['id']))
  for i,f in enumerate(p['listeningPlan']['frames']):
   if f.get('src') and f['groupId']==g['id'] and f.get('questionId') in (None,q['id']):
    a,b=f['start'],f['end'];expected.append(dict(url=f['src'],role=f['role'],group=g['id'],question=f.get('questionId'),frame=i,timelineAt=f['at'],start=a,end=b,startSample48k=frames48(a),endSample48k=frames48(b)))
 need(set(declared)=={r['url'] for r in expected},'question sidecar media closure mismatch')
 for r in expected:r['source']=declared[r['url']]
 need(Counter(canonical(x) for x in roles)==Counter(canonical(x) for x in expected),'question sidecar role/range/mapping differs from runtime')

def search_source(root,name):
 files=[]
 for x in sorted((root/name).rglob('*')):
  rel=x.relative_to(root).as_posix();need_path(rel);need(not x.is_symlink(),f'symlink source file: {rel}')
  if x.is_file() and rel!=name+'/exam-lock.json':
   need(not rel.startswith(name+'/archive/'),f'pre-release archive in active source: {rel}')
   files.append(rel)
 return files

def inventory(src,site,test,check_codec=True):
 need(isinstance(test,str) and EXAM.fullmatch(test),'invalid exam ID')
 fjson=f'data/{test}.json';fjs=f'data/{test}.js';pb=bytes_at(site,fjson);wb=bytes_at(site,fjs);m=WRAPPER.fullmatch(wb)
 need(m is not None,'JS wrapper format is not canonical data-only');p=read_json(pb); need(read_json(m[1])==p,'JSON/JS wrapper payload mismatch')
 q,g,plan=validate_pack(p,test); continuous=geometry(plan,test)
 em=f'{test}/exam.json';b=read_json(bytes_at(src,em));need(b.get('testId')==test,'source exam identity mismatch')
 rs=b['records'];need(set(rs)<= {'questions','groups','legacyQuestions'} and not rs.get('legacyQuestions'),'active authoring archive or unknown record type')
 need(b['metadata']=={k:v for k,v in p.items() if k not in ('questions','groups')},'editable exam metadata differs from runtime')
 qp=[f'{test}/questions/Q{n:03}/question.json' for n in range(1,201)]
 pg=[f"{test}/groups/{row['id']}/group.json" for row in g]
 need(rs.get('questions')==qp and rs.get('groups')==pg,'source records not at exact per-question/group paths or ordered differently')
 strict_part7=uses_source_document_count(test); source_counts={}
 for name,row in zip(qp+pg,q+g,strict=True):
  record=read_json(bytes_at(src,name))
  need(record==row,f'editable record differs from active runtime: {name}')
  if strict_part7 and name.endswith('/group.json') and record['part']==7:
   count=record.get('documentCount')
   need(type(count) is type(row.get('documentCount')),f'documentCount type differs from runtime: {name}')
   source_counts[record['id']]=count
 if strict_part7:
  require_part7_layout(g,require_contiguous_groups(q,need),lambda row: source_counts[row['id']],need)
 paths=search_source(src,test); known=set(qp+pg+[em]); media_set=set(media_refs(p))
 media_files={};source_dig={};sidecars=0;active_groups={row['id']:row for row in g}
 for path in paths:
  if path.endswith('/media.json'):
   known.add(path);index=read_json(bytes_at(src,path));keys=set(index); rich=keys=={'files','question','groupSource','roles'}
   need((keys=={'files'} or rich) and isinstance(index['files'],list),'invalid media map')
   qq=re.fullmatch(rf'{test}/questions/Q([0-9]{{3}})/media.json',path);declared={}
   need(not rich or qq is not None,'misplaced question sidecar')
   for r in index['files']:
    allowed=set(r)=={'url','source'} or (path==test+'/common/media.json' and set(r)=={'url','source','sha256','bytes','ownership','uses'})
    need(allowed,f'unexpected map keys: {path}')
    url,sp=need_path(r['url']),need_path(r['source'])
    need(url in media_set and sp.endswith('/'+url) and (sp.startswith(test+'/') or sp.startswith('common/')),f'unbound or aliased media reference: {url}')
    need(media_files.get(url,sp)==sp,f'multiple source owners for media URL: {url}');media_files[url]=sp
    need(url not in declared,'duplicated media entry within source map');declared[url]=sp
    bb=bytes_at(src,sp);s=sha(bb);need(s==sha(bytes_at(site,url)),f'editable source and delivered media differ: {url}');source_dig[sp]=s
    if 'sha256' in r:need(r['sha256']==s and r['bytes']==len(bb),'common sidecar byte/hash differs')
   if rich:
    n=int(qq[1]);need(1<=n<=200,'invalid sidecar slot');row=q[n-1]
    check_question_sidecar(index,row,active_groups.get(row.get('groupId')),p,test,declared,continuous);sidecars+=1
 if continuous:
  need(sidecars==200,'continuous pack requires all 200 question role sidecars')
  for gid,rr in continuous.items():
   path=rr['src'];target=continuous_owner(test,gid,path)
   need(media_files.get(path)==target,'continuous file is not physically owned by its exact group')
   gside=read_json(bytes_at(src,f'{test}/groups/{gid}/media.json'))
   need(sum(x=={'url':path,'source':target} for x in gside['files'])==1,'missing group-level continuous file dependency')
 need(set(media_files)==media_set,'source media maps do not exactly cover active dependencies')
 need(set(paths)==known|{x for x in source_dig if x.startswith(test+'/')},'untracked source file or extra media under exam')
 manifest=read_json(bytes_at(src,'manifest.json')) if (src/'manifest.json').exists() else {}
 for r in media_files:
  if manifest:
   mrow=manifest['media'].get(r)
   need(isinstance(mrow,dict) and mrow['source']==media_files[r] and mrow['sha256']==source_dig[media_files[r]],'global source manifest media alias differs')
 for r in REQUIRED_COMMON:
  st=manifest.get('standalone',{}).get(r)
  if st:
   sp=need_path(st['source']);data=bytes_at(src,sp)
   need(sp==f'common/standalone/{r}' and st['sha256']==sha(data)==sha(bytes_at(site,r)) and st['bytes']==len(data),'standalone source artifact hash/ownership differs')
   source_dig[sp]=st['sha256']
 artifact_aliases(set(paths)|set(source_dig)|set(media_set))
 for path in known:source_dig[path]=sha(bytes_at(src,path))
 urls=media_set|REQUIRED_COMMON; run={};coverage={}
 for path in sorted(urls):
  f=location(site,path)
  if path.startswith('audio/'):
   need(path.endswith('.ogg'),f'active audio has non-Opus extension: {path}')
   if check_codec:coverage[path]=opus(f)
  else:need(path.startswith('assets/'),f'unsupported dependency: {path}')
  run[path]=dict(sha256=sha(f.read_bytes()),bytes=f.stat().st_size)
 if check_codec:
  bounds=[(x['audio'],x['audioStart'],x['audioEnd']) for x in g if x.get('audio')]+[(x['src'],x['start'],x['end']) for x in plan['frames'] if x['kind']=='audio']
  for path,lo,hi in bounds:
   need(path in coverage and 0<=frames48(lo)<frames48(hi)<=coverage[path],f'formal/practice range falls outside decoded-size media: {path}')
  if continuous:
   # A formal continuous asset cannot share bytes with practice, historic French etc.
   paths_cont={r['src'] for r in continuous.values()}
   all_shas=Counter(x['sha256'] for x in run.values())
   for gid,rr in continuous.items():
    need(all_shas[run[rr['src']]['sha256']]==1,'duplicate encoded formal group bytes are not independently owned')
    need(coverage[rr['src']]==rr['size'],'Opus granules do not cover exact group wait/speech durations')
    inspect_continuous_decode(location(site,rr['src']),rr)
 for path, data in ((fjson,pb),(fjs,wb)):run[path]=dict(sha256=sha(data),bytes=len(data))
 return dict(examId=test,examRevision=p['revision'],canonicalRuntimeSha256=sha(canonical(p)),formalPlanSha256=sha(canonical(plan)),questionIdentities=[{'number':z['number'],'id':z['id'],'revision':z['revision'],'sourceSha256':source_dig[k]} for z,k in zip(q,qp,strict=True)],sourceFiles=source_dig,runtimeFiles=run,mediaSource=media_files,checkedQuestionRoleSidecars=sidecars,part1MissingAltIds=[z['id'] for z in g if z['part']==1 and not text(z.get('imageAlt'))])

def policy_load(path,digest):
 z=pinned(path,digest);need(set(z)=={'format','release','expectedExams','baselineLocks','initialExams'},'invalid trusted policy fields')
 need(z['format']=='shift-externally-trusted-lock-policy-v1' and text(z['release']),'invalid trusted policy domain')
 e=z['expectedExams'];prior=z['baselineLocks']; new=z['initialExams']
 need(isinstance(e,list) and re.fullmatch(r'[A-Za-z0-9_.-]+',z['release']) and all(EXAM.fullmatch(t) for t in e) and len(e)==len(set(e)) and e and set(prior).isdisjoint(new) and set(prior)|set(new)==set(e) and all(is_sha(s) for s in prior.values()),'wrong trusted baseline/initial scope')
 # Initial pins are from a trusted gate runner, not from candidate data.
 need(all(is_sha(s) for s in new.values()),'initial gate report pins missing')
 return z
def locked_record(inv,gate_policy,gate_file,evidence_root):
 need(isinstance(gate_policy,dict),'invalid policy'); test=inv['examId']
 need(test not in gate_policy['baselineLocks'] and test in gate_policy['initialExams'],'established exam cannot run initial generation; human amendment review is external and not implemented')
 gate=pinned(gate_file,gate_policy['initialExams'][test])
 need(set(gate)=={'format','examId','release','inventorySha256','gates'} and gate['format']=='shift-post-qa-receipt-v1' and gate['examId']==test and gate['release']==gate_policy['release'] and gate['inventorySha256']==sha(canonical(inv)),'QA bundle is not for this exact inventory/release')
 need(set(gate['gates'])==GATES,'missing release gates')
 need(len({g['artifact'] for g in gate['gates'].values()})==len(GATES),'gate artifacts must be independently identified')
 for n,x in gate['gates'].items():
  need(set(x)=={'status','artifact','sha256'} and x['status']=='pass' and is_sha(x['sha256']),'failed or unpinned release gate: '+n)
  need(sha(bytes_at(evidence_root,x['artifact']))==x['sha256'],'missing/changed gate evidence: '+n)
 payload=dict(format='shift-whole-exam-lock-v1',status='locked',release=gate_policy['release'],initialQaEvidence=gate,inventory=inv)
 return dict(**payload,integritySha256=sha(canonical(payload)))

def check_lock(src,site,test,policy,check_codec=True):
 raw=bytes_at(src,f'{test}/exam-lock.json')
 base=policy['baselineLocks'].get(test)
 need(is_sha(base) and sha(raw)==base,f'{test} lock missing from or changed vs externally trusted baseline')
 pack=read_json(raw);need(raw==canonical(pack) and set(pack)=={'format','status','release','initialQaEvidence','inventory','integritySha256'},f'{test} malformed lock')
 work={k:v for k,v in pack.items() if k!='integritySha256'}
 need(pack['format']=='shift-whole-exam-lock-v1' and pack['status']=='locked' and sha(canonical(work))==pack['integritySha256'],'lock flags or integrity signature mismatch')
 need(pack['inventory']==inventory(src,site,test,check_codec=check_codec),f'{test} locked question/source/media/runtime differs')
 return base

def check_site_scope(site,expected):
 # Catalog is generated JS. Check only its known data literals; never execute it here.
 data=bytes_at(site,'data/catalog.js').decode('utf-8')
 extras=set()
 for ext in ('json','js'):
  got={x.name.removesuffix('.'+ext) for x in (site/'data').glob(f'test-*.{ext}')}
  need(got==expected,f'whole-site {ext} exam inventory differs from trusted policy')
 # A registered ID is adjacent to the primary built-in JS path within the same row.
 reg={t:path for t,path in re.findall(r"""\bid\s*:\s*['"](test-[0-9]{2,3})['"][^{}\n]*?\bpath\s*:\s*['"]([^'"]+)['"]""",data)}
 need(set(reg)==expected and all(reg[t]==f'data/{t}.js' for t in expected),'catalog redirects or excludes an expected formal pack')
 found=re.findall(r"""['"](data/test-[0-9]{2,3}\.js)['"]""",data)
 need(Counter(found)==Counter(f'data/{t}.js' for t in expected),'catalog contains a duplicate/extra built-in path')

def main():
 cli=argparse.ArgumentParser(description=__doc__)
 cli.add_argument('action',choices=('snapshot','generate','verify','check'));cli.add_argument('--source',type=Path,required=True);cli.add_argument('--site',type=Path,required=True);cli.add_argument('--exam')
 cli.add_argument('--out',type=Path);cli.add_argument('--trusted-policy',type=Path);cli.add_argument('--trusted-policy-sha');cli.add_argument('--gates',type=Path);cli.add_argument('--evidence-root',type=Path)
 args=cli.parse_args();src=norm(args.source);site=norm(args.site)
 if args.action=='snapshot':
  need(args.out is not None and args.out.name!='exam-lock.json','snapshot writes an explicitly unapproved inventory only')
  need(not args.out.resolve().is_relative_to(src) and not args.out.resolve().is_relative_to(site),'draft inventory must be outside source and site')
  inv=inventory(src,site,args.exam)
  output(args.out,canonical(dict(status='draft-check-only',inventorySha256=sha(canonical(inv)),inventory=inv)));return
 need(args.trusted_policy is not None,'externally trusted policy and SHA are mandatory')
 po=policy_load(args.trusted_policy,args.trusted_policy_sha)
 if args.action=='generate':
  need(args.out is not None and args.gates is not None and args.evidence_root is not None,'explicit gate bundle and output required')
  need(args.exam in po['initialExams'] and args.exam not in po['baselineLocks'],'initial generation forbidden for established lock')
  need(not (src/args.exam/'exam-lock.json').exists(), 'existing lock may never be regenerated')
  need(args.out.name=='exam-lock.json' and not args.out.resolve().is_relative_to(site),'lock output filename/site separation')
  output(args.out,canonical(locked_record(inventory(src,site,args.exam),po,args.gates,norm(args.evidence_root))));return
 if args.action=='verify':
  need(args.exam in po['baselineLocks'],'requested exam has no established baseline')
  print(args.exam,check_lock(src,site,args.exam,po));return
 need(set(po['baselineLocks'])==set(po['expectedExams']),'not all expected exams have established trusted lock pins')
 check_site_scope(site,set(po['expectedExams']))
 for t in po['expectedExams']: print(t,check_lock(src,site,t,po))
if __name__=='__main__':
 try:main()
 except (LockError,ValueError,KeyError,TypeError,OSError) as e:
  print('EXAM LOCK BLOCKED:',e,file=sys.stderr);sys.exit(2)
