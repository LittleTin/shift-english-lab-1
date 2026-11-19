#!/usr/bin/env python3
"""Create offline-reviewed browser matrix input; not browser acceptance or owner lock."""
import argparse,hashlib,json
from pathlib import Path
P=argparse.ArgumentParser()
for k in ('stage','verified-bindings','source-roundtrip','out'):P.add_argument('--'+k,type=Path,required=True)
a=P.parse_args()
assert not a.out.exists()
rd=lambda f:json.loads(f.read_bytes())
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
site=a.stage/'site'; x=rd(a.verified_bindings); y=rd(a.source_roundtrip)
assert x['offlineScopeCount']==600 and x['releaseReady'] is False and y['questions']==600
assert sha(a.stage/'asset-report.json')==x['frozenReceiptSha256']
t=('test-01','test-02','test-03'); q=[]; files={}
for k in ('index.html','assets/app.js','assets/style.css','data/catalog.js'):
 files[k]=sha(site/k)
for test in t:
 rows=x['exams'][test];assert rows['status']=='exact-offline-passed' and rows['displayLabelsVerified'] is True
 for k in ('json','js'):
  path=f'data/{test}.{k}'; files[path]=sha(site/path);assert files[path]==y['matchedPackSha256'][path]
 assert files[f'data/{test}.json']==x['packRevisions'][test]['packSha256']
 for n,id,rev,v,d,qd,gd,ad,lev in rows['perItemProof']:
  q.append(dict(test=test,number=n,id=id,difficulty=lev,reviewEvidenceSha256=v,difficultyEvidenceSha256=d))
assert len(q)==600 and len({z['id'] for z in q})==600
report=rd(a.stage/'asset-report.json');med={}
for z in report['assets'].values():
 f=z['path'];h=z['encodedSha256'];assert f not in med and sha(site/f)==h
 med[f]=h
body=dict(status='approved-600-bound-release-candidate',files=files,questions=q,media=med,offlineEvidenceSha256=sha(a.verified_bindings),sourceRoundtripSha256=sha(a.source_roundtrip),ownerLockOrPublicationApproval=False)
a.out.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n')
