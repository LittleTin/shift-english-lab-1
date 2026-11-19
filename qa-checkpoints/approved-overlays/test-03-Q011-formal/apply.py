"""Scoped Part 2 exact unchanged-word, one-mode overlays; candidate until independent QA."""
from pathlib import Path
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import argparse,hashlib,json,wave
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dig(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def tick(x):return int((Decimal(str(x))*100000).to_integral_value(rounding=ROUND_HALF_UP))
def one(rows,**kw):
 x,=[x for x in rows if all(x.get(k)==v for k,v in kw.items())];return x
def apply(p,o,d):
 s=p['testId']; assert s==o['testId']
 q=one(p['questions'],number=o['number']);g=one(p['groups'],id=q['groupId']);fs=p['listeningPlan']['frames']
 assert dig(q)==o['questionSha256'] and dig(g)==o['groupSha256'] and dig(p['listeningPlan'])==o['oldPlanSha256']
 ind={fs[i]['role']:i for i in range(len(fs)) if fs[i].get('groupId')==g['id']}; assert set(ind)=={'cue','passage','answer'}
 old=[fs[ind[k]] for k in ('cue','passage','answer')];assert [dig(x) for x in old]==o['oldFrameSha256']
 assert all(sha(d/src)==h for src,h in o['oldAudio'].items())
 n=o['asset'];file=d/n['path']; assert sha(file)==n['sha256']
 with wave.open(str(file),'rb') as a:
  assert (a.getnchannels(),a.getsampwidth(),a.getframerate(),a.getnframes())==(1,2,24000,n['samples'])
  assert len(a.readframes(n['samples']))==2*n['samples'] and n['samples']/24000==n['seconds']
 o2=deepcopy(p); f=o2['listeningPlan']['frames']; gg=one(o2['groups'],id=g['id'])
 if o['mode']=='practice':
  gg.update(audio=n['path'],audioStart=0,audioEnd=n['seconds'],duration=n['seconds'])
  assert f==fs and gg['turns']==g['turns']
 else:
  i,j=ind['passage'],ind['answer']; assert j==i+1
  end=tick(fs[j+1]['at']); start=tick(fs[i]['at']); new_end=start+tick(n['seconds']);new_wait=end-new_end
  assert new_wait>=tick(4) and new_end+new_wait==end
  f[i].update(src=n['path'],start=0,end=n['seconds'],duration=n['seconds'])
  f[j].update(at=new_end/100000,duration=new_wait/100000)
  assert all(x==y for k,(x,y) in enumerate(zip(f,fs)) if k not in (i,j))
  assert gg==g
 assert o2['questions']==p['questions'] and all(o2.get(k)==p.get(k) for k in ('previousListeningPlan','alternateListeningPlans','legacyQuestions'))
 assert len(f)==284 and sum(x['role']=='answer' for x in f)==100 and tick(f[-1]['at'])+tick(f[-1]['duration'])==270000000
 if o.get('newPlanSha256'):assert dig(o2['listeningPlan'])==o['newPlanSha256']
 return o2
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--input',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--assets',type=Path,required=True);a.add_argument('--overlay',type=Path,default=Path(__file__).with_name('overlay.json'));z=a.parse_args();assert not z.output.exists();write(z.output,apply(read(z.input),read(z.overlay),z.assets))
