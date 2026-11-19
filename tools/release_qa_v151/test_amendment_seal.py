from pathlib import Path
import copy,hashlib,tempfile,unittest
import seal_amendment as S
import exam_lock as L
class GateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  self.prior={'release':'1.5.0'}
  self.approved={'release':'1.5.1'}
  self.inv={k:{'exam':k}for k in S.A.TESTS}
  self.audit=dict(physicalCodecAndGapChecks=True,strictWholeScope=True,exams={k:{'proposedInventorySha256':S.digest(v)}for k,v in self.inv.items()})
  def evidence(names):
   out={}
   for n in names:
    path=f'{n}.json'; body=n.encode();(self.root/path).write_bytes(body)
    out[n]=dict(status='pass',artifact=path,sha256=hashlib.sha256(body).hexdigest())
   return out
  self.qa=dict(format='shift-amendment-post-qa-v1',release='1.5.1',priorRelease='1.5.0',baselinePolicyCanonicalSha256=S.digest(self.prior),approvalScopeCanonicalSha256=S.digest(self.approved),auditCanonicalSha256=S.digest(self.audit),exams={t:dict(format='shift-post-qa-receipt-v1',examId=t,release='1.5.1',inventorySha256=S.digest(v),gates=evidence(L.GATES))for t,v in self.inv.items()},additionalIndependentGates=evidence(S.SUPPLEMENT))
 def check(self):
  S.check_qa(self.qa,self.approved,self.prior,self.audit,self.inv,self.root)
 def test_exact_gate_chain(self):self.check()
 def test_missing_sup_gate_rejected(self):
  self.qa['additionalIndependentGates'].pop('nativeOnePlayAndSameFileResume')
  with self.assertRaises(L.LockError):self.check()
 def test_structural_only_not_physical(self):
  self.audit['physicalCodecAndGapChecks']=False;self.qa['auditCanonicalSha256']=S.digest(self.audit)
  with self.assertRaises(L.LockError):self.check()
 def test_different_scope_or_old_pin_rejected(self):
  self.prior['baselineLocks']={'test-01':'0'*64}
  with self.assertRaises(L.LockError):self.check()
 def test_mismatch_new_inventory_rejected(self):
  self.inv['test-01']['drift']=True
  with self.assertRaises(L.LockError):self.check()
 def test_evidence_artifact_content_change(self):
  (self.root/'legacyResume.json').touch()
  (self.root/'nativeOnePlayAndSameFileResume.json').write_text('tampered')
  with self.assertRaises(L.LockError):self.check()
