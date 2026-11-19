"""Replay exact Test03 Q002 bilingual/mode audio repair in scoped cumulative pack."""
import argparse,copy,hashlib,json,wave
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def tick(x):return int((Decimal(str(x))*100000).to_integral_value(rounding=ROUND_HALF_UP))
def sec(x):return x/100000
def item(rows,key,val):
 x,=[o for o in rows if o.get(key)==val];return x
def write(path,x):path.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def apply(old,o,assets):
 assert old['testId']=='test-03' and digest(old['listeningPlan'])==o['oldPlanSha256']
 p=copy.deepcopy(old);frames=p['listeningPlan']['frames'];before=old['listeningPlan']['frames']
 q=item(p['questions'],'number',2);g=item(p['groups'],'id',q['groupId'])
 assert digest(q)==o['oldQuestionSha256'] and digest(g)==o['oldGroupSha256'] and q['answer']=='D'
 q17=item(p['questions'],'number',17);g17=item(p['groups'],'id',q17['groupId']);assert (digest(q17),digest(g17))==(o['predecessor']['q017QuestionSha256'],o['predecessor']['q017GroupSha256'])
 assert h(assets/g17['audio'])==o['predecessor']['q017MediaSha256']
 newq,newg=o['newQuestion'],o['newGroup']; gid=newg['id']
 assert newq['answer']==q['answer'] and newq['options'][:3]==q['options'][:3] and newq['number']==2 and newq['groupId']==gid
 assert not any(z['id']==newq['id'] for z in p['questions']+p.get('legacyQuestions',[])) and not any(z['id']==gid for z in p['groups'])
 assert q.keys()==newq.keys() and g.keys()==newg.keys()
 assert all(newq[k]==v for k,v in q.items() if k not in ('id','groupId','revision','options','evidence','explanationZh','vocabulary'))
 assert all(newg[k]==v for k,v in g.items() if k not in ('id','audio','audioStart','audioEnd','duration','passage','passageZh','audioScript','turns'))
 assert (g['image'],newg['image'])==(o['image']['src'],o['image']['src']) and h(assets/g['image'])==o['image']['sha256']
 for a in o['oldSources'].values():assert h(assets/a['asset'])==a['sha256']
 for a in o['newAssets'].values():
  src=assets/a['path']; assert h(src)==a['sha256']
  with wave.open(str(src),'rb') as w:assert (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())==(24000,1,2,a['samples']) and w.getnframes()/w.getframerate()==a['seconds']
 p['questions'][p['questions'].index(q)]=newq;p['groups'][p['groups'].index(g)]=newg
 formal=o['newAssets']['formal'];practice=o['newAssets']['practice'];assert newg['audio']==practice['path'] and newg['audioEnd']==practice['seconds']
 idx={}
 for role in ('cue','passage','answer'):
  i,=[i for i,f in enumerate(frames) if f.get('groupId')==g['id'] and f['role']==role]
  f=frames[i]; assert digest(f)==o['oldFrames'][role];idx[role]=i
  f['groupId']=gid
  if role=='passage':
   assert f['speakers']==formal['voices']
   f.update(src=formal['path'],start=0,end=formal['seconds'],duration=formal['seconds'])
  if role=='answer':f['questionId']=newq['id']
 part1=[i for i,f in enumerate(frames) if f['part']==1];first,last=min(part1),max(part1)
 assert part1==list(range(first,last+1)) and first==0
 pauses=[i for i in part1 if frames[i]['role']=='answer'];assert len(pauses)==6
 start=tick(before[first]['at']);finish=tick(before[last+1]['at']);lens={i:tick(frames[i]['duration']) for i in part1}
 delta=finish-start-sum(lens.values()); assert delta==tick(before[idx['passage']]['duration'])-tick(formal['seconds'])==383050
 add,rem=divmod(delta,len(pauses))
 for j,i in enumerate(pauses):lens[i]+=add+(j<rem);frames[i]['duration']=sec(lens[i])
 cursor=start
 for i in part1: frames[i]['at']=sec(cursor);cursor+=lens[i]
 assert cursor==finish and frames[last+1:]==before[last+1:] and len(frames)==len(before)==284
 assert sum(f['role']=='answer' for f in frames)==100 and tick(frames[-1]['at'])+tick(frames[-1]['duration'])==270000000
 for i,(a,b) in enumerate(zip(frames,before)):
  assert (a['part'],a['role'])==(b['part'],b['role'])
  if i!=idx['passage']:assert all(a.get(k)==b.get(k) for k in ('src','start','end','speakers'))
  if i!=idx['passage'] and i not in pauses:assert a['duration']==b['duration']
  if i not in idx.values():assert all(a.get(k)==b.get(k) for k in ('groupId','questionId'))
 assert all(p.get(k)==old.get(k) for k in ('previousListeningPlan','alternateListeningPlans','legacyQuestions'))
 return p,dict(status='isolated-exact-structure-no-release',totalSeconds=2700,formalFrameCount=284,answerFrames=100,newPlanSha256=digest(p['listeningPlan']),oldPassageSeconds=before[idx['passage']]['duration'],newPassageSeconds=formal['seconds'],gainedSilenceSeconds=sec(delta),part1AnswerPauseRange=[min(frames[i]['duration'] for i in pauses),max(frames[i]['duration'] for i in pauses)],part2Start=sec(finish),parts2to4Exact=True,q017PracticePredecessor=True)
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--input',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--assets',type=Path,required=True);z=a.parse_args()
 assert not z.output.exists()
 o=json.loads(Path(__file__).with_name('overlay.json').read_text())
 p,r=apply(json.loads(z.input.read_text()),o,z.assets)
 if 'newPlanSha256' in o:assert r['newPlanSha256']==o['newPlanSha256']
 write(z.output,p);print(json.dumps(r,indent=2))
