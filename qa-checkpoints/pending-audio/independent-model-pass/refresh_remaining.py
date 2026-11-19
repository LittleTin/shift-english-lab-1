"""Read pinned stage Git and produce a local audio-only restart index. No synthesis."""
import argparse,json,subprocess
from collections import Counter, defaultdict
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--repo',required=True)
p.add_argument('--ref',required=True,help='full stage commit')
p.add_argument('--out',required=True,type=Path)
a=p.parse_args()
run=lambda *args:subprocess.check_output(['git','-C',a.repo,*args])
assert a.ref==run('rev-parse','--verify','--end-of-options',a.ref+'^{commit}').decode().strip()
r=lambda path:json.loads(run('show',f'{a.ref}:{path}'))
base='qa-checkpoints/pending-audio/inventory-0605'
inv=r(base+'/index.json')
out=dict(stageCommit=a.ref,onlyExistingAudioAndProspectiveDrafts=True,
 specBlob=run('rev-parse',f'{a.ref}:SHIFT-SPEC.md').decode().strip(),
 state='not-release-approval',tests={})
for test in sorted(inv['slices']):
 pack=r(f'data/{test}.json'); old_approved=set(); ledger=f'qa-checkpoints/verified-items/{test}'
 reg=run('ls-tree','-r','--name-only',a.ref,ledger).decode().splitlines()
 for pth in reg:
  d=r(pth);q=d.get('activeQuestion',{})
  if d['status']=='verified-item-not-published' and d['scope']=='listening':
   assert q['testId']==test and 1<=q['number']<=100
   assert pth==f'{ledger}/Q{q["number"]:03}.json'
   old_approved.add(q['number'])
 missing=set(range(1,101))-old_approved
 pending=defaultdict(list)
 for piece in inv['slices'][test]:
  path=base+'/'+piece
  for d in r(path)['groups']:
   for n in d['questions']:
    if n in missing:pending[n].append((d,path))
 assert set(pending)==missing
 groups=defaultdict(list)
 for q in pack['questions'][:100]:groups[q['groupId']].append(q['number'])
 by={q['number']:q for q in pack['questions']}
 values=[]
 for number in sorted(missing):
  q=by[number]; n=number; index=pending[n]; gid=q['groupId']
  assert all(x['group']==gid and x['part']==q['part'] for x,_ in index)
  values.append(dict(number=n,questionId=q['id'],groupId=gid,part=q['part'],
        concurrentlyVerifiedSiblings=sorted(set(groups[gid])&old_approved),
        allGroupItemsHeld=set(groups[gid])<=missing,
        versionedInventory=[dict(path=path,tokens=x['focus'],mode=x['scopedMode'],type=x['status']) for x,path in index]))
 out['tests'][test]=dict(verified=len(old_approved),remaining=len(missing),groupsWithHolds=len({x['groupId'] for x in values}),items=values)
with a.out.open('x') as handle:json.dump(out,handle,ensure_ascii=False,indent=2);handle.write('\n')
print({x:d['remaining'] for x,d in out['tests'].items()})
