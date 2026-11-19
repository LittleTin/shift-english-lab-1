"""Unit/integration checks on the immutable e04107b fixture; no fake ledger passes."""
from pathlib import Path
import unittest
import reconcile as m

ROOT=Path(__file__).resolve().parent
SITE=ROOT/'inputs'
LEDGER=ROOT/'evidence/qa-checkpoints/verified-items'


class Gate(unittest.TestCase):
    def test_reject_escape_and_nonfinite(self):
        for p in ('assets/../private','/assets/p.png','audio/./x.wav','assets/shell\\abc.png'):
            with self.subTest(p=p),self.assertRaises(ValueError):m.rel(SITE,p)
        for n in ('infinity','NaN',True):
            with self.subTest(n=n),self.assertRaises(ValueError):m.d(n)

    def test_Q003_and_Q001_are_bound_to_exact_roles(self):
        report,packs=m.run(SITE,LEDGER,{})
        test=report['exams']['test-01']
        self.assertEqual(set(test['verifiedMedia']['1']['audio']),{'passage','practice'})
        self.assertEqual(set(test['verifiedMedia']['3']['audio']),{'passage','practice'})
        self.assertEqual(packs,{})
        self.assertFalse(report['evidenceComplete'])

    def test_hold_missing_and_group_drift_gate(self):
        report,packs=m.run(SITE,LEDGER,{})
        exp={'test-01':(153,43,1),'test-02':(100,100,0),'test-03':(75,125,0)}
        for name,v in report['exams'].items():
            self.assertEqual(tuple(len(v[k]) for k in ('accepted','missing','issues')), exp[name])
        test=report['exams']['test-01']
        self.assertTrue(set(range(135,139)).isdisjoint(test['accepted']))
        self.assertEqual(set(map(tuple,test['groups']['t01-r-p6-02'].values())),{(135,136,137),(138,)})
        self.assertEqual(packs,{})

    def test_bogus_conflict_decision_is_refused(self):
        report,packs=m.run(SITE,LEDGER,{})
        hashes=report['exams']['test-01']['groups']['t01-r-p6-02']
        desired=next(k for k,v in hashes.items() if v==[135,136,137])
        fake={'test-01/t01-r-p6-02':{'canonicalSha256':desired,
              'seenSha256':list(hashes),'reverifiedQuestionNumbers':[],
              'reason':'Synthetic negative test: deliberately missing Q138'}}
        r,p=m.run(SITE,LEDGER,fake)
        self.assertIn('test-01/t01-r-p6-02',r['unusedDecisions'])
        self.assertEqual(p,{})

    def test_wrong_audio_asset_digest_fails(self):
        actual=m.strict(LEDGER/'test-01/Q003.json')
        r=actual['audio'][0]
        interval={r['mode']:(r['path'],r['from'],r['to'])}
        with self.assertRaisesRegex(ValueError,'source hash mismatch'):
            m.check_audio({'audio':[dict(r,assetSha256='0'*64)]},interval,lambda p,k:m.file_sha(m.rel(SITE,p,k)))

if __name__=='__main__':
    unittest.main()
