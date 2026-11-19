from pathlib import Path
import tempfile,json,copy,unittest
from difficulty_gate import TESTS,review_record,report,apply_accepted,summarize

class TestDifficulty(unittest.TestCase):
    def setUp(self):
        d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup)
        self.root=Path(d.name)
        self.v=self.root/'verified';self.r=self.root/'review'
        self.packs={}
        for t in TESTS:
            self.packs[t]={'testId':t,'questions':[],'groups':[]}
            for n in range(1,201):
                q=dict(id=f'{t}-q{n}',revision=1,testId=t,number=n,part=2 if n<=100 else 5,groupId=None,prompt='Underlying words',answer='A',difficulty='intermediate')
                self.packs[t]['questions'].append(q)
                item={'status':'verified-item-not-published','activeQuestion':q}
                self.write(self.v,t,n,item)
                k=(n-1)%100
                d='foundation' if k<20 else 'intermediate' if k<80 else 'advanced'
                self.write(self.r,t,n,review_record(t,n,item,d,'Exact task reasoning','reviewed fixture'))
    def write(self,root,t,n,value):
        path=root/t/f'Q{n:03}.json';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,ensure_ascii=False)+'\n')
        return path
    def test_applies_difficulty_only_and_does_not_claim_release(self):
        old=copy.deepcopy(self.packs)
        p,r=apply_accepted(self.packs,self.v,self.r)
        self.assertEqual(self.packs,old)
        self.assertTrue(r['difficultyGateComplete'])
        self.assertFalse(r['releaseReady'])
        for t in TESTS:
            for a,b in zip(old[t]['questions'],p[t]['questions']):
                self.assertEqual({**a,'difficulty':b['difficulty']},b)
    def test_stale_key_blocks_application(self):
        q=self.packs['test-02']['questions'][0]
        q['answer']='B'
        with self.assertRaisesRegex(ValueError,'content changed'):
            apply_accepted(self.packs,self.v,self.r)
    def test_missing_content_or_ungrounded_review_fails(self):
        (self.v/'test-01'/'Q002.json').unlink()
        report_,_=report(self.v,self.r)
        self.assertIn(2,report_['exams']['test-01']['listening']['contentUnverified'])
        self.assertFalse(report_['difficultyGateComplete'])
    def test_all_medium_does_not_satisfy_three_layers(self):
        t='test-03'
        for n in range(101,201):
            p=self.r/t/f'Q{n:03}.json'
            u=json.loads(p.read_text());u['toDifficulty']='intermediate';self.write(self.r,t,n,u)
        report_,_=report(self.v,self.r)
        s=report_['exams']['test-03']['reading']
        self.assertTrue(s['reviewComplete'])
        self.assertFalse(s['distributionAccepted'])
        self.assertFalse(report_['difficultyGateComplete'])
    def test_same_group_mixed_and_partial_not_counted_as_selectable(self):
        s=summarize({'g':[1,2,3],'h':[4,5,6],'i':[7,8,9]},
            {1:'advanced',2:'intermediate',3:'foundation',4:'advanced',5:'advanced',
             7:'advanced',8:'advanced',9:'advanced'})
        self.assertEqual(s['reviewedCounts']['advanced'],6)
        self.assertEqual(s['completePracticeQuestionCounts']['advanced'],3)
        self.assertEqual(s['completePracticeGroupCounts']['advanced'],1)

if __name__=='__main__':unittest.main()
