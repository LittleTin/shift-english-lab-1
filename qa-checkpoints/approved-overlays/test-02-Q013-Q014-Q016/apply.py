"""Apply a selected, SHA-guarded Test 02 Part 2 overlay to a scratch pack only."""
import argparse,copy,hashlib,json,wave,shutil
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def tick(x):return int((Decimal(str(x))*100000).to_integral_value(rounding=ROUND_HALF_UP))
def sec(x):return x/100000
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def select_index(xs,key,val):
 i,=[i for i,x in enumerate(xs) if x.get(key)==val]
 return i
def hfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def apply_pack(old,overlay,selected,assets):
 p=copy.deepcopy(old);f=p['listeningPlan']['frames']; before=old['listeningPlan']['frames']
 assert p['testId']==overlay['testId'] and digest(p['listeningPlan'])==overlay['oldListeningPlanSha256']
 edits={}
 for n in selected:
  u=overlay['units'][str(n)]
  g=select_index(p['groups'],'id',u['oldGroupId']); q=select_index(p['questions'],'number',n)
  assert digest(p['groups'][g])==u['oldGroupSha256'] and digest(p['questions'][q])==u['oldQuestionSha256']
  assert not any(x['id']==u['newGroup']['id'] for x in p['groups'])
  assert not any(x['id']==u['newQuestion']['id'] for x in p['questions']+p.get('legacyQuestions',[]))
  p['groups'][g],p['questions'][q]=copy.deepcopy(u['newGroup']),copy.deepcopy(u['newQuestion'])
  for a in u['assets'].values():
   path=assets/a['path']
   assert hfile(path)==a['sha256']
   with wave.open(str(path),'rb') as w:assert (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())==(a['hz'],1,2,a['samples'])
  for role in ['cue','passage','answer']:
   i,=[i for i,x in enumerate(f) if x.get('groupId')==u['oldGroupId'] and x.get('role')==role]
   assert digest(f[i])==u[role+'Sha256']
   f[i]['groupId']=u['newGroup']['id']; edits[i]=role
   if role=='answer':f[i]['questionId']=u['newQuestion']['id']
   if role=='passage':
    a=u['assets']['formal']
    f[i].update(src=a['path'],start=0,end=a['seconds'],duration=a['seconds'],speakers=a['speakers'])
 part=[i for i,a in enumerate(f) if a['part']==2]
 first,last=min(part),max(part); assert part==list(range(first,last+1))
 start,after=tick(before[first]['at']),tick(before[last+1]['at'])
 pause=[i for i in part if f[i]['role']=='answer']; assert len(pause)==25
 lens={i:tick(f[i]['duration']) for i in part}
 delta=after-start-sum(lens.values())
 q,r=divmod(abs(delta),len(pause)); sign=-1 if delta<0 else 1
 for j,i in enumerate(pause):
  lens[i]+=sign*(q+(j<r));f[i]['duration']=sec(lens[i])
 assert min(lens[i] for i in pause)>=min(500000,min(tick(before[i]['duration']) for i in pause))
 at=start
 for i in part:f[i]['at']=sec(at);at+=lens[i]
 assert at==after and f[:first]==before[:first] and f[last+1:]==before[last+1:]
 assert p['previousListeningPlan']==old['previousListeningPlan'] and p['alternateListeningPlans']==old['alternateListeningPlans'] and p['legacyQuestions']==old['legacyQuestions']
 assert tick(f[-1]['at'])+tick(f[-1]['duration'])==270000000 and len(f)==len(before)
 assert sum(a['role']=='answer' for a in f)==100
 for i in part:
  if edits.get(i)!='passage':
   assert all(f[i].get(k)==before[i].get(k) for k in ('src','start','end','speakers'))
  if f[i]['role']!='answer' and edits.get(i)!='passage':
   assert f[i]['duration']==before[i]['duration']
  if i not in edits:assert f[i].get('groupId')==before[i].get('groupId') and f[i].get('questionId')==before[i].get('questionId')
 return p,dict(status='structural-candidate-not-published',selected=selected,part2PassageDeltaSeconds=sum(f[i]['duration']-before[i]['duration'] for i in edits if edits[i]=='passage'),part2TotalPauseChangeSeconds=sec(delta),part2OldMinimum=min(before[i]['duration'] for i in pause),part2NewMinimum=min(f[i]['duration'] for i in pause),part2NewMaximum=max(f[i]['duration'] for i in pause),part2Beginning=sec(start),part3Beginning=sec(after),seconds=2700,answerSlots=100,frames=len(f),listeningPlanSha256=digest(p['listeningPlan']))

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--assets',type=Path,required=True);parser.add_argument('--raw-candidate-audio',type=Path)
 parser.add_argument('--select',type=int,nargs='+',required=True); a=parser.parse_args()
 assert not a.output.exists() and len(a.select)==len(set(a.select))
 o=json.loads(Path(__file__).with_name('overlay.json').read_text()); subset=sorted(a.select)
 if a.raw_candidate_audio:
  for n in subset:
   for asset in o['units'][str(n)]['assets'].values():
    src=a.raw_candidate_audio/asset['sourceFile'];dst=a.assets/asset['path']
    assert hfile(src)==asset['sha256']; dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():assert hfile(dst)==asset['sha256']
    else:shutil.copyfile(src,dst)
 p,r=apply_pack(json.loads(a.input.read_text()),o,subset,a.assets)
 put(a.output,p);print(json.dumps(r,indent=2))
