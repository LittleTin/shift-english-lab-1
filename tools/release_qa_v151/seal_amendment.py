#!/usr/bin/env python3
"""Separately pin a qualified amendment; never replace baseline or source locks."""
import argparse,tempfile,shutil
from pathlib import Path
import amendment_audit as A
import exam_lock as L
SUPPLEMENT={'nativeOnePlayAndSameFileResume','physicalContinuityAndSemantics','scoredJpegEquivalence','unchangedHistoricalAttemptScoring'}
def need(x,m):L.need(x,m)
def digest(x):return L.sha(L.canonical(x))
def evidence(evidence_root,rows,expected):
 need(type(rows)==dict and set(rows)==expected,'missing or extra QA gate names')
 files=set()
 for name,x in rows.items():
  need(type(x)==dict and set(x)=={'artifact','sha256','status'} and x['status']=='pass'and L.is_sha(x['sha256']),'nonpassing/unpinned QA gate: '+name)
  need(L.sha(L.bytes_at(evidence_root,x['artifact']))==x['sha256'],'QA artifact changed: '+name)
  files.add(x['artifact'])
 need(len(files)==len(expected),'a single artifact may not satisfy every gate')
def check_qa(qa,scope,prior,audit,inv,root):
 need(set(qa)=={'format','release','priorRelease','baselinePolicyCanonicalSha256','approvalScopeCanonicalSha256','auditCanonicalSha256','exams','additionalIndependentGates'},'malformed amendment QA bundle')
 need(qa['format']=='shift-amendment-post-qa-v1' and qa['release']==scope['release'] and qa['priorRelease']==prior['release'] and scope['release']!=prior['release'],'QA for wrong release/transition')
 need(qa['baselinePolicyCanonicalSha256']==digest(prior) and qa['approvalScopeCanonicalSha256']==digest(scope) and qa['auditCanonicalSha256']==digest(audit),'QA does not bind exact baseline/approved scope and actual audit')
 need(audit['physicalCodecAndGapChecks'] and audit['strictWholeScope'] and set(inv)==set(qa['exams'])==A.TESTS,'requires full firsthand physical scope audit and each qualified exam')
 evidence(root,qa['additionalIndependentGates'],SUPPLEMENT)
 for t,row in qa['exams'].items():
  need(set(row)=={'format','examId','release','inventorySha256','gates'} and row['format']=='shift-post-qa-receipt-v1' and row['examId']==t and row['release']==scope['release'],'malformed per-exam QA receipt')
  need(row['inventorySha256']==digest(inv[t])==audit['exams'][t]['proposedInventorySha256'],'per-exam evidence is for wrong amended inventory')
  evidence(root,row['gates'],L.GATES)
def run(oldsrc,oldsite,newsrc,newsite,old_policy,scope,qa,evidence_root,out,external_pins):
 need(not out.exists() and not out.is_symlink() and out.parent.is_dir() and out.parent.resolve()==out.parent.absolute(),'new output directory must be absent with unaliased parent')
 need(all(not out.resolve().is_relative_to(x) for x in (oldsrc,oldsite,newsrc,newsite)),'output must be external to original and candidate source/site')
 inv={}
 with tempfile.TemporaryDirectory(prefix='.amendment-check-',dir=out.parent) as work:
  tmp=Path(work)
  audit=A.audit(oldsrc,oldsite,newsrc,newsite,old_policy,scope,tmp/'local-reperformed-audit.json',inventory_sink=inv)
  check_qa(qa,scope,old_policy,audit,inv,evidence_root)
  stage=tmp/'qualified';stage.mkdir()
  pins={}
  for t in sorted(A.TESTS):
   # The established shape has no amendment slot. Store the new exact inventory's
   # QA binding in its compatibility slot; preserve the untouched first lock in
   # the prior trusted artifact and the chain outside this record.
   payload=dict(format='shift-whole-exam-lock-v1',status='locked',release=scope['release'],initialQaEvidence=qa['exams'][t],inventory=inv[t])
   body=L.canonical(dict(**payload,integritySha256=digest(payload)))
   pins[t]=L.sha(body);f=stage/t/'exam-lock.json';f.parent.mkdir();L.output(f,body)
  next_policy=dict(format=old_policy['format'],release=scope['release'],expectedExams=old_policy['expectedExams'],baselineLocks=pins,initialExams={})
  L.output(stage/'next-external-baseline-policy.json',L.canonical(next_policy))
  chain=dict(format='shift-amended-lock-trust-chain-v1',status='local-verified-lock-package-not-adopted-not-published',priorRelease=old_policy['release'],release=scope['release'],priorLockPins=old_policy['baselineLocks'],nextLockPins=pins,priorBaselinePolicyCanonicalSha256=digest(old_policy),nextBaselinePolicyCanonicalSha256=digest(next_policy),approvedScopeCanonicalSha256=digest(scope),postQaCanonicalSha256=digest(qa),auditCanonicalSha256=digest(audit),externalInputPins=external_pins)
  L.output(stage/'amendment-trust-chain.json',L.canonical(chain))
  shutil.copyfile(tmp/'local-reperformed-audit.json',stage/'reperformed-audit.json')
  stage.rename(out)
 return chain
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__)
 for k in ('old-source','old-site','new-source','new-site','trusted-baseline-policy','approved-scope','post-qa','evidence-root','out'):a.add_argument('--'+k,required=True,type=Path)
 for k in ('trusted-baseline-policy-sha256','approved-scope-sha256','post-qa-sha256'):a.add_argument('--'+k,required=True)
 z=a.parse_args()
 pins=dict(trustedBaselinePolicy=z.trusted_baseline_policy_sha256,approvedScope=z.approved_scope_sha256,independentPostQa=z.post_qa_sha256)
 po=L.policy_load(z.trusted_baseline_policy,pins['trustedBaselinePolicy']);sc=A.scope_load(z.approved_scope,pins['approvedScope']);qa=L.pinned(z.post_qa,pins['independentPostQa'])
 print(run(L.norm(z.old_source),L.norm(z.old_site),L.norm(z.new_source),L.norm(z.new_site),po,sc,qa,L.norm(z.evidence_root),z.out,pins))
