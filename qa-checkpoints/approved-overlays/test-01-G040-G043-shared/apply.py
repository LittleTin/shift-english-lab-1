"""Compose exact selected Test01 held-group shared dialogue repairs without global retiming."""
import argparse,copy,hashlib,json,wave
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def tick(x):return int((Decimal(str(x))*100000).to_integral_value(rounding=ROUND_HALF_UP))
def sec(x):return x/100000
def issue(xs,k,v):
 q,=[x for x in xs if x.get(k)==v];return q
def wf(path,x):path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def apply(old,o,selected,media):
 assert old['testId']=='test-01' and digest(old['listeningPlan'])==o['oldPlanSha256'] and len(selected)==len(set(selected))
 p=copy.deepcopy(old);fr=p['listeningPlan']['frames'];of=old['listeningPlan']['frames'];edited=set();statuses={}
 for gid in selected:
  u=o['groups'][gid];oldg=issue(p['groups'],'id',gid);assert digest(oldg)==u['oldGroupSha256']
  g=u['newGroup']; assert not any(x['id']==g['id'] for x in p['groups']); a=u['newShared']
  assert h(media/a['path'])==a['sha256'] and g['audio']==a['path'] and g['audioEnd']==a['seconds']
  with wave.open(str(media/a['path']),'rb') as w:assert (w.getframerate(),w.getsampwidth(),w.getnchannels(),w.getnframes())==(24000,2,1,a['samples']) and w.getnframes()/24000==a['seconds']
  for path,hash in u['oldSources'].items():assert h(media/path)==hash
  p['groups'][p['groups'].index(oldg)]=g
  for q in u['newQuestions']:
   existing=issue(p['questions'],'id',q['id'])
   assert digest(existing)==u['oldQuestionSha256'][q['id']] and existing['answer']==q['answer'] and q['groupId']==g['id']
   assert existing['prompt']==q['prompt'] and existing['promptZh']==q['promptZh'] and [(x['id'],x['text'],x['zh']) for x in q['options']]==[(x['id'],x['text'],x['zh']) for x in existing['options']]
   p['questions'][p['questions'].index(existing)]=q
  inds=[i for i,f in enumerate(fr) if f['groupId']==gid]; start,end=inds[0],inds[-1]+1
  assert inds==list(range(start,end)) and not edited.intersection(inds)
  assert [digest(fr[i]) for i in inds]==u['oldFrameSha256']
  edited.update(inds)
  astart=tick(of[start]['at']);afinish=tick(of[end]['at'])
  pas,=[i for i in inds if fr[i]['role']=='passage']; delta=tick(of[pas]['duration'])-tick(a['seconds']); assert delta>0
  pause=[i for i in inds if fr[i]['role']=='answer'];assert len(pause)==3
  lens={i:tick(fr[i]['duration']) for i in inds};lens[pas]=tick(a['seconds'])
  fr[pas].update(src=a['path'],start=0,end=a['seconds'],duration=a['seconds']);assert fr[pas]['speakers']==g['audioSpeakers']
  each,rem=divmod(delta,3)
  for j,i in enumerate(pause):
   lens[i]+=each+(j<rem);fr[i]['duration']=sec(lens[i])
  at=astart
  for i in inds:fr[i].update(at=sec(at),groupId=g['id']);at+=lens[i]
  assert at==afinish
  for i in inds:
   assert all(fr[i].get(k)==of[i].get(k) for k in ('role','part','questionId','speakers'))
   if i!=pas:assert all(fr[i].get(k)==of[i].get(k) for k in ('src','start','end'))
   if i!=pas and i not in pause:assert fr[i]['duration']==of[i]['duration']
  statuses[gid]=dict(localGainedSeconds=sec(delta),answerSeconds=[fr[i]['duration'] for i in pause],unchangedStart=sec(astart),unchangedFollowing=sec(afinish))
 assert all(a==b for i,(a,b) in enumerate(zip(fr,of)) if i not in edited)
 assert len(fr)==len(of)==284 and sum(f['role']=='answer' for f in fr)==100 and tick(fr[-1]['at'])+tick(fr[-1]['duration'])==270000000
 assert all(p.get(k)==old.get(k) for k in ('legacyQuestions','previousListeningPlan','alternateListeningPlans'))
 return p,dict(status='isolated-group-local-offline-structure-not-browser-proof',oldPlanSha256=o['oldPlanSha256'],newPlanSha256=digest(p['listeningPlan']),seconds=2700,frames=284,answerWindows=100,otherFramesExact=True,groups=statuses)
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--input',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--assets',type=Path,required=True);a.add_argument('--select',nargs='+',required=True); z=a.parse_args()
 assert not z.output.exists()
 o=json.loads(Path(__file__).with_name('overlay.json').read_text());p,r=apply(json.loads(z.input.read_text()),o,z.select,z.assets)
 if 'newPlanSha256' in o:assert r['newPlanSha256']==o['newPlanSha256']
 wf(z.output,p); print(json.dumps(r,indent=2))
