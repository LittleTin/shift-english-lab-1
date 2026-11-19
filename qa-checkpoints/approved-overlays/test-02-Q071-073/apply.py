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
 for path,h in overlay['oldAudioSha256'].items():timing.guarded_asset(args.assets,{'path':path,'sha256':h})
 for g in overlay['newAudioGuards'].values():timing.inspect_new(args.assets,g)
 chart=overlay['chartGuard']; cg=chart['groupId']
 need(sha((args.assets/chart['imagePath']).read_bytes())==chart['imageSha256'],'Chart drift')
 need(dg([f for f in pack['listeningPlan']['frames']if f.get('groupId')==cg])==chart['formalFramesCanonicalSha256'],'Chart formal scope drift')
 i=next(i for i,g in enumerate(pack['groups'])if g['id']==overlay['oldGroupId'])
 need(dg(pack['groups'][i])==overlay['oldGroupSha256'],'Stale old group')
 pack['groups'][i]=overlay['newGroup']
 for q in overlay['newQuestions']:
  i=next(i for i,b in enumerate(pack['questions'])if b['number']==q['number'])
  need(dg(pack['questions'][i])==overlay['oldQuestionSha256'][str(q['number'])],'Stale item')
  pack['questions'][i]=q
 for op in overlay['formalFrameOps']:
  f=pack['listeningPlan']['frames'][op['index']]
  need(dg(f)==op['beforeSha256'],'Stale formal frame')
  f.update(op['updates'])
 need(dg(pack['listeningPlan'])==overlay['newListeningPlanSha256'],'Unexpected result plan')
 need(dg([f for f in pack['listeningPlan']['frames']if f.get('groupId')==cg])==chart['formalFramesCanonicalSha256'],'Chart retiming not allowed')
 fs=pack['listeningPlan']['frames']
 need(len(timing.audit(fs))==100 and pack['listeningPlan']['duration']==2700,'Invalid timing or count')
 need(all(a==b for a,b in zip(pack['questions'],old['questions'])if b['number'] not in (71,72,73)),'Unrelated items changed')
 need(all(pack[k]==old[k]for k in ('previousListeningPlan','alternateListeningPlans','legacyQuestions')),'History changed')
 with args.output.open('x') as f:f.write(json.dumps(pack,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
