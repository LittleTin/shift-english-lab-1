from pathlib import Path
import argparse,hashlib,json
from copy import deepcopy
import timing
def sha(x):return hashlib.sha256(x).hexdigest()
def dg(v):return sha(json.dumps(v,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode())
def need(g,msg):
 if not g:raise ValueError(msg)
a=argparse.ArgumentParser()
a.add_argument('--input',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--assets',type=Path,required=True);a.add_argument('--overlay',type=Path,default=Path(__file__).with_name('overlay.json'))
a=a.parse_args(); need(not a.output.exists(),'Output already exists')
m=json.loads(a.overlay.read_bytes());data=a.input.read_bytes();p=json.loads(data)
need(p['testId']=='test-03' and dg(p['listeningPlan'])==m['oldListeningPlanSha256'],'Stale predecessor plan; use guarded prepare against current input')
orig=deepcopy(p)
def chart(fs):
 q=m['protected']['q087']
 return dg([{k:v for k,v in x.items()if k!='at'}for x in fs if x.get('questionId')==q['qid']])
q=m['protected']['q087']; need(sha((a.assets/q['image']).read_bytes())==q['oldChartSha256'],'Changed chart')
f=p['listeningPlan']['frames'];need(chart(f)==q['assetAndDurationsHash'],'Existing chart interval changed')
for path,h in m['oldMediaSha256'].items(): timing.guarded_asset(a.assets,{'path':path,'sha256':h})
for x in m['newAudioGuards'].values():timing.inspect_new(a.assets,x)
i=next(i for i,q in enumerate(p['groups'])if q['id']==m['oldGroupId'])
need(dg(p['groups'][i])==m['oldGroupSha256'],'Stale target group')
p['groups'][i]=m['newGroup']
for n in m['newQuestions']:
 i=next(j for j,b in enumerate(p['questions'])if b['number']==n['number']); need(dg(p['questions'][i])==m['oldQuestionSha256'][str(n['number'])],'Stale question')
 p['questions'][i]=n
for c in m['formalFrameOps']:
 fx=f[c['index']];need(dg(fx)==c['beforeSha256'],'Changed frame');fx.update(c['updates'])
need(dg(p['listeningPlan'])==m['newListeningPlanSha256'],'Unexpected timing')
need(chart(f)==q['assetAndDurationsHash'],'Q087 source or duration moved')
need(dg([x for x in f if x.get('groupId')=='t03-g053-r2'])==m['protected']['q095GroupFramesSha256'],'Q095–097 protected frame changed')
need(len(timing.audit(f))==100 and p['listeningPlan']['duration']==2700,'Bad duration')
need(all(p.get(k)==orig.get(k)for k in ('previousListeningPlan','alternateListeningPlans','legacyQuestions')),'History changed')
with a.output.open('x') as w:w.write(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
