import copy,json,os,pathlib,sys,unittest
from rotation import Repo,EXAMS,rotate,strict,dig,media,dump,KIND
HERE=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path.cwd()
R=Repo(pathlib.Path(os.environ.get('SHIFT_TEST_REPO',str(ROOT/'shift-qa'))))
BASE=R.git('rev-parse','8ab882d065cd33550ab8e694cc035c5135f1b146').decode().strip()
REF=R.git('rev-parse','1183d26ee5a97ae050dec34ec6bb86c872adc058').decode().strip()
def fixtures():
 return ({t:R.row(BASE,f'data/{t}.json') for t in EXAMS},R.row(REF,'question-reserve/index.json'),strict((HERE/'baseline-8ab882d-overrides.json').read_bytes()))

class Tests(unittest.TestCase):
 def test_real_five_groups(self):
  b,i,o=fixtures(); now,splice,archive=rotate(R,REF,b,i,o)
  self.assertEqual([s['numbers'] for s in splice],[[147,148,149],[150,151,152],[165,166,167],[162,163,164],[153,154,155]])
  for t in EXAMS:
   self.assertEqual(set(media(b[t])),set(media(now[t])))
   self.assertEqual(b[t].get('legacyQuestions'),now[t].get('legacyQuestions'))
   self.assertEqual(b[t]['listeningPlan'],now[t]['listeningPlan'])
  self.assertEqual(len(archive),42)
  prev='043b91761f63062708d70f7cda3a6b2046cd4cf9'
  self.assertEqual(archive[f'historical-snapshots/{prev}/data/test-02.json'],R.read(prev,'data/test-02.json'))
  self.assertEqual(archive['qa-checkpoints/reconstructions/history/test-02/t02-r-p7-06.json'],R.read(REF,'qa-checkpoints/reconstructions/history/test-02/t02-r-p7-06.json'))
  sys.path.insert(0,str(HERE))
  from reconcile import pair_number
  for s in splice:
   for n in s['numbers']:
    p=f'qa-checkpoints/verified-items/{s["testId"]}/Q{n:03}.json'; q=R.row(REF,p)['activeQuestion']
    with self.assertRaisesRegex(ValueError,'explicit layout change'):pair_number(q,s['testId'],n,b[s['testId']]['questions'][n-1])
    self.assertEqual(pair_number(q,s['testId'],n,now[s['testId']]['questions'][n-1]),q)
 def test_older_baseline_stop_no_override(self):
  b,i,o=fixtures()
  with self.assertRaisesRegex(ValueError,'stale/incomplete old group'):rotate(R,REF,b,i)
 def test_stale_input_reject_even_with_override(self):
  b,i,o=fixtures(); b['test-01']['questions'][147]['promptZh']+='（被改動）'
  with self.assertRaisesRegex(ValueError,'stale or incorrect old item'):rotate(R,REF,b,i,o)
 def test_partial_group_rejected(self):
  b,i,o=fixtures(); b['test-01']['questions'][148]['groupId']='other'
  with self.assertRaisesRegex(ValueError,'stale/incomplete old group'):rotate(R,REF,b,i,o)
 def test_unused_override_rejected(self):
  b,i,o=fixtures(); o['test-02/Q160']={'observedSha256':'bad','verifiedSha256':'bad'}
  with self.assertRaisesRegex(ValueError,'unused baseline override'):rotate(R,REF,b,i,o)
 def test_hash_drift_rejected(self):
  b,i,o=fixtures(); proxy=Proxy(R)
  k=f'qa-checkpoints/reconstructions/test-01/t01-r-p7-01.json'
  x=R.row(REF,k);x['questionCanonicalSha256'][0]='0'*64;proxy.data[k]=x
  with self.assertRaisesRegex(ValueError,'replacement hash/staging mismatch'):rotate(proxy,REF,b,i,o)
 def test_already_replayed_baseline_rejected(self):
  b,i,o=fixtures(); now,_,_=rotate(R,REF,b,i,o)
  with self.assertRaisesRegex(ValueError,'stale/incomplete old group'):rotate(R,REF,now,i,o)
 def test_archive_wrong_old_key_rejected(self):
  b,i,o=fixtures(); proxy=Proxy(R)
  k='qa-checkpoints/reconstructions/history/test-02/t02-r-p7-06.json'
  x=R.row(REF,k);x['legacyQuestions'][0]['answer']='C' if x['legacyQuestions'][0]['answer']!='C' else 'D'
  proxy.data[k]=x
  with self.assertRaisesRegex(ValueError,'historical items do not match previous pack'):rotate(proxy,REF,b,i,o)
 def test_history_legacy_deduped_without_legacy_loss(self):
  b,i,o=fixtures()
  path='qa-checkpoints/reconstructions/history/test-02/t02-r-p7-06.json'
  rows=R.row(REF,path)['legacyQuestions']
  for q in rows:
   n=q['number']; entry=f'question-reserve/test-02/t02-r-p7-06/questions/Q{n:03}/question.json'
   b['test-02']['legacyQuestions'].append(q)
   b['test-02']['questions'][n-1]=R.row(REF,entry)
   del o[f'test-02/Q{n:03}']
  now,_,_=rotate(R,REF,b,i,o)
  self.assertFalse({q['id'] for q in rows}&{q['id'] for q in now['test-02']['legacyQuestions']})
  proxy=Proxy(R)
  k='qa-checkpoints/reconstructions/test-02/t02-r-p7-06.json'
  x=R.row(REF,k); del x['retiredLegacyHistory'];proxy.data[k]=x
  with self.assertRaisesRegex(ValueError,'without hash-bound history'):rotate(proxy,REF,b,i,o)
 def test_unrelated_reviewed_input_mutation_rejected_by_cli_baseline_binding(self):
  from rotation import check_site_and_ledger
  from tempfile import TemporaryDirectory
  with TemporaryDirectory() as tmp:
   tmp=pathlib.Path(tmp); (tmp/'data').mkdir(); ledger=tmp/'ledger'
   for t in EXAMS:(tmp/'data'/f'{t}.json').write_bytes(R.read(BASE,f'data/{t}.json'))
   b,i,o=fixtures(); _,splices,_=rotate(R,REF,b,i,o)
   for a in splices:
    t=a['testId'];(ledger/t).mkdir(parents=True,exist_ok=True)
    for n in a['numbers']:(ledger/t/f'Q{n:03}.json').write_bytes(R.read(REF,f'qa-checkpoints/verified-items/{t}/Q{n:03}.json'))
   check_site_and_ledger(R,BASE,REF,tmp,ledger,splices)
   f=ledger/'test-01'/'Q147.json'; x=strict(f.read_bytes()); x['checks']='wrong candidate'; f.write_text(dump(x))
   with self.assertRaisesRegex(ValueError,'rotation ledger not exact Git evidence'):check_site_and_ledger(R,BASE,REF,tmp,ledger,splices)
   f=tmp/'data'/'test-01.json'; f.write_bytes(f.read_bytes()+b' ')
   with self.assertRaisesRegex(ValueError,'site baseline pack not exact Git source'):check_site_and_ledger(R,BASE,REF,tmp,ledger,splices)

class Proxy:
 def __init__(self,re):self.repo=re;self.data={}
 def row(self,ref,path):return strict(self.read(ref,path))
 def read(self,ref,path):
  return dump(self.data[path]).encode() if ref==REF and path in self.data else self.repo.read(ref,path)
 def git(self,*args):
  b=self.repo.git(*args)
  if args[0]=='ls-tree':
   p=[k for k in self.data if k.startswith('qa-checkpoints/reconstructions') and k.encode() not in b.splitlines()]
   b+=''.join(k+'\n' for k in p).encode()
  return b

if __name__=='__main__':unittest.main()
