"""Deterministic exact Test02 final15 replay; refuses wrong prerelease input."""
from pathlib import Path
from hashlib import sha256
import argparse,json
a=argparse.ArgumentParser()
for n in ('base','media-root','output'):a.add_argument('--'+n,type=Path,required=True)
u=a.parse_args()
def sha(b):return sha256(b).hexdigest()
def dg(x):return sha(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
r=json.loads(Path(__file__).with_name('scoped-replay.json').read_bytes())
b=u.base.read_bytes();assert sha(b)==r['inputPackSha256']; p=json.loads(b); assert p['testId']=='test-02'
for _,x in r['newOpus'].items():
 m=u.media_root/x['path'];assert sha(m.read_bytes())==x['encodedSha256']
for n,x in r['newQuestions'].items():
 i=int(n)-1
 assert dg(p['questions'][i])==x['beforeSha256'];p['questions'][i]=x['active']
for x in r['labelOnly']:
 q=p['questions'][x['number']-1];assert dg(q)==x['beforeSha256'];q['difficulty']=x['level']
f=p['listeningPlan']['frames']
for x in r['frames']:
 i=x['index'];assert dg(f[i])==x['beforeSha256'];f[i]=x['active']
assert all(dg(f[int(i)])==h for i,h in r['chartFrames'].items()) and dg(p['listeningPlan'])==r['outputTimingSha256']
assert len(p['questions'])==200 and sum(round(x['duration']*1e5) for x in f)==2700*100000
assert not {'previousListeningPlan','alternateListeningPlans','legacyQuestions'}&p.keys()
out=(json.dumps(p,ensure_ascii=False,indent=2)+'\n').encode()
assert sha(out)==r['outputPackSha256']
with u.output.open('xb') as w:w.write(out)
print(sha(out))
