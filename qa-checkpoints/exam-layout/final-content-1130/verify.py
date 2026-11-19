#!/usr/bin/env python3
"""Local immutable-evidence assembly, not release or audio creation."""
import argparse,copy,hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
D=Path(__file__).resolve().parent
assert not sys.flags.optimize
def sha(a):return hashlib.sha256(a).hexdigest()
def dig(x):return sha(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
def load(p):return json.loads(p.read_bytes())
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def git(*a):return subprocess.check_output(['git','-C',str(repo),*a])
def index(rows,k):return {r[k]:r for r in rows}
def link(a,b):
 b.parent.mkdir(parents=True,exist_ok=True)
 try:os.link(a,b)
 except OSError:shutil.copyfile(a,b)
P=argparse.ArgumentParser()
for k in ('repo','historical','test-01','test-02','test-03','out'):P.add_argument('--'+k,required=True,type=Path)
P.add_argument('--work',default='1968b72a3eb23d84e718ed787bd239113e2f3791')
z=P.parse_args()
repo=z.repo.resolve();H=z.historical.resolve();A=H/'qa-checkpoints'
sys.path[:0]=[str(A/'exam-layout/reconcile'),str(A/'exam-layout/difficulty')]
from reconcile import run,assets
from difficulty_gate import report as audit_difficulty
expected=load(D/'proof-summary.json'); chain=load(D/'replay-chain.json')
assert z.work==expected['workRef']==chain['workRef'] and git('rev-parse','--verify',z.work+'^{commit}').decode().strip()==z.work
assert sha((H/'proof-summary.json').read_bytes())==expected['historicalSummarySha256']
for k,p in chain['gitArtifactSha256'].items():assert sha(git('show',z.work+':'+k))==p,k
for t,row in chain['exams'].items():
 previous=row['replayStartPlanSha256']
 for info in row['steps']:
  assert info['beforePlanSha256']==previous,(t,info)
  previous=info['afterPlanSha256']
 assert previous==row['finalListeningPlanSha256']
out=z.out.resolve();assert not out.exists() and not out.is_relative_to(repo) and not out.is_relative_to(H)
out.mkdir();site=out/'assembled-canonical';site.mkdir()
tool=out/'tooling';tool.mkdir()
for f,r in {'add_pack.py':'tools/add_pack.py','validate_exam.py':'tools/validate_exam.py','layout.py':'qa-checkpoints/exam-layout/layout.py'}.items():
 (tool/f).write_bytes(git('show',z.work+':'+r))
paths=['assets','audio','qa-checkpoints/verified-items','qa-checkpoints/difficulty']
pr=subprocess.Popen(['git','-C',str(repo),'archive',z.work,*paths],stdout=subprocess.PIPE)
with tarfile.open(fileobj=pr.stdout,mode='r|') as t:t.extractall(out/'work-tree',filter='data')
assert pr.wait()==0
tree=out/'work-tree'; led=tree/'qa-checkpoints/verified-items'; dif=tree/'qa-checkpoints/difficulty'
packs={t:(getattr(z,t.replace('-','_')),row['finalListeningPlanSha256']) for t,row in chain['exams'].items()}
for t,(f,_) in packs.items():assert sha(f.read_bytes())==expected['exams'][t]['listeningSourceSha256'],t
splices=load(H/'splices.json')
merged={}; proofs={}
for test,(fn,expect) in packs.items():
 p=load(fn);ori=copy.deepcopy(p); hist=load(H/'reading-merged'/f'{test}.json'); raw=load(H/'hydrated/data'/f'{test}.json')
 assert p['testId']==test and dig(p['listeningPlan']).startswith(expect)
 assert [q['number'] for q in p['questions']]==list(range(1,201)) and p['questions'][100:]==raw['questions'][100:]
 qs=index(hist['questions'],'number');revs=index(hist['groups'],'id');rawgs=index(raw['groups'],'id')
 for s in splices:
  if s['testId']!=test:continue
  assert min(s['numbers'])>=101
  for n in s['numbers']:
   assert p['questions'][n-1]==raw['questions'][n-1]
   p['questions'][n-1]=qs[n]
  if g:=s.get('oldGroupId'):
   i,=[i for i,x in enumerate(p['groups']) if x['id']==g]
   assert p['groups'][i]==rawgs[g]; p['groups'][i]=revs[qs[s['numbers'][0]]['groupId']]
 assert p['questions'][:100]==ori['questions'][:100]
 for k in ('listeningPlan','previousListeningPlan','alternateListeningPlans','legacyQuestions'):
  assert p.get(k)==ori.get(k)
 merged[test]=p
 proofs[test]=dict(listeningSourceSha256=sha(fn.read_bytes()),listeningPlanCanonicalSha256=dig(p['listeningPlan']),retainedHistoryCanonicalSha256={k:dig(p[k]) for k in ('previousListeningPlan','alternateListeningPlans','legacyQuestions') if k in p})
 f=site/'data'/f'{test}.json';write(f,p)
 body=json.dumps(p,ensure_ascii=False,allow_nan=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
 f.with_suffix('.js').write_text('window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('+body+');\n')
refs=set(k for p in merged.values() for k in assets(p))
for f in led.glob('test-*/Q[0-9][0-9][0-9].json'):
 row=load(f);refs.update(assets(row.get('group')));refs.update(x['path'] for x in row.get('audio',[]) if isinstance(x,dict) and 'path' in x)
for r in sorted(refs):
 assert not Path(r).is_absolute() and '..' not in Path(r).parts
 src=next((f for b in (tree,H/'hydrated') if (f:=b/r).is_file()),None)
 if src is None:raise FileNotFoundError(r)
 link(src,site/r)
# Catalog is not evidence, but the original registered catalog makes the canonical validator runnable.
(site/'data/catalog.js').write_bytes(git('show',z.work+':data/catalog.js'))
ev,validated=run(site,led,{},merged);write(out/'evidence-full.json',ev)
levels,_=audit_difficulty(led,dif);write(out/'difficulty-full.json',levels)
summary=dict(status='offline-complete-content-only-not-release',workRef=z.work,workSource='exact one immutable Git tree',historicalSummarySha256=sha((H/'proof-summary.json').read_bytes()),readingRecipeCount=len(splices),readingSpliceQuestions=sum(len(x['numbers']) for x in splices),canonicalAssetCount=len(refs),exams={t:dict(**proofs[t],accepted=len(e['accepted']),missing=e['missing'],issues=e['issues'],holds=e['holds']) for t,e in ev['exams'].items()},difficultyReviewed=levels.get('reviewed'),difficultyGateComplete=levels.get('difficultyGateComplete'),difficultyTargets={t:{k:v for k,v in row.items() if k not in ('accepted','issues')} for t,row in levels.get('exams',{}).items()})
write(out/'proof-summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
assert ev['evidenceComplete'] and all(len(e['accepted'])==200 and not any(e[k] for k in ('missing','issues','holds')) for e in ev['exams'].values())
for t in packs:
 before,after=merged[t],validated[t]
 for k in ('previousListeningPlan','alternateListeningPlans'):
  assert before.get(k)==after.get(k),(t,k,'ledger may not modify prior plans')
 if 'legacyQuestions' in before:
  assert not {q['id'] for q in before['legacyQuestions']}&{q['id'] for q in after['questions']}
  after['legacyQuestions']=before['legacyQuestions']
 plan=copy.deepcopy(before['listeningPlan'])
 oldnew={x['id']:y['id'] for x,y in zip(before['questions'],after['questions']) if x['id']!=y['id']}
 for f in plan['frames']:
  if f.get('questionId') in oldnew:f['questionId']=oldnew[f['questionId']]
 assert after['listeningPlan']==plan,(t,'only ledger-directed active question ID rebinding permitted')
 proofs[t]['canonicalPlanAfterEvidenceSha256']=dig(plan)
 proofs[t]['activeQuestionIdRebinding']=oldnew
 qdiff=[x['number'] for x,y in zip(before['questions'],after['questions']) if x!=y]
 gdiff=[x['id'] for x,y in zip(before['groups'],after['groups']) if x!=y]
 print('Ledger-authoritative snapshots',t,qdiff,gdiff)
 f=site/'data'/f'{t}.json';write(f,after)
 body=json.dumps(after,ensure_ascii=False,allow_nan=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
 f.with_suffix('.js').write_text('window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('+body+');\n')
 merged[t]=after

for t in packs:
 assert proofs[t]['canonicalPlanAfterEvidenceSha256']==expected['exams'][t]['canonicalPlanAfterEvidenceSha256'],t
 assert sha((site/'data'/f'{t}.json').read_bytes())==expected['exams'][t]['canonicalPackSha256'],t
 summary['exams'][t].update(proofs[t])
write(out/'proof-summary.json',summary)
subprocess.run([sys.executable,str(tool/'validate_exam.py'),'--site',str(site)],check=True,stdout=(out/'validator.log').open('w'))
if True:
 source=out/'authoring'; regenerated=out/'authoring-roundtrip'
 subprocess.run([sys.executable,str(tool/'layout.py'),'split','--site',str(site),'--source',str(source)],check=True)
 subprocess.run([sys.executable,str(tool/'layout.py'),'build','--source',str(source),'--site',str(regenerated)],check=True)
 assert all(load(regenerated/'data'/f'{t}.json')==p for t,p in merged.items())
 write(out/'authoring-proof.json',dict(status='three exact canonical split/build roundtrips with archived legacy preserved',canonicalPackSha256={t:sha((site/'data'/f'{t}.json').read_bytes()) for t in packs},roundtripPackSha256={t:sha((regenerated/'data'/f'{t}.json').read_bytes()) for t in packs}))
