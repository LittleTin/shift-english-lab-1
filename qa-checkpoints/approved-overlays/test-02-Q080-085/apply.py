"""Apply exact selected Test02 repaired scopes to a never-published scratch pack."""
from copy import deepcopy
from pathlib import Path
import argparse,hashlib,json
import timing
def sha(x):return hashlib.sha256(x).hexdigest()
def dg(x):return sha(json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode())
def need(ok,bad):
 if not ok:raise ValueError(bad)
def main():
 a=argparse.ArgumentParser(description=__doc__)
 a.add_argument('--input',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--assets',type=Path,required=True)
 args=a.parse_args()
 need(not args.output.exists()and args.output.resolve()!=args.input.resolve(),'Invalid output path')
 overlay=json.loads(Path(__file__).with_name('overlay.json').read_bytes())
 data=args.input.read_bytes();pack=json.loads(data);old=deepcopy(pack)
 need(pack['testId']=='test-02'and dg(pack['listeningPlan'])==overlay['oldListeningPlanSha256'],'Unexpected predecessor plan')
 cg=overlay['chartGuard']; chk=lambda f:dg([x for x in f if x.get('questionId')=='t02-q085-v2'])
 need(sha((args.assets/cg['path']).read_bytes())==cg['sha256'],'Chart image drift')
 need(chk(pack['listeningPlan']['frames'])==cg['framesSha'],'Predecessor chart frame drift')
 for path,h in overlay['oldMediaSha256'].items(): timing.guarded_asset(args.assets,{'path':path,'sha256':h})
 for g in overlay['newAudioGuards'].values():timing.inspect_new(args.assets,g)
 for g in overlay['units']:
  i=next(i for i,b in enumerate(pack['groups'])if b['id']==g['groupId'])
  need(dg(pack['groups'][i])==g['oldGroupSha256'],'Stale old group')
  pack['groups'][i]=g['newGroup']
  for q in g['newQuestions']:
   i=next(i for i,b in enumerate(pack['questions'])if b['id']==q['id'])
   need(dg(pack['questions'][i])==g['oldQuestionSha256'][q['id']],'Stale item')
   pack['questions'][i]=q
 for op in overlay['formalFrameOps']:
  f=pack['listeningPlan']['frames'][op['index']]
  need(dg(f)==op['beforeSha256'],'Stale formal frame')
  f.update(op['updates'])
 need(dg(pack['listeningPlan'])==overlay['newListeningPlanSha256'],'Unexpected result plan')
 fs=pack['listeningPlan']['frames']
 need(chk(fs)==cg['framesSha'],'Chart question/answer interval changed')
 need(len(timing.audit(fs))==100 and pack['listeningPlan']['duration']==2700,'Invalid timing or count')
 need([q['id']for q in pack['questions']]==[q['id']for q in old['questions']] and [q['answer']for q in pack['questions']]==[q['answer']for q in old['questions']],'Current IDs/keys changed')
 need(all(pack[k]==old[k]for k in ('previousListeningPlan','alternateListeningPlans','legacyQuestions')),'History changed')
 with args.output.open('x') as f:f.write(json.dumps(pack,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
