"""Apply a narrow, SHA-guarded structural listening overlay to a scratch pack."""
import argparse,hashlib,json
from pathlib import Path
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
x=argparse.ArgumentParser(description=__doc__)
x.add_argument('--input',type=Path,required=True);x.add_argument('--output',type=Path,required=True);x.add_argument('--assets',type=Path,required=True)
a=x.parse_args(); assert a.input.resolve()!=a.output.resolve() and not a.output.exists()
blob=Path(__file__).with_name('overlay.json')
o=json.loads(blob.read_text());p=json.loads(a.input.read_text())
t=json.loads(blob.with_name('timing.json').read_text())
for rel,record in t['assets'].items():assert hashlib.sha256((a.assets/rel).read_bytes()).hexdigest()==record['sha256']
assert p['testId']=='test-03' and digest(p['listeningPlan'])==o['oldListeningPlanSha256']
g=next(i for i,x in enumerate(p['groups']) if x['id']==o['oldGroupId']); assert digest(p['groups'][g])==o['oldGroupSha256']; p['groups'][g]=o['newGroup']
for item in o['newQuestions']:
 n=item['number']; i=next(i for i,q in enumerate(p['questions']) if q['number']==n)
 assert digest(p['questions'][i])==o['oldQuestionSha256'][str(n)];p['questions'][i]=item
frames=p['listeningPlan']['frames']
for op in o['formalFrameOps']:
 f=frames[op['index']]; assert digest(f)==op['beforeSha256'];f.update(op['updates'])
assert digest(p['listeningPlan'])==o['newListeningPlanSha256']
a.output.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
