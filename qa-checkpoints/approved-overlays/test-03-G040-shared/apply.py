import argparse,copy,hashlib,json,pathlib,wave
D=pathlib.Path(__file__).parent
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def issue(xs,k,v):
 q,=[x for x in xs if x.get(k)==v];return q
def wt(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def tick(n):return round(n*100000)
def content(q):return q['id'],q['part'],q['number'],q['prompt'],q['promptZh'],q['answer'],[(x['id'],x['text'],x['zh']) for x in q['options']]
def unsigned(p,site,o):
 assert p['testId']==o['testId'] and digest(p['listeningPlan'])==o['checkedPredecessorSha256']
 for gid,u in o['groups'].items():
  g=issue(p['groups'],'id',gid);assert digest(g)==u['oldGroupSha256'] and u['newGroup']['audioSpeakers']==g['audioSpeakers']
  for q in u['newQuestions']:
   old=issue(p['questions'],'id',q['id']);assert digest(old)==u['oldQuestionSha256'][q['id']] and content(q)==content(old)
   assert q['groupId']==u['newGroup']['id']
  fr=[x for x in p['listeningPlan']['frames'] if x['groupId']==gid]
  assert [digest(x) for x in fr]==u['oldFrameSha256'] and [x for x in fr if x.get('src')]==u['roleRanges']
  assert all(h(site/r)==s for r,s in u['oldSources'].items())
  s=u['imageSha256']
  if s:
   assert h(site/g['image'])==s
   assert all(u['newGroup'][k]==g[k] for k in ('graphicText','imageAlt','image'))
  else:assert not g.get('image')
def apply(prev,site,o,receipts,wavs,selected):
 unsigned(prev,site,o);p=copy.deepcopy(prev);frames=p['listeningPlan']['frames'];old=prev['listeningPlan']['frames']; changed=set(); audit={}
 for gid in selected:
  u=o['groups'][gid];new=u['newShared'];a=issue(receipts,'name',new['name']);src=wavs/(a['name']+'.wav')
  if not src.is_file():src=wavs/new['path']
  assert a['status']=='rendered-candidate-not-validated' and h(src)==a['sha256'] and len(src.read_bytes())==a['bytes']
  assert a['inputCharacters']==sum(len(t['text']) for t in new['turns'])
  with wave.open(str(src),'rb') as w:assert (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())==(24000,1,2,a['samples']) and w.getnframes()/24000==a['seconds']
  inds=[i for i,x in enumerate(frames) if x['groupId']==gid]; assert inds==list(range(inds[0],inds[-1]+1)) and not changed.intersection(inds); changed.update(inds)
  ip,=[i for i in inds if frames[i]['role']=='passage']
  ap=[i for i in inds if frames[i]['role']=='answer'];assert len(ap)==3
  delta=tick(old[ip]['duration'])-tick(a['seconds']);assert delta>=0, 'Exceeds local speech budget: no implicit shortening of pauses; separate reviewed retiming required'
  start=tick(old[inds[0]]['at']);after=tick(old[inds[-1]+1]['at'])
  group=copy.deepcopy(u['newGroup']);group.update(audio=new['path'],audioStart=0,audioEnd=a['seconds'],duration=a['seconds'])
  p['groups'][p['groups'].index(issue(p['groups'],'id',gid))]=group
  for q in u['newQuestions']:p['questions'][p['questions'].index(issue(p['questions'],'id',q['id']))]=q
  frames[ip].update(src=new['path'],start=0,end=a['seconds'],duration=a['seconds'])
  each,rem=divmod(delta,len(ap))
  for j,i in enumerate(ap):frames[i]['duration']=(tick(frames[i]['duration'])+each+(j<rem))/100000
  at=start
  for i in inds:
   frames[i].update(at=at/100000,groupId=group['id']);at+=tick(frames[i]['duration'])
   if i!=ip and i not in ap:assert all(frames[i].get(k)==old[i].get(k) for k in ('src','start','end','role','part','questionId','duration'))
  assert at==after
  audit[gid]=dict(sha256=a['sha256'],path=new['path'],duration=a['seconds'],deltaLocal=delta/100000,answerWindows=[frames[i]['duration'] for i in ap])
 assert all(f==old[i] for i,f in enumerate(frames) if i not in changed)
 assert all(p.get(k)==prev.get(k) for k in o['historyKeys'])
 assert len(frames)==284 and sum(f['role']=='answer' for f in frames)==100 and tick(frames[-1]['at'])+tick(frames[-1]['duration'])==270000000
 return p,dict(status='local-candidate-not-verified',oldPlanSha256=digest(prev['listeningPlan']),newPlanSha256=digest(p['listeningPlan']),groups=audit,seconds=2700,frames=284,answerWindows=100,historyExact=True,otherFramesExact=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--pack',type=pathlib.Path,required=True);a.add_argument('--site',type=pathlib.Path,required=True);a.add_argument('--authorized-plan',type=pathlib.Path);a.add_argument('--receipts',type=pathlib.Path);a.add_argument('--wavs',type=pathlib.Path);a.add_argument('--out',type=pathlib.Path);a.add_argument('--select',nargs='+',default=['t03-g032','t03-g040']);z=a.parse_args()
 p=json.loads(z.pack.read_text());o=json.loads((D/'candidate-overlay.json').read_text())
 if not z.receipts:
  unsigned(p,z.site,o);print('PASS exact predecessor, six stems, both cues, both old shared bytes, bilingual key/choice invariants and Q057 group graphic');sys_exit=0
 else:
  assert z.authorized_plan and z.wavs and z.out and not z.out.exists() and len(z.select)==len(set(z.select))
  authorized=json.loads(z.authorized_plan.read_text())['items']
  for gid in z.select:
   n=o['groups'][gid]['newShared']; assert issue(authorized,'name',n['name'])['turns']==n['turns']
  raw=z.receipts.read_text();receipts=json.loads(raw) if raw.lstrip().startswith('[') else [json.loads(x) for x in raw.splitlines() if x.strip()]
  q,t=apply(p,z.site,o,receipts,z.wavs,z.select)
  if o.get('approvedSuccessorPlanSha256'):assert t['newPlanSha256']==o['approvedSuccessorPlanSha256']
  wt(z.out,q);print(json.dumps(t,indent=2))
