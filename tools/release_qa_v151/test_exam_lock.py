import copy,json,pathlib,shutil,subprocess,tempfile,unittest
import exam_lock as e

TEST='test-01';AU='audio/exams/test-01/common/example.ogg';PIC='assets/exams/test-01/questions/Q001/photo.svg';SV='assets/scenes/formal-example.svg'
def w(root,key,b):
 f=root/key;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b if isinstance(b,bytes) else e.canonical(b));return f
class Synthetic(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fake_audio=subprocess.check_output(['ffmpeg','-nostdin','-hide_banner','-v','error','-f','lavfi','-i','sine=frequency=500:sample_rate=48000:duration=1','-c:a','libopus','-f','ogg','pipe:1'])
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();root=pathlib.Path(self.t.name);self.s=root/'source';self.p=root/'site'; self.ev=root/'proof';self.ev.mkdir()
  w(self.p,AU,self.fake_audio);w(self.p,PIC,b'<svg/>');w(self.p,SV,b'<svg/>')
  self.pack=self.make(); self.emit()
  self.raw_inv=e.inventory(self.s,self.p,TEST,check_codec=False)
  gate=dict(format='shift-post-qa-receipt-v1',examId=TEST,release='synthetic-only-1',inventorySha256=e.sha(e.canonical(self.raw_inv)),gates={})
  for k in sorted(e.GATES):
   proof=w(self.ev,k+'.json',dict(testOnly=True,gate=k));gate['gates'][k]=dict(status='pass',artifact=proof.name,sha256=e.sha(proof.read_bytes()))
  self.gate=w(self.ev,'synthetic.gates.json',gate);self.initial=self.policy({}, {TEST:e.sha(self.gate.read_bytes())})
  self.lock=e.locked_record(self.raw_inv,self.initial,self.gate,self.ev)
  self.lfile=w(self.s,TEST+'/exam-lock.json',self.lock)
  self.mark=self.policy({TEST:e.sha(self.lfile.read_bytes())},{})
 def tearDown(self):self.t.cleanup()
 def policy(self,old,new):
  return dict(format='shift-externally-trusted-lock-policy-v1',release='synthetic-only-1',expectedExams=[TEST],baselineLocks=old,initialExams=new)
 def make(self):
  qs=[];gs=[];fr=[];n=0;now=0
  for p,count in e.PARTS.items():
   size=e.GROUPS.get(p,1)
   for _ in range(0,count,size):
    gid=f'synthetic-group-{n+1}'
    if p!=5:
     g=dict(id=gid,testId=TEST,part=p,passage='Example talk',passageZh='示例內容')
     if p<=4:g.update(audio=AU,audioStart=0,audioEnd=1)
     if p==1:g.update(image=PIC,imageAlt='Sample portrait')
     gs.append(g)
    for _ in range(size):
     n+=1;qid=f'synthetic-item-{n}'
     opts=[dict(id=k,text=f'Option {k}',zh=f'示例 {k}',whyZh=f'說明 {k}') for k in ('ABC' if p==2 else 'ABCD')]
     q=dict(id=qid,number=n,testId=TEST,part=p,revision=1,difficulty=('foundation','intermediate','advanced')[n%3],prompt='Example',promptZh='例題',options=opts,answer='A',explanationZh='解說',evidence='Example',vocabulary=[dict(term='example',zh='示例',note='試用')])
     if p!=5:q['groupId']=gid
     qs.append(q)
     if p<=4:
      fr.extend([dict(at=now,duration=1,kind='audio',role='passage',src=AU,start=0,end=1,groupId=gid,part=p),dict(at=now+1,duration=26,kind='silence',role='answer',groupId=gid,part=p,questionId=qid)])
      now+=27
  return dict(schemaVersion=1,testId=TEST,revision=1,questions=qs,groups=gs,listeningPlan=dict(testId=TEST,duration=2700,frames=fr))
 def emit(self):
  p=self.pack; w(self.p,'data/test-01.json',p)
  w(self.p,'data/test-01.js',b'window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('+e.canonical(p).strip()+b');\n')
  qpaths=[f'{TEST}/questions/Q{z["number"]:03}/question.json' for z in p['questions']]
  gpaths=[f'{TEST}/groups/{z["id"]}/group.json' for z in p['groups']]
  for f,z in zip(qpaths+gpaths,p['questions']+p['groups'],strict=True):w(self.s,f,z)
  w(self.s,f'{TEST}/exam.json',dict(testId=TEST,records=dict(questions=qpaths,groups=gpaths),metadata={k:v for k,v in p.items() if k not in ('questions','groups')}))
  refs=sorted(set(e.media_refs(p)))
  for r in refs:
   w(self.s,f'{TEST}/common/media/{r}',(self.p/r).read_bytes())
  w(self.s,f'{TEST}/common/media.json',dict(files=[dict(url=r,source=f'{TEST}/common/media/{r}') for r in refs]))
 def check(self):return e.check_lock(self.s,self.p,TEST,self.mark,check_codec=False)
 def test_catalog_protects_exact_set_but_allows_new_index_entries_when_pinned(self):
  w(self.p,'data/catalog.js',b"window.SHIFT_CATALOG={tests:[{id:'test-01',path:'data/test-01.js'}]};")
  e.check_site_scope(self.p,{TEST})
  w(self.p,'data/test-02.js',b'duplicate ignored?')
  with self.assertRaisesRegex(e.LockError,'JS|js'):e.check_site_scope(self.p,{TEST})
  (self.p/'data/test-02.js').unlink()
  w(self.p,'data/catalog.js',b"window.SHIFT_CATALOG={tests:[{id:'test-01',path:'data/swap.js'}]};")
  with self.assertRaisesRegex(e.LockError,'redirects'):e.check_site_scope(self.p,{TEST})
 def test_profile_rejects_ogg_wrong_codec(self):
  f=w(self.p,'audio/bogus.ogg',b'OggS fake OpusHead bytes')
  with self.assertRaisesRegex(e.LockError,'ffprobe'):e.opus(f)
 def test_dedicated_question_role_ranges_reconcile_then_fail_on_alias(self):
  g=self.pack['groups'][0]; q=self.pack['questions'][0]; gd=f"{TEST}/groups/{g['id']}/group.json"
  sp={u:f'{TEST}/common/media/{u}' for u in (AU,PIC)}
  roles=[
   dict(url=AU,source=sp[AU],role='practice-audio',group=g['id'],start=0,end=1,startSample48k=0,endSample48k=48000),
   dict(url=PIC,source=sp[PIC],role='group-visual',group=g['id']),
   dict(url=AU,source=sp[AU],role='passage',group=g['id'],question=None,frame=0,timelineAt=0,start=0,end=1,startSample48k=0,endSample48k=48000),
  ]
  media=dict(files=[dict(url=u,source=x) for u,x in sp.items()],question=q['id'],groupSource=gd,roles=roles)
  f=w(self.s,f'{TEST}/questions/Q001/media.json',media)
  self.assertEqual(e.inventory(self.s,self.p,TEST,check_codec=False)['checkedQuestionRoleSidecars'],1)
  media['roles'][2]['endSample48k']=47999;f.write_bytes(e.canonical(media))
  with self.assertRaisesRegex(e.LockError,'role/range'):e.inventory(self.s,self.p,TEST,check_codec=False)
 def test_positive_exact_lock(self):
  self.assertEqual(self.check(),self.mark['baselineLocks'][TEST])
  e.opus(self.p/AU)
 def test_runtime_unauthored_translation(self):
  p=self.p/'data/test-01.json';q=json.loads(p.read_bytes());q['questions'][0]['promptZh']='更改';p.write_bytes(e.canonical(q))
  with self.assertRaisesRegex(e.LockError,'wrapper'):self.check()
 def test_subtle_owner_unapproved_coherent_edit(self):
  self.pack['questions'][0]['options'][0]['zh']='更改';self.emit()
  with self.assertRaisesRegex(e.LockError,'locked'):self.check()
 def test_changed_answer_and_difficulty(self):
  self.pack['questions'][1].update(answer='B',difficulty='advanced');self.emit()
  with self.assertRaisesRegex(e.LockError,'locked'):self.check()
 def test_changed_formal_range_coherent_metadata(self):
  self.pack['listeningPlan']['frames'][0].update(start=.01,end=1.01);self.emit()
  with self.assertRaisesRegex(e.LockError,'locked'):self.check()
 def test_missing_media(self):
  (self.p/PIC).unlink()
  with self.assertRaisesRegex(e.LockError,'missing'):self.check()
 def test_changed_opus_byte_even_with_matching_source(self):
  out=self.p/AU;out.write_bytes(out.read_bytes()[:-1]+bytes([out.read_bytes()[-1]^1]));self.emit()
  with self.assertRaisesRegex(e.LockError,'locked'):self.check()
 def test_resealed_replaced_manifest_rejected(self):
  self.pack['questions'][0]['explanationZh']='另一說明';self.emit()
  # Explicitly a test of the wrong approach: matching edits plus locally recalculated digests.
  inv=e.inventory(self.s,self.p,TEST,check_codec=False)
  fake=copy.deepcopy(self.lock);fake['inventory']=inv
  fake['integritySha256']=e.sha(e.canonical({k:v for k,v in fake.items() if k!='integritySha256'}));self.lfile.write_bytes(e.canonical(fake))
  with self.assertRaisesRegex(e.LockError,'trusted baseline'):self.check()
 def test_missing_lock(self):
  self.lfile.unlink()
  with self.assertRaisesRegex(e.LockError,'missing'):self.check()
 def test_changed_lock_status(self):
  fake=copy.deepcopy(self.lock);fake['status']='draft';self.lfile.write_bytes(e.canonical(fake))
  with self.assertRaisesRegex(e.LockError,'trusted baseline'):self.check()
 def test_missing_or_failed_gate_cannot_generate(self):
  (self.ev/'itemContent.json').unlink()
  with self.assertRaisesRegex(e.LockError,'missing'):e.locked_record(self.raw_inv,self.initial,self.gate,self.ev)
 def test_no_regenerate_for_established(self):
  with self.assertRaisesRegex(e.LockError,'established'):e.locked_record(self.raw_inv,self.mark,self.gate,self.ev)
 def test_replaced_initial_receipt_rejected(self):
  self.gate.write_bytes(b'{}')
  with self.assertRaisesRegex(e.LockError,'pinned artifact'):e.locked_record(self.raw_inv,self.initial,self.gate,self.ev)
 def test_wrong_baseline_policy_pin(self):
  policy=w(self.ev,'policy.json',self.mark)
  with self.assertRaisesRegex(e.LockError,'pinned artifact'):e.policy_load(policy,'a'*64)
 def test_symlink_media_even_if_same_bytes(self):
  img=self.p/PIC;dst=img.with_name('copy.svg');shutil.copyfile(img,dst);img.unlink();img.symlink_to(dst)
  with self.assertRaisesRegex(e.LockError,'symlink'):self.check()
 def test_absolute_or_encoded_media_alias(self):
  for bad in ('/assets/a.svg','assets/x/../a.svg','assets/a%2e.svg','assets//a.svg','https://host.example/x.svg'):
   with self.subTest(bad=bad):
    with self.assertRaises(e.LockError):list(e.media_refs({'image':bad}))
 def test_same_bytes_renamed_media_cannot_override_old_baseline(self):
  dst=PIC.replace('photo','copy');w(self.p,dst,(self.p/PIC).read_bytes());self.pack['groups'][0]['image']=dst
  (self.s/f'{TEST}/common/media/{PIC}').unlink();self.emit()
  with self.assertRaisesRegex(e.LockError,'locked'):self.check()
 def test_duplicate_json_keys(self):
  with self.assertRaisesRegex(e.LockError,'duplicate JSON'):e.read_json(b'{"a":1,"a":2}')
 def test_extras_do_not_enter_exam(self):
  w(self.s,TEST+'/unreferenced.json',{'x':1})
  with self.assertRaisesRegex(e.LockError,'untracked'):self.check()
 def test_case_alias_rejected(self):
  with self.assertRaisesRegex(e.LockError,'case-alias'):e.artifact_aliases(['audio/A.ogg','audio/a.ogg'])
if __name__=='__main__':unittest.main(verbosity=2)
