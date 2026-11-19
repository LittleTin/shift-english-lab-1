import argparse,hashlib,json,wave
from pathlib import Path
a=argparse.ArgumentParser()
for k in ('input','output','assets'):a.add_argument('--'+k,type=Path,required=True)
a.add_argument('--overlay',type=Path,required=True,action='append')
x=a.parse_args()
def sha(b):return hashlib.sha256(b).hexdigest()
def dg(z):return sha(json.dumps(z,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
raw=x.input.read_bytes(); p=json.loads(raw); f=p['listeningPlan']['frames']; seen=set()
for fi in x.overlay:
 m=json.loads(fi.read_bytes())
 assert m['inputPackSha256']==sha(raw) and m['oldGroupId'] not in seen
 seen.add(m['oldGroupId'])
 for r in m['oldAudio']:assert sha((x.assets/r['src']).read_bytes())==r['assetSha256']
 for src,r in m['newAudio'].items():
  path=x.assets/src
  assert sha(path.read_bytes())==r['sha256']
  with wave.open(str(path)) as h:assert (h.getnchannels(),h.getsampwidth(),h.getframerate(),h.getnframes())==(1,2,24000,r['samples'])
 g=next(g for g in p['groups'] if g['id']==m['oldGroupId']); assert dg(g)==m['oldGroupSha256']
 p['groups'][p['groups'].index(g)]=m['newGroup']
 for q in m['newQuestions']:
  i=q['number']-1; o=p['questions'][i]
  assert dg(o)==m['oldQuestionsSha256'][o['id']] and q['id']==o['id']+'-r2'
  p['questions'][i]=q
 i,j=m['frameIndexes']; assert dg(f[i:j])==m['oldFramesSha256']
 f[i:j]=m['newFrames']
t=0
for f0 in f:
 assert round(f0['at']*1e5)==t;t+=round(f0['duration']*1e5)
assert t==270000000 and len(p['questions'])==200 and len([z for z in f if z['role']=='answer'])==100
b=(json.dumps(p,ensure_ascii=False,indent=2)+'\n').encode()
if len(x.overlay)==1:assert sha(b)==m['outputPackSha256']
with x.output.open('xb') as y:y.write(b)
print(sha(b))
