"""Compose only Q084 after the approved Test03 Q095–097 overlay."""
import argparse,copy,hashlib,json,wave
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tick(x):return int((Decimal(str(x))*100000).to_integral_value(rounding=ROUND_HALF_UP))
def sec(x):return x/100000
def obj(xs,k,val):
 a,=[y for y in xs if y.get(k)==val];return a
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def apply(old,ov,assets):
 assert old['testId']=='test-03' and digest(old['listeningPlan'])==ov['oldPlanSha256']
 p=copy.deepcopy(old);fs=p['listeningPlan']['frames'];orig=old['listeningPlan']['frames']
 q=obj(p['questions'],'number',84); k=p['questions'].index(q); newq=ov['newQuestion']
 assert digest(q)==ov['oldQuestionSha256'] and q.keys()==newq.keys() and all(newq[key]==q[key] for key in q if key not in {'prompt','promptZh'})
 g=obj(p['groups'],'id','t03-g049'); j=p['groups'].index(g)
 assert digest(g)==ov['oldGroupSha256'] and g.keys()==ov['newGroup'].keys() and all(g[key]==ov['newGroup'][key] for key in g if key!='passageZh')
 p['groups'][j]=ov['newGroup'];p['questions'][k]=newq
 for n,expected in ov['siblingQuestionGuard'].items():assert digest(obj(p['questions'],'number',int(n)))==expected
 a=ov['newAsset']; path=assets/a['path']; assert h(path)==a['sha256']
 with wave.open(str(path),'rb') as w:assert (w.getframerate(),w.getsampwidth(),w.getnchannels(),w.getnframes())==(24000,2,1,a['samples'])
 seconds=sec(tick(Decimal(a['samples'])/24000))
 for path,expected in ov['oldSourceAssets'].items():assert h(assets/path)==expected
 idx,=[i for i,f in enumerate(fs) if f.get('questionId')==q['id'] and f['role']=='question']
 stem=fs[idx]; assert digest(stem)==ov['oldFormalStemSha256']
 stem.update(src=a['path'],start=0,end=seconds,duration=seconds)
 part4=[i for i,f in enumerate(fs) if f['part']==4]; begin=min(part4); assert part4==list(range(begin,len(fs)))
 pauses=[i for i in part4 if fs[i]['role']=='answer' and fs[i]['questionId'] not in ov['protectedQuestionIds']];assert len(pauses)==29
 start=tick(orig[begin]['at']);end=270000000
 lens={i:tick(fs[i]['duration']) for i in part4}; added=tick(seconds)-tick(orig[idx]['duration'])
 assert sum(lens.values())+start-end==added and added==143588
 each,rem=divmod(added,len(pauses))
 for j,i in enumerate(pauses):
  cut=each+(j<rem); assert 0<cut<=5000
  lens[i]-=cut;fs[i]['duration']=sec(lens[i])
 cursor=start
 for i in part4:fs[i]['at']=sec(cursor);cursor+=lens[i]
 assert cursor==end and fs[:begin]==orig[:begin] and len(fs)==len(orig)==284
 assert sum(f['role']=='answer' for f in fs)==100
 for i,(f,b) in enumerate(zip(fs,orig)):
  assert all(f.get(x)==b.get(x) for x in ('role','part','groupId','questionId'))
  if i!=idx:assert all(f.get(x)==b.get(x) for x in ('src','start','end','speakers'))
  if i not in pauses and i!=idx:assert f['duration']==b['duration']
 assert all(p.get(entry)==old.get(entry) for entry in ('previousListeningPlan','alternateListeningPlans','legacyQuestions'))
 r=dict(status='isolated-item-proof-not-browser-acceptance',newPlanSha256=digest(p['listeningPlan']),oldStem=orig[idx]['duration'],newStem=seconds,addedSpeechSeconds=sec(added),ordinarySharedPauses=len(pauses),ordinaryPauseCutRange=[sec(each),sec(each+bool(rem))],minOrdinaryPart4Pause=min(fs[i]['duration'] for i in pauses),chartQ087Pause=next(x['duration'] for x in fs if x.get('questionId')=='t03-q087' and x['role']=='answer'),part4EntrySeconds=sec(start),totalFrames=len(fs),answerFrames=100,seconds=sec(cursor))
 assert r['chartQ087Pause']==9.82898 and r['minOrdinaryPart4Pause']>=6.45
 return p,r
if __name__=='__main__':
 x=argparse.ArgumentParser(description=__doc__)
 x.add_argument('--input',type=Path,required=True);x.add_argument('--output',type=Path,required=True);x.add_argument('--assets',type=Path,required=True);a=x.parse_args()
 assert not a.output.exists()
 ov=json.loads(Path(__file__).with_name('overlay.json').read_text())
 new,receipt=apply(json.loads(a.input.read_text()),ov,a.assets)
 if 'newPlanSha256' in ov:assert receipt['newPlanSha256']==ov['newPlanSha256']
 write(a.output,new);print(json.dumps(receipt,indent=2))
