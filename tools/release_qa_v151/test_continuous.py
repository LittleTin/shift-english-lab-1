from pathlib import Path
import copy,json,os,subprocess,tempfile,unittest
import numpy as np
import amendment_audit as A
import exam_lock as L
from continuous_contract import geometry,role,owner
D=Path(__file__).parent
H=Path('/workspace/shared/shift-t02-formal-independent-prototype/all162-master')
BASE=Path('/workspace/shared/shift-full-candidate-1230/deploy-preflight-v150/site/data')
class TestContinuous(unittest.TestCase):
 def setUp(self):
  self.t='test-01';self.old=json.loads((BASE/'test-01.json').read_bytes());g=geometry(json.loads((H/'data/test-01.json').read_bytes())['listeningPlan'],self.t)
  self.r={u['src']:'a'*64 for u in g.values()}
  self.new=copy.deepcopy(self.old);self.new['listeningPlan']['groupAudio']={k:dict(src=v['src'],duration=v['seconds'])for k,v in g.items()}
  self.images={}
  for i,q in enumerate(self.new['groups']):
   if not q.get('image'):continue
   path=q['image'];dst=f'{path.rsplit("/",1)[0]}/{i:024x}.jpg';r=dict(oldPath=path,newPath=dst,jpegSha256='b'*64)
   if q['part']==1:q['imageAlt']=r['imageAltAfter']='Question photograph'
   q['image']=dst;self.images[q['id']]=r
  self.scope=dict(formalAssetHashes=self.r,images=self.images)
 def test_exact_timing_and_no_question_change(self):
  s,im=A.allowed_pack(self.old,self.new,self.scope,self.t)
  self.assertEqual(len(s),54);self.assertEqual(sum(x['size']for x in s.values()),129600000)
  q=self.new['questions'][0];q['answer']='B' if q['answer']=='A' else 'A'
  with self.assertRaises(L.LockError):A.allowed_pack(self.old,self.new,self.scope,self.t)
 def test_blocks_scored_chart_alt_and_question_option(self):
  row=next(q for q in self.new['groups']if q['part']>1 and self.images.get(q['id']))
  row['imageAlt']='Hints at the answer'
  with self.assertRaises(L.LockError):A.allowed_pack(self.old,self.new,self.scope,self.t)
 def test_blocks_duration_and_src_alias(self):
  plan=self.new['listeningPlan'];g=next(iter(plan['groupAudio'].values()));g['duration']+=1/48000
  with self.assertRaises(ValueError):geometry(plan,self.t)
  g['duration']-=1/48000;g['src']='audio/formal-groups/test-01/wrong.ogg'
  with self.assertRaises(ValueError):geometry(plan,self.t)
 def test_blocks_logical_frame_edit_even_if_duration_unchanged(self):
  self.new['listeningPlan']['frames'][0]['src']='audio/different.ogg'
  with self.assertRaises(L.LockError):A.allowed_pack(self.old,self.new,self.scope,self.t)
 def test_verified_role_owner(self):
  plan=self.new['listeningPlan']; c=geometry(plan,self.t); g=next(z for z in self.new['groups']if z['id'] in c); q=next(x for x in self.new['questions']if x['groupId']==g['id'])
  gid=g['id']; m=role(c[gid],gid)
  q2={'id':q['id']};g2={'id':gid}
  t={'listeningPlan':{'frames':[]}}
  wrong=f'{self.t}/questions/Q001/media/'+m['url']
  with self.assertRaises(L.LockError):
   L.check_question_sidecar({'question':q['id'],'groupSource':f'{self.t}/groups/{gid}/group.json','roles':[]},q2,g2,t,self.t,{m['url']:wrong},c)
  actual=owner(self.t,gid,m['url']);r=dict(m,source=actual)
  L.check_question_sidecar({'question':q['id'],'groupSource':f'{self.t}/groups/{gid}/group.json','roles':[r]},q2,g2,t,self.t,{m['url']:actual},c)
 def test_reject_actual_nonsilent_wait(self):
  root=Path(tempfile.mkdtemp(dir=D))
  try:
   src=root/'sample.ogg'; a=(10000*np.sin(np.linspace(0,3000,48000))).astype('<i2')
   proc=subprocess.run(['ffmpeg','-nostdin','-v','error','-f','s16le','-ar','48000','-ac','1','-i','-','-c:a','libopus','-y',str(src)],input=a.tobytes(),check=True)
   with self.assertRaisesRegex(L.LockError,'non-silent encoded answer'):
    L.inspect_continuous_decode(src,{'size':48000,'frames':[dict(index=0,start=0,end=24000,kind='audio',role='passage'),dict(index=1,start=24000,end=48000,kind='silence',role='answer')]})
  finally:
   import shutil;shutil.rmtree(root)
if __name__=='__main__':unittest.main()
