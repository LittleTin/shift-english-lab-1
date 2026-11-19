#!/usr/bin/env python3
"""Private whole-site assembly. No source mutation, final approval or lock."""
from pathlib import Path
import argparse,copy,hashlib,json,os,re,shutil,subprocess,sys
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
p=argparse.ArgumentParser()
for k in ('base-projection','t02-pack','t02-media','t02-proof','new-opus-receipts','namespace-apply','namespace-test','out'):p.add_argument('--'+k,type=Path,required=True)
p.add_argument('--expected-t02-sha',required=True,help='Independent expected byte hash for the exact editor snapshot')
p.add_argument('--t02-label-proof',type=Path,help='only verified label-only successor of --t02-pack; readiness still not inferred')
p.add_argument('--t02-labeled-pack',type=Path)
p.add_argument('--version',default='1.5.0')
a=p.parse_args(); assert not a.out.exists() and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',a.version)
b=a.base_projection/'site';a.out.mkdir(parents=True);s=a.out/'site';s.mkdir()
rd=lambda q:json.loads(q.read_bytes())
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def d(b):return hashlib.sha256(b).hexdigest()
def wr(f,o):f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def dh(o):return d(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def copyfile(f,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dst)
def link(f,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 try:os.link(f,dst)
 except OSError:copyfile(f,dst)
def safe(r):
 assert isinstance(r,str) and re.fullmatch(r'(audio|assets)/[A-Za-z0-9_./-]+',r) and not set(r.split('/'))&{'','.','..'},r
 return r
def refs(o):
 if isinstance(o,dict):
  for k,v in o.items():
   if k in ('src','audio','image','archivedImage') and isinstance(v,str):yield safe(v)
   else:yield from refs(v)
 elif isinstance(o,list):
  for v in o:yield from refs(v)
def js(x):return ('window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('+json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')+');\n').encode()
old=rd(a.base_projection/'asset-report.json');t2_bytes=a.t02_pack.read_bytes();t2_raw_sha=d(t2_bytes);t2=json.loads(t2_bytes); guard=rd(a.t02_proof)
assert guard['outputSha256']==t2_raw_sha==a.expected_t02_sha and guard['basePackSha256']==sha(b/'data/test-02.json')
assert bool(a.t02_label_proof)==bool(a.t02_labeled_pack)
if a.t02_label_proof:
 r=rd(a.t02_label_proof); assert r['sourcePackSha256']==t2_raw_sha and r['outputPackSha256']==d(a.t02_labeled_pack.read_bytes()) and r['difficultyGatePass'] and r['applied'] and r['reviewed']==200
 t2_bytes=a.t02_labeled_pack.read_bytes();assert d(t2_bytes)==r['outputPackSha256'];tp=json.loads(t2_bytes)
 assert all({k:v for k,v in x.items() if k!='difficulty'}=={k:v for k,v in y.items() if k!='difficulty'} for x,y in zip(t2['questions'],tp['questions'],strict=True))
 assert all(v==tp[k] for k,v in t2.items() if k!='questions')
 t2=tp
packs={t:(rd(b/'data'/f'{t}.json') if t!='test-02' else t2) for t in ('test-01','test-02','test-03')}
static={}; packproof={}
for t,x in packs.items():
 assert len(x['questions'])==200 and x['testId']==t and not set(x)&{'legacyQuestions','previousListeningPlan','alternateListeningPlans'}
 fr=x['listeningPlan']['frames'];assert x['listeningPlan']['duration']==2700 and sum(f['role']=='answer' for f in fr)==100 and len(fr)==284
 f=s/'data'/f'{t}.json'
 if t=='test-02':
  f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(t2_bytes);f.with_suffix('.js').write_bytes(js(x));assert json.loads(t2_bytes)==x
 else:
  copyfile(b/'data'/f'{t}.json',f);copyfile(b/'data'/f'{t}.js',f.with_suffix('.js'));assert sha(f)==old['packs'][t]['opusPackSha256']
 packproof[t]=dict(sha256=sha(f),wrapperSha256=sha(f.with_suffix('.js')),planSha256=dh(x['listeningPlan']),questions=200,listeningSeconds=2700)
audio_by_path={v['path']:(q,v) for q,v in old['assets'].items()}
fresh=rd(a.new_opus_receipts)['assets']; assert len(fresh)==4 and {v['question'] for v in fresh.values()}=={35,36,50,51}
for path,r in fresh.items():
 safe(path);given=a.t02_media/path;assert sha(given)==r['opusSha256']
 rec=dict(path=path,sourcePaths=[path],sourceCodec='opus',sourceContainer='ogg',encodedSha256=r['opusSha256'],encodedBytes=r['assetBytes'],decodedSamples=r['sampleCount'],durationSeconds=r['durationSeconds'],preSkipSamples=r['opusPreSkip'],finalGranule=r['opusFinalGranule'],oggPages=r['oggPages'],sourcePcmSha256=r['sourcePcmSha256'],decodedPcmSha256=r['decodedPcmSha256'],ch=1,originalRenderSha256=r['inputReceipt']['sha256'],pcmShapeCorrelation=r['correlation'],mime=r['mime'],passthroughExact=True)
 assert rec['finalGranule']-rec['preSkipSamples']==rec['decodedSamples']
 audio_by_path[path]=(r['opusSha256'],rec)
r0={r for x in packs.values() for r in refs(x)}; previews={old['mapping'][r] for r in old['samples']};assert len(previews)==14
planned={r for r in r0 if r.startswith('audio/')}|previews
active={}; refs_proof={}
for r in sorted(planned):
 key,receipt=audio_by_path[r];src=(a.t02_media if r in fresh else b)/r
 assert sha(src)==receipt['encodedSha256'] and r.endswith('.ogg')
 assert key not in active, 'duplicate delivery canonical identity'
 link(src,s/r);active[key]=receipt;refs_proof[r]=receipt['encodedSha256']
for f in sorted((b/'assets').rglob('*')):
 if f.is_file():copyfile(f,s/f.relative_to(b))
for r in r0:
 if r.startswith('assets/'):
  f=s/r; assert f.is_file() and sha(f)==sha(b/r),r
for f in (b/'data/example-pack.json',b/'AUTHORING.md'):
 copyfile(f,s/f.relative_to(b))
assert sha(s/'data/example-pack.json')=='de36c1be445c9f31e7ae59c09ccb7aed9dd3ce242f492d6281a7053beefd47af'
assert sha(s/'assets/scenes/formal-example.svg')=='de68dc145f3a746869039dcb0a7c9e79408681e0b46404a4899e192412f0dbe6'
prior_app=s/'assets/app.js';assert sha(prior_app)=='50e779e815e972b5f42c23b2e9a90bf137f4ed335652dcb289c9a3d1e6f7c188'
updated=a.out/'official-app.js'
subprocess.run([sys.executable,str(a.namespace_apply),str(prior_app),str(updated)],check=True)
assert sha(updated)=='1ffef4f55769e60f8193755bfa5a1c70e88bef26abb0067c26c5f0dede18d949'
shutil.copyfile(updated,prior_app)
with (a.out/'namespace-tests.log').open('w') as fh:subprocess.run(['node',str(a.namespace_test),str(prior_app)],check=True,stdout=fh)
catalog=(b/'data/catalog.js').read_text();assert catalog.count("version:'1.4.2'")==1 and 'data/resume/' not in catalog
(s/'data/catalog.js').write_text(catalog.replace("version:'1.4.2'",f"version:'{a.version}'"))
changes={
'Historical versions of revised questions remain available for saved answers, notes, favorites and incomplete sessions. New practice uses the current questions.':'This first official release does not migrate preview questions or preview listening assets. Within this release, saved answers, notes, favorites, history and unfinished sessions remain available in the same browser. New practice uses the current official questions.',
'If an older imported custom pack shares an ID with a newly added built-in pack, the existing custom pack is preserved and takes priority in that browser. A notice explains the conflict; export a backup to keep your custom material safe.':'Official test IDs are reserved. A conflicting custom definition is not loaded as an official test. Existing saved scores and answers are kept; an unfinished conflicting session cannot be resumed as a different test.'}
for f in sorted(b.glob('*.html')):
 v=f.read_text()
 assert '?v=1.4.2' in v
 v=v.replace('?v=1.4.2','?v='+a.version)
 if f.name=='使用說明.html':
  for v0,v1 in changes.items():assert v.count(v0)==1;v=v.replace(v0,v1)
 (s/f.name).write_text(v)
class Links(HTMLParser):
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k not in ('src','href') or not v or v.startswith('#'):continue
   url=urlparse(v)
   if url.scheme or url.netloc:continue
   rel=unquote(url.path);assert (s/rel).is_file(),rel
for f in s.glob('*.html'):Links().feed(f.read_text())
assert not (s/'data/resume').exists() and not any(s.rglob('exam-lock.json'))
assert {f.relative_to(s).as_posix() for f in (s/'audio').rglob('*') if f.is_file()}==planned
assert all('1.4.2' not in f.read_text() for f in [*s.glob('*.html'),s/'data/catalog.js'])
summary=dict(status='private-held-candidate-no-public-readiness',tentativeVersion=a.version,t02FinalQualificationClaimed=False,t02LabelOnlyApplied=bool(a.t02_label_proof),rawT02CandidateSha256=t2_raw_sha,t02PlanSha256=dh(t2['listeningPlan']),t02EvidenceGatePassedByThisAssembly=False,namespaceAppSha256=sha(prior_app),files={f.relative_to(s).as_posix():sha(f) for f in sorted(s.glob('*.html'))},catalogSha256=sha(s/'data/catalog.js'),packs=packproof,exactMediaAssets=len(planned),previewAssets=14,totalRuntimeBytes=sum(f.stat().st_size for f in s.rglob('*') if f.is_file()),preReleaseHistoryShipped=False,lockStatus='not generated',releaseReady=False)
wr(a.out/'proof-summary.json',summary)
report=copy.deepcopy(old);report['assets']=active;report['mapping']={r:v for r,v in old['mapping'].items() if v in planned};report['packs']=packproof; report['status']=summary['status']
wr(a.out/'asset-report.json',report);print(json.dumps(summary,ensure_ascii=False,indent=2))
