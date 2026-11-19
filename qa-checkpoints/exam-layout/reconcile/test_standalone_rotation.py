"""Synthetic replacement records over actual pinned old question bytes, no repository mutations."""
import copy
import hashlib
import unittest
from rotation import rotate, dig, dump
from test_rotation import REF, R, Proxy, fixtures

SRC='5caabdb55aa0faca2ce7dc76bb33723c515a9c42'
TEST='test-01'
N=119
EP=f'qa-checkpoints/verified-items/{TEST}/Q{N}.json'
RP=f'qa-checkpoints/reconstructions/{TEST}/Q{N}.json'
ROOT=f'question-reserve/{TEST}/Q{N}/'
QP=ROOT+'question.json'; VP=ROOT+'verification.json'; MP=ROOT+'manifest.json'

class BytesProxy(Proxy):
 def read(self,ref,path):
  if ref==REF and path in self.data and isinstance(self.data[path],bytes):return self.data[path]
  return super().read(ref,path)

class StandaloneTest(unittest.TestCase):
 def setUp(self):
  self.base,self.idx,self.overrides=fixtures()
  self.repo=BytesProxy(R)
  source=R.row(SRC,EP)
  self.old=source['activeQuestion']; self.raw=R.read(SRC,EP)
  self.new=copy.deepcopy(self.old)
  self.new.update(id=self.old['id']+'-r2',revision=self.old['revision']+1,prompt='SYNTHETIC CHANGE ____')
  self.man=dict(status='reserved-inactive-in-work-candidate',sourceStillActive=False,sourceTest=TEST,sourceQuestionNumber=N,
                sourceCommit=SRC,sourceQuestionId=self.old['id'],sourceQuestionRevision=self.old['revision'],sourceAnswer=self.old['answer'],
                sourceEvidencePath=EP,sourceEvidenceGitBlob=R.git('rev-parse',f'{SRC}:{EP}').decode().strip(),
                sourceEvidenceSha256=hashlib.sha256(self.raw).hexdigest(),media=[],format='standalone-text-only-part-5',
                notActiveHere=True,replacementQuestionId=self.new['id'])
  self.entry=dict(sourceTest=TEST,number=N,path=MP.removeprefix('question-reserve/'),status=self.man['status'])
  self.idx['standalone']=[self.entry]
  self.recipe=dict(kind='replace-standalone-part-5-by-exact-old-scope',notPublished=True,questionNumber=N,
                   sourceQuestionId=self.old['id'],newQuestionId=self.new['id'],replacementEvidence=EP,previousReserve=MP,
                   questionCanonicalSha256=dig(self.new))
  self.current=dict(source,activeQuestion=self.new,originalQuestion=self.old,retiredSourceReference=VP)
  self.repo.data.update({VP:self.raw,QP:self.old,MP:self.man,RP:self.recipe,EP:self.current})
  base_q=self.base[TEST]['questions'][N-1]
  if base_q!=self.old:self.overrides[f'{TEST}/Q{N}']=dict(observedSha256=dig(base_q),verifiedSha256=dig(self.old))
 def run_fixture(self):return rotate(self.repo,REF,self.base,self.idx,self.overrides)
 def test_success_and_invariants(self):
  expected,_,_=rotate(R,REF,self.base,{k:v for k,v in self.idx.items() if k!='standalone'},
                     {k:v for k,v in self.overrides.items() if k!=f'{TEST}/Q{N}'})
  actual,splices,retained=self.run_fixture()
  self.assertEqual(splices[-1]['numbers'],[N])
  self.assertEqual(actual[TEST]['questions'][N-1],self.new)
  expected[TEST]['questions'][N-1]=self.new
  self.assertEqual(expected,actual)
  self.assertEqual(retained[VP],self.raw)
  self.assertEqual(retained[QP],dump(self.old).encode())
 def test_pending_provenance_no_replacement(self):
  self.man.update(status='saved-pending-replacement',sourceStillActive=True)
  self.man.pop('replacementQuestionId')
  self.entry['status']=self.man['status']
  self.repo.data.pop(RP); self.repo.data.pop(EP)
  self.overrides.pop(f'{TEST}/Q{N}',None)
  actual,splices,retained=self.run_fixture()
  self.assertEqual(len(splices),5)
  self.assertEqual(actual[TEST]['questions'][N-1],self.base[TEST]['questions'][N-1])
  self.assertNotIn(VP,retained)
  self.repo.data[VP]=b'not an archive'
  with self.assertRaisesRegex(ValueError,'lost provenance'):self.run_fixture()
 def test_draft_authoring_is_not_adoption(self):
  self.current['status']='draft'
  with self.assertRaisesRegex(ValueError,'verification link mismatch'):self.run_fixture()
 def test_duplicate_and_orphan(self):
  self.idx['standalone'].append(self.entry)
  with self.assertRaisesRegex(ValueError,'duplicate standalone reserve'):self.run_fixture()
  self.idx.pop('standalone')
  with self.assertRaisesRegex(ValueError,'unmatched standalone reconstruction'):self.run_fixture()
 def test_malformed_and_wrong_digest(self):
  self.entry['path']='test-01/Q120/manifest.json'
  with self.assertRaisesRegex(ValueError,'index path mismatch'):self.run_fixture()
  self.entry['path']=MP.removeprefix('question-reserve/')
  self.recipe['questionCanonicalSha256']='0'*64
  with self.assertRaisesRegex(ValueError,'identity/digest mismatch'):self.run_fixture()
 def test_blocks_media_and_group(self):
  self.new['audio']='audio/unreviewed.mp3'
  self.recipe['questionCanonicalSha256']=dig(self.new)
  with self.assertRaisesRegex(ValueError,'identity/digest mismatch'):self.run_fixture()
  self.new.pop('audio');self.new['groupId']='t01-g001';self.recipe['questionCanonicalSha256']=dig(self.new)
  with self.assertRaisesRegex(ValueError,'identity/digest mismatch'):self.run_fixture()
 def test_stale_baseline_and_historic_collision(self):
  existing=self.base[TEST]['questions'][N-1]['prompt']
  self.base[TEST]['questions'][N-1]['prompt']='unapproved old prompt'
  with self.assertRaisesRegex(ValueError,'stale or unordered'):self.run_fixture()
  self.base[TEST]['questions'][N-1]['prompt']=existing
  historical=copy.deepcopy(self.new)
  historical['id']=self.new['id']
  self.base[TEST].setdefault('legacyQuestions',[]).append(historical)
  with self.assertRaisesRegex(ValueError,'duplicate/archived active ID'):self.run_fixture()

if __name__=='__main__':unittest.main()
