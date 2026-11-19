import copy,json,shutil,tempfile,unittest,wave
from hashlib import sha256
from pathlib import Path
from timing import draft,audit,ticks,EXAM
ROOT=Path('shift-next')
P=json.loads((ROOT/'data/test-02.json').read_text())
G='t02-g036'
def asset(path):return sha256(path.read_bytes()).hexdigest()

class Timing(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.g=next(g for g in P['groups'] if g['id']==G)
        self.f=next(f for f in P['listeningPlan']['frames'] if f.get('groupId')==G and f['role']=='passage')
        self.q=next(f for f in P['listeningPlan']['frames'] if f.get('questionId')=='t02-q045' and f['role']=='question')
        self.old=self.paper(self.f);self.stem=self.paper(self.q)
    def paper(self,f):
        path=f['src'];d=self.root/path
        d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,d)
        return dict(path=path,sha256=asset(d),start=f['start'],end=f['end'])
    def new(self,seconds,name='fixture.wav'):
        rel='audio/repair-fixture/'+name
        dest=self.root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        rate=16000;n=round(rate*seconds)
        with wave.open(str(dest),'wb') as w:
            w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(b'\0\0'*n)
        return dict(path=rel,sha256=asset(dest),frames=n,sampleRate=rate)
    def unit(self,*edits,floor=8):
        return dict(testId='test-02',groupId=G,minAnswerSec=floor,changes=edits)
    def edit(self,mode,new,role='passage',old=None,qid=None):
        return dict(mode=mode,role=role,old=old or self.old,new=new,questionId=qid)
    def test_shared_replacement_keeps_old_bytes_end_and_other_groups(self):
        before=copy.deepcopy(P)
        a=self.new(31)
        out,proof=draft(P,self.root,self.unit(self.edit('formal',a),self.edit('practice',a)))
        self.assertEqual(P,before)
        self.assertNotEqual(out,P)
        self.assertEqual(asset(self.root/self.old['path']),self.old['sha256'])
        self.assertEqual(proof['formalSeconds'],2700)
        self.assertEqual(audit(out['listeningPlan']['frames']),audit(P['listeningPlan']['frames']))
        old=[f for f in P['listeningPlan']['frames'] if f.get('groupId')!=G]
        new=[f for f in out['listeningPlan']['frames'] if f.get('groupId')!=G]
        self.assertEqual(old,new)
        self.assertTrue(all(s>=8 for s in proof['answerSeconds']))
    def test_practice_only_never_moves_any_formal_frame(self):
        a=self.new(99)
        out,proof=draft(P,self.root,self.unit(self.edit('practice',a)))
        self.assertEqual(out['listeningPlan'],P['listeningPlan'])
        self.assertEqual(proof['changedFormalIndices'],[])
    def test_stem_only_keeps_actual_dialogue_and_group_end(self):
        a=self.new(4.2)
        out,proof=draft(P,self.root,self.unit(self.edit('formal',a,'question',self.stem,'t02-q045')))
        src=next(f for f in out['listeningPlan']['frames'] if f.get('groupId')==G and f['role']=='passage')
        self.assertEqual(src,self.f)
        self.assertEqual(len(proof['changedFormalIndices']),1)
        self.assertEqual(audit(out['listeningPlan']['frames']),audit(P['listeningPlan']['frames']))
    def test_overlong_audio_refused_not_trimmed(self):
        with self.assertRaisesRegex(ValueError,'Cannot fit'):
            draft(P,self.root,self.unit(self.edit('formal',self.new(85))))
    def test_old_hash_old_range_and_sample_count_enforced(self):
        a=self.new(31)
        for old,repl,msg in [
            ({**self.old,'sha256':'0'*64},a,'Audio bytes drifted'),
            ({**self.old,'start':self.old['start']+.01},a,'range drift'),
            (self.old,{**a,'frames':a['frames']-1},'sample metadata drift'),
        ]:
            with self.assertRaisesRegex(ValueError,msg):draft(P,self.root,self.unit(self.edit('formal',repl,old=old)))
    def test_no_in_place_no_cue_splice(self):
        a=self.new(31)
        with self.assertRaisesRegex(ValueError,'in place'):
            draft(P,self.root,self.unit(self.edit('formal',{**a,'path':self.old['path']})))
        with self.assertRaisesRegex(ValueError,'Only practice/formal'):
            draft(P,self.root,self.unit(self.edit('formal',a,'cue')))

if __name__=='__main__':unittest.main()
