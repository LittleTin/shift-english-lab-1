from pathlib import Path
import copy,json,os,subprocess,tempfile,unittest
import numpy as np
import amendment_audit as A
import exam_lock as L
from continuous_contract import geometry,role,owner
D=Path(__file__).parent
def synthetic_legacy_pair(test):
 # Deterministic fixture, not a published pack or evidence about a historical release.
 # Keep the historical test dimensions: 54 independent groups, 100 items, 45 minutes.
 groups=[]; questions=[]; frames=[]; audio={}
 for index in range(54):
  gid=f't01-g{index+1:03}'
  part=1 if index<6 else 2 if index<31 else 3 if index<44 else 4
  group={'id':gid,'part':part}
  if index==0: group.update(image='assets/scenes/synthetic-scene.svg',imageAlt='Synthetic scene')
  if index==31: group.update(image='assets/graphics/synthetic-chart.svg',imageAlt='Synthetic chart')
  groups.append(group)
  for _ in range(1 if part<3 else 3):
   questions.append(dict(id=f't01-q{len(questions)+1:03}',groupId=gid,answer='A'))
  at=index*50
  frames.append(dict(at=at,duration=26,groupId=gid,kind='audio',role='passage',
                     src=f'audio/legacy/{test}/{gid}.ogg'))
  frames.append(dict(at=at+26,duration=24,groupId=gid,kind='silence',role='answer'))
  audio[gid]=dict(src=f'audio/formal-groups/{test}/{gid}.ogg',duration=50)
 old=dict(groups=groups,questions=questions,listeningPlan=dict(duration=2700,frames=frames))
 new=copy.deepcopy(old)
 new['listeningPlan']['groupAudio']=audio
 return old,new

def fixture_pair(test):
 paths=[os.environ.get('SHIFT_CONTINUOUS_LEGACY_PACK'),os.environ.get('SHIFT_CONTINUOUS_GROUPED_PACK')]
 if not any(paths):
  return synthetic_legacy_pair(test)
 if not all(paths):
  raise ValueError('set both SHIFT_CONTINUOUS_LEGACY_PACK and SHIFT_CONTINUOUS_GROUPED_PACK')
 return tuple(json.loads(Path(path).read_bytes()) for path in paths)

class TestContinuous(unittest.TestCase):
 def setUp(self):
  self.t='test-01';self.old,grouped=fixture_pair(self.t)
  g=geometry(grouped['listeningPlan'],self.t)
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
