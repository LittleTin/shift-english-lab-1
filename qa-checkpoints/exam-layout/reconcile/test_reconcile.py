"""Unit/integration checks on the immutable e04107b fixture; no fake ledger passes."""
from pathlib import Path
import unittest
import reconcile as m

ROOT=Path(__file__).resolve().parent
SITE=ROOT/'inputs'
LEDGER=ROOT/'evidence/qa-checkpoints/verified-items'


class Gate(unittest.TestCase):
    def test_retained_vocabulary_requires_usage_note(self):
        passes=dict(vocabulary=[dict(term='stand',zh='支架',note='在文章中指放置樣品的支架。')])
        self.assertIsNone(m.check_item_vocabulary(passes))
        for bad in ({}, {'vocabulary':[]},
          {'vocabulary':[{'term':'stand','zh':'支架'}]},
          {'vocabulary':[{'term':'stand','zh':'支架','note':'  '}]}):
            with self.assertRaisesRegex(ValueError,'Incomplete vocabulary'):
                m.check_item_vocabulary(bad)

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

    def test_supplied_cue_is_verified_against_exact_source(self):
        pack=m.strict(SITE/'data/test-01.json')
        q=next(q for q in pack['questions'] if q['number']==1)
        g=next(g for g in pack['groups'] if g['id']==q['groupId'])
        req=m.want_audio(pack,q,g,has_cue=True)
        self.assertIn('cue',req)
        self.assertNotIn('cue',m.want_audio(pack,q,g))
        dig=lambda p,k:m.file_sha(m.rel(SITE,p,k))
        rows=[dict(mode=k,path=src,start=start,end=end,assetSha256=dig(src,'audio'))
              for k,(src,start,end) in req.items()]
        self.assertIn('cue',m.check_audio({'audio':rows},req,dig))
        cue=next(r for r in rows if r['mode']=='cue')
        cue['start']+=0.01
        with self.assertRaisesRegex(ValueError,'range'):
            m.check_audio({'audio':rows},req,dig)

    def test_wrong_audio_asset_digest_fails(self):
        actual=m.strict(LEDGER/'test-01/Q003.json')
        r=actual['audio'][0]
        interval={r['mode']:(r['path'],r['from'],r['to'])}
        with self.assertRaisesRegex(ValueError,'source hash mismatch'):
            m.check_audio({'audio':[dict(r,assetSha256='0'*64)]},interval,lambda p,k:m.file_sha(m.rel(SITE,p,k)))

if __name__=='__main__':
    unittest.main()
