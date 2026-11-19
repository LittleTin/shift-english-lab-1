"""Plan exact, deduplicated unverified audio windows for later qualified review."""
import argparse, collections, hashlib, json, math, re, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--repo',required=True)
p.add_argument('--ref',required=True)
p.add_argument('--index',required=True,type=Path)
p.add_argument('--assets',required=True,type=Path)
p.add_argument('--out',required=True,type=Path)
a=p.parse_args()
ref=a.ref
git=lambda *args:subprocess.check_output(['git','-C',a.repo,*args])
assert git('rev-parse','--verify','--end-of-options',ref+'^{commit}').decode().strip()==ref
r=lambda path:json.loads(git('show',ref+':'+path))
idx=json.loads(a.index.read_text());assert idx['stageCommit']==ref and idx['state']=='not-release-approval'
roles={
 'practice':('practicePassage',),
 'formal-passage':('formalPassage',),
 'formal-stem':('formalStem',),
 'shared-passage':('practicePassage','formalPassage'),
 'shared+stem':('practicePassage','formalPassage','formalStem'),
 'both-distinct':('practicePassage','formalPassage'),
}
clips={}; byfile={}; claimed=set()
for test,record in idx['tests'].items():
 for item in record['items']:
  n=item['number']; key=(test,n);assert key not in claimed
  claimed.add(key)
  found=0
  for old in item['versionedInventory']:
   m=old['mode'];assert m in roles
   inv=r(old['path'])['groups']
   old_rows=[x for x in inv if n in x['questions'] and x['group']==item['groupId'] and
     x['focus']==old['tokens'] and x['scopedMode']==m]
   assert len(old_rows)==1
   row=old_rows[0]
   for role in roles[m]:
    clip=row[role]
    if isinstance(clip,dict):clip=[clip]
    seen=0
    for x in clip:
     if role=='formalStem' and x.get('questionId')!=item['questionId']:continue
     url,lo,hi,digest=(x[k] for k in ('file','start','end','sha256'))
     assert re.fullmatch(r'audio/(?:[a-zA-Z0-9_.-]+/)*[a-zA-Z0-9_.-]+\.(mp3|wav|m4a)',url)
     assert not any(k in ('.','..') for k in url.split('/')) and 0 <= lo < hi and math.isfinite(hi)
     file=(a.assets/url).resolve()
     assert file.is_relative_to(a.assets.resolve()) and file.is_file()
     if url not in byfile:byfile[url]=hashlib.sha256(file.read_bytes()).hexdigest()
     assert byfile[url]==digest
     k=(url,lo,hi)
     entry=clips.setdefault(k,dict(asset=url,start=lo,end=hi,sha256=digest,targets=[]))
     targets=dict(exam=test,scope=f'Q{n:03}',group=item['groupId'],questionId=item['questionId'],
         requiredCheck=old['tokens'],audioRole=role,protectedSiblings=item['concurrentlyVerifiedSiblings'],
         olderInventoryEvidence=old['path'])
     if targets not in entry['targets']:entry['targets'].append(targets)
     found+=1;seen+=1
    if role in ('formalStem','formalPassage','practicePassage'):assert seen
  assert found
scoped=sum(len(x['targets']) for x in clips.values()); seconds=round(sum(x['end']-x['start'] for x in clips.values()),2)
result=dict(stage=ref,verifiedByProgram='exact existing asset hashes and logged scoped intervals only',
   noClipsExportedOrQualifiedListeningHere=True,
   questionCount=len(claimed),uniqueWindows=len(clips),roleTargets=scoped,totalSinglePassSeconds=seconds,
   clipWindows=list(clips.values()))
with a.out.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print({k:result[k] for k in ('questionCount','uniqueWindows','roleTargets','totalSinglePassSeconds')})
