#!/usr/bin/env python3
"""Normalize a separately qualified T02 label-only receipt, without issuing approval."""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter
A=argparse.ArgumentParser()
for k in ('qualified','source','source-proof','base-index','out-label','out-index'):A.add_argument('--'+k,type=Path,required=True)
A.add_argument('--expected-source-sha',required=True);z=A.parse_args()
assert not z.out_label.exists() and not z.out_index.exists()
rd=lambda f:json.loads(f.read_bytes())
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def wr(f,x):f.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
s=rd(z.source);doc=rd(z.source_proof);x=rd(z.qualified/'test-02.json');y=rd(z.qualified/'difficulty-materialization.json')
h=sha(z.source);out=sha(z.qualified/'test-02.json')
assert h==doc['outputSha256']==y['sourcePackSha256']==z.expected_source_sha and out==y['outputPackSha256']; assert y['noBrowserOrLock'] is True
assert set(s)==set(x) and all(v==x[k] for k,v in s.items() if k!='questions')
assert len(x['questions'])==200 and len(y['all200ExactDecisions'])==200
for q0,q1 in zip(s['questions'],x['questions'],strict=True):
 assert {k:v for k,v in q0.items() if k!='difficulty'}=={k:v for k,v in q1.items() if k!='difficulty'}
 assert q1['difficulty']==y['all200ExactDecisions'][str(q1['number'])]['reviewedLevel']
scope=doc['candidateOnlyNumbers'];assert len(scope)==15
index=rd(z.base_index)
for n in scope:
 row={}
 for role in ('verified-items','difficulty'):
  p=z.qualified/f'qa-checkpoints/{role}/test-02/Q{n:03}.json'; row[role]=dict(path=str(p),sha256=sha(p))
 assert rd(Path(row['verified-items']['path']))['activeQuestion']==x['questions'][n-1] and str(n) not in index['test-02']
 index['test-02'][str(n)]=row
assert len(index['test-02'])==24
sections={}
for section,lo,hi in [('listening',0,100),('reading',100,200)]:
 v=dict(Counter(q['difficulty'] for q in x['questions'][lo:hi]));assert v==y['distribution'][section]
 assert v['intermediate']>max(v['foundation'],v['advanced']) and min(v['foundation'],v['advanced'])>=3
 sections[section]=v
wr(z.out_label,dict(status='exact-editor-qualified-label-only-no-browser-or-lock',sourcePackSha256=h,outputPackSha256=out,difficultyGatePass=True,applied=True,reviewed=200,sourceReviewReceiptSha256=sha(z.qualified/'difficulty-materialization.json'),sections=sections))
wr(z.out_index,index)
