"""Exact predecessor replay. Subsets can be replayed only from the pinned predecessor."""
from copy import deepcopy
from pathlib import Path
import hashlib, json, argparse
import timing
def sha(x):return hashlib.sha256(x).hexdigest()
def dg(x):return sha(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def apply(raw,overlay,assets,selected=None):
 p=json.loads(raw); f=p['listeningPlan']['frames']; o=overlay
 assert p['testId']==o['testId'] and sha(raw)==o['predecessorPackSha256'] and dg(p['listeningPlan'])==o['predecessorPlanSha256']
 assert all(sha(timing.guarded_asset(assets,dict(path=k,sha256=v)).read_bytes())==v for k,v in o['oldMediaSha256'].items())
 units={x['number']:x for x in o['units']}; chosen=set(selected or units)
 assert chosen and chosen<=units.keys()
 gids=set()
 for n in sorted(chosen):
  x=units[n]
  qi,=[i for i,q in enumerate(p['questions']) if q['number']==n];q=p['questions'][qi]
  gi,=[i for i,g in enumerate(p['groups']) if g['id']==q['groupId']];g=p['groups'][gi]
  assert dg(q)==x['oldQuestionSha256'] and dg(g)==x['oldGroupSha256']
  assert q['answer']==x['newQuestion']['answer']
  w={m:timing.inspect_new(assets,s) for m,s in x['audio'].items()}
  g2=x['newGroup']; assert (g2['audio'],g2['audioStart'],g2['audioEnd'])==(w['practice']['src'],w['practice']['start'],w['practice']['end'])
  p['questions'][qi]=x['newQuestion']; p['groups'][gi]=g2;gids.add(g['id'])
 for x in o['frameOperations']:
  k=x['index']; old=f[k]; new=x['replace']
  assert dg(old)==x['originalSha256']
  if old['groupId'] in gids:f[k]=new
 timing.audit(f)
 if chosen==units.keys():assert dg(p['listeningPlan'])==o['successorPlanSha256']
 return p
if __name__=='__main__':
 a=argparse.ArgumentParser()
 for flag in ('input','output','assets','overlay'):a.add_argument('--'+flag,type=Path,required=True)
 a.add_argument('--select',nargs='+',type=int); z=a.parse_args()
 assert not z.output.exists()
 p=apply(z.input.read_bytes(),json.loads(z.overlay.read_bytes()),z.assets,z.select)
 z.output.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
