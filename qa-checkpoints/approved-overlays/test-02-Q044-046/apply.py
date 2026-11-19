"""Rebuild an unapproved, one-group scratch candidate, never a release artifact."""
import argparse, copy, hashlib, json, wave
from pathlib import Path
import timing

def dg(v):
 return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def require(ok,reason):
 if not ok: raise ValueError(reason)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
 a=p.parse_args()
 require(not a.output.exists() and a.output.resolve()!=a.input.resolve(),'Output must be a separate, absent file')
 o=json.loads(Path(__file__).with_name('overlay.json').read_text())
 base=json.loads(a.input.read_text()); old=copy.deepcopy(base)
 require(base['testId']==o['testId'] and dg(base['listeningPlan'])==o['oldListeningPlanSha256'],'Old plan drift')
 for g in o['oldAudioGuards']:
  timing.guarded_asset(a.assets,{**g,'path':g['file']})
 for g in o['newAudioGuards'].values():timing.inspect_new(a.assets,g)
 i=next(i for i,g in enumerate(base['groups']) if g['id']==o['oldGroupId'])
 require(dg(base['groups'][i])==o['oldGroupSha256'],'Group drift')
 base['groups'][i]=o['newGroup']
 for q in o['newQuestions']:
  i=next(i for i,x in enumerate(base['questions']) if x['number']==q['number'])
  require(dg(base['questions'][i])==o['oldQuestionSha256'][str(q['number'])],'Question drift')
  base['questions'][i]=q
 frames=base['listeningPlan']['frames']
 for op in o['formalFrameOps']:
  f=frames[op['index']]
  require(dg(f)==op['beforeSha256'],'Frame drift')
  f.update(op['updates'])
 require(dg(base['listeningPlan'])==o['newListeningPlanSha256'],'Result plan drift')
 require(len(timing.audit(frames))==100 and frames[-1]['at']+frames[-1]['duration']==2700,'Invalid formal schedule')
 require(all(base[k]==old[k] for k in ('previousListeningPlan','alternateListeningPlans','legacyQuestions')),'Old history changed')
 require(len({q['id'] for q in base['questions']})==200,'Nonunique active IDs or wrong item count')
 with a.output.open('x') as dst:dst.write(json.dumps(base,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
