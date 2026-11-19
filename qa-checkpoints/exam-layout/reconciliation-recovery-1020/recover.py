#!/usr/bin/env python3
"""Read-only SHIFT scoped ledger recovery against an exact audio composition."""
import argparse,copy,gzip,hashlib,io,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path

WORK='92bf2a621452ac8e54db87eb50f4f0cd9456c379'
BASE='8ab882d065cd33550ab8e694cc035c5135f1b146'
RECEIPT='b58a19760e56d1349a53f526a9037aad0d2afcb3ceb13db97aeba3d5915c271b'
PACKS={
'test-01':'b3a71869dfd1d0ec036ffe36c29d066ea05ec7bf08b105ed8c8b62e22bd17b9b',
'test-02':'9ec5c813dda01db241e4d21d81d3c025947d6f19a6c7f5a5007a9d8dfbb5c232',
'test-03':'af668512d7864d3af783c006d2930058d79c15d677c64bca924c5ff12afcfdc3'}
PATHS=[
'qa-checkpoints/verified-items','qa-checkpoints/difficulty',
'qa-checkpoints/exam-layout/reconcile','qa-checkpoints/exam-layout/difficulty',
'qa-checkpoints/reading-02-03','qa-checkpoints/test01-candidate.patch.gz']
REFS=[
'043b91761f63062708d70f7cda3a6b2046cd4cf9',
'411434806d3e9df5831910bb23de1d6129335731',
'5ae438b0b6db88bdddfca7ba1328da8a10b08c31',
'5caabdb55aa0faca2ce7dc76bb33723c515a9c42',
'8b45475885b83062f4a50a7f6589bf9757b71792',
'92b6c686b5166028fd3b16a4d1120938933134d7',
'a3370773e33d4dfa03c4f273abd2b2cd193338fc',
'db910d2fa740dd6e916f9e9dd6b8d6ea70de547d']
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--repo',required=True,type=Path)
ap.add_argument('--audio-stage',required=True,type=Path,help='Root containing proof.json and site/ from the pinned audio composer')
ap.add_argument('--out',required=True,type=Path)
args=ap.parse_args()
assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE'),'Keep all integrity guards enabled'
d=args.out.resolve(); r=args.repo.resolve(); astage=args.audio_stage.resolve(); site=astage/'site'
assert not d.exists() and not d.is_relative_to(r) and not d.is_relative_to(astage),'Choose absent scratch output outside both inputs'
git=lambda *a:subprocess.check_output(['git','-C',str(r),*a])
load=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(astage/'proof.json')==RECEIPT,'Unexpected audio composition receipt'
assert all(sha(site/'data'/f'{t}.json')==h for t,h in PACKS.items()),'Audio stage pack drift'
for ref in (WORK,BASE,*REFS):
 assert git('rev-parse','--verify',ref+'^{commit}').decode().strip()==ref
d.mkdir(parents=True); qa=d/'qa-checkpoints'
with tarfile.open(fileobj=io.BytesIO(git('archive',WORK,*PATHS)),mode='r:') as archive:
 archive.extractall(d,filter='data')
sys.path.insert(0,str(qa/'exam-layout/reconcile'));sys.path.insert(0,str(qa/'exam-layout/difficulty'))
from rotation import Repo,rotate,EXAMS
from reconcile import run
from difficulty_gate import report
repo=Repo(r); base=BASE; ref=WORK
old={t:repo.row(base,f'data/{t}.json') for t in EXAMS}
rotated,splices,retained=rotate(repo,ref,old,repo.row(ref,'question-reserve/index.json'),load(qa/'exam-layout/reconcile/baseline-8ab882d-overrides-with-part5.json'))
x=d/'hydrated'; x.mkdir()
for p in ('assets','audio','data'): shutil.copytree(site/p,x/p,copy_function=os.link)
# Restore only exact graphics required by recorded approvals.
patch=gzip.decompress((qa/'test01-candidate.patch.gz').read_bytes())
subprocess.run(['git','apply','--include=assets/scenes/warehouse-cart-r2.svg','--include=assets/scenes/cafe-handoff-r2.svg','-'],input=patch,cwd=x,check=True)
for f in sorted((qa/'reading-02-03').rglob('*.svg')):
 dest=x/'assets/graphics'/f.name
 if not dest.exists(): shutil.copyfile(f,dest)
for s in splices:
 if 'addedGraphic' not in s:continue
 item=s['addedGraphic']; target=x/item['runtimePath']
 src=f"question-reserve/{s['testId']}/{s['oldGroupId']}/media/"+target.name
 b=retained[src]; assert hashlib.sha256(b).hexdigest()==item['sha256'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
for q in (qa/'verified-items').glob('*/*.json'):
 item=load(q); rel=item.get('group',{}).get('image') if isinstance(item.get('group'),dict) else None
 if rel and (x/rel).exists():assert sha(x/rel)==item['imageSha256'],str(q)
# Verify each approved revised reading identity in the current work-branch ledger; merge only numbered reading changes after confirming identical source section.
merged={}
for t in EXAMS:
 source=load(site/'data'/f'{t}.json'); before=copy.deepcopy(source)
 only=[n for s in splices if s['testId']==t for n in s['numbers']]
 for n in only:
  assert before['questions'][n-1]==old[t]['questions'][n-1],(t,n,'raw source variation')
  assert (qa/'verified-items'/t/f'Q{n:03}.json').read_bytes()==repo.read(ref,f'qa-checkpoints/verified-items/{t}/Q{n:03}.json')
  source['questions'][n-1]=rotated[t]['questions'][n-1]
 for s in splices:
  if s['testId']!=t or not s.get('oldGroupId'):continue
  gid=s['oldGroupId']; i=next(i for i,g in enumerate(source['groups']) if g['id']==gid)
  assert source['groups'][i]==next(g for g in old[t]['groups'] if g['id']==gid)
  newgid=source['questions'][s['numbers'][0]-1]['groupId']
  source['groups'][i]=next(g for g in rotated[t]['groups'] if g['id']==newgid)
 for k in ('listeningPlan','previousListeningPlan','alternateListeningPlans','legacyQuestions'):
  assert source.get(k)==before.get(k)
 merged[t]=source
raw,_=run(site,qa/'verified-items',{})
verify,_=run(x,qa/'verified-items',{},merged)
levels,_=report(qa/'verified-items',qa/'difficulty')
reason=lambda z:z.split(': ',1)[1].split("'",1)[0].rstrip()
from collections import Counter
raw_kinds=Counter(reason(issue) for e in raw['exams'].values() for issue in e['issues'])
out={
 'scope':'complete-ledger-structural-dry-run-not-release',
 'workRef':WORK,'rotationBase':BASE,'audioStageReceiptSha256':RECEIPT,'audioStagePackSha256':PACKS,
 'rotationRecipeCount':len(splices),
 'rotationQuestionCount':sum(len(row['numbers']) for row in splices),
 'rawIssuePatterns':dict(sorted(raw_kinds.items())),
 'exams':{t:{'accepted':len(e['accepted']),'missingListening':e['missing'],'holds':len(e['holds']),'issues':len(e['issues'])} for t,e in verify['exams'].items()},
 'difficultyGateComplete':levels['difficultyGateComplete'],
}
assert [(z['accepted'],len(z['missingListening']),z['issues'],z['holds']) for z in out['exams'].values()]==[(175,25,0,0),(180,20,0,0),(187,13,0,0)]
assert all(n<=100 for z in out['exams'].values() for n in z['missingListening'])
assert sha(astage/'proof.json')==RECEIPT and all(sha(site/'data'/f'{t}.json')==h for t,h in PACKS.items()),'Input stage changed during validation'
(d/'proof-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
