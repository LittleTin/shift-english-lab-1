"""Replay selected Test03 Q002/Q017 exact practice audio only after Q084."""
import argparse,copy,hashlib,json,wave
from pathlib import Path
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def item(rows,k,v):
 o,=[x for x in rows if x.get(k)==v];return o
def write(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def apply(p,ov,wanted,assets):
 assert p['testId']=='test-03' and digest(p['listeningPlan'])==ov['unchangedPlanSha256']
 assert len(wanted)==len(set(wanted)) and set(wanted)<=set(ov['units'])
 out=copy.deepcopy(p); anyq=[]
 for n in wanted:
  u=ov['units'][n]; q=item(out['questions'],'number',int(n)); g=item(out['groups'],'id',q['groupId'])
  assert digest(q)==u['questionSha256'] and digest(g)==u['oldGroupSha256']
  assert q['id']==u['id'] and q['answer']==u['key']
  current={role:item([f for f in out['listeningPlan']['frames'] if f.get('groupId')==q['groupId']],'role',role) for role in ('cue','passage')}
  for mode,guard in u['oldMedia'].items():
   assert h(assets/guard['asset'])==guard['sha256']
   old=(g['audio'],g['audioStart'],g['audioEnd']) if mode=='practice' else tuple(current['passage' if mode=='formal' else 'cue'][k] for k in ('src','start','end'))
   assert old==tuple(guard[k] for k in ('asset','start','end'))
  if u['image']:
   assert g['image']==u['image']['src'] and h(assets/g['image'])==u['image']['sha256']
  a=u['asset']; src=assets/a['path'];assert h(src)==a['sha256']
  with wave.open(str(src),'rb') as w:
   assert (w.getframerate(),w.getsampwidth(),w.getnchannels(),w.getnframes())==(24000,2,1,a['samples'])
   end=w.getnframes()/w.getframerate(); assert end==a['seconds']
  assert u['newGroup']==dict(g,audio=a['path'],audioStart=0,audioEnd=end,duration=end)
  out['groups'][out['groups'].index(g)]=u['newGroup']
  anyq.append(int(n))
 assert out['listeningPlan']==p['listeningPlan'] and out['questions']==p['questions']
 assert all(out.get(k)==p.get(k) for k in ('previousListeningPlan','alternateListeningPlans','legacyQuestions'))
 assert all(a==b for a,b in zip(out['groups'],p['groups']) if a['id'] not in [ov['units'][n]['newGroup']['id'] for n in wanted])
 return out,dict(status='isolated practice-only assembly no release',selected=anyq,formalPlanSha256=digest(out['listeningPlan']),totalSeconds=2700,formalFrameChanges=0,questionChanges=0,groupMediaChanges=len(anyq))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--select',nargs='+',required=True);a=p.parse_args(); assert not a.output.exists()
 o=json.loads(Path(__file__).with_name('overlay.json').read_text())
 dest,receipt=apply(json.loads(a.input.read_text()),o,a.select,a.assets)
 write(a.output,dest);print(json.dumps(receipt,indent=2))
