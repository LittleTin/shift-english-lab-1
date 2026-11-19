from pathlib import Path
from copy import deepcopy
import hashlib,json,sys,shutil,argparse
import timing
d=Path(__file__).parent
ca=argparse.ArgumentParser()
ca.add_argument('--input',type=Path,required=True); ca.add_argument('--assets',type=Path,required=True); ca.add_argument('--out',type=Path,required=True)
a=ca.parse_args();assert not a.out.exists();a.out.mkdir()
def sha(b):return hashlib.sha256(b).hexdigest()
def dg(v):return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
R=(d/'compact-advanced-courtyard.json').read_bytes();g0=json.loads((d/'exact-shared-guard.json').read_bytes());g=json.loads(R)
assert sha(R)==g0['draftSha256']=='819a305566412ab6a9bf452e6a27b77b52f45604ab8f229967e5e2670d9554b4'
raw=a.input.read_bytes();p=json.loads(raw);n=deepcopy(p)
assert p['testId']=='test-03'and p['listeningPlan']['duration']==2700
f0=p['listeningPlan']['frames'];f=n['listeningPlan']['frames']
id0=g['sourceGuard']['oldGroupId'];id1=g['group']['id']; old=next(q for q in p['groups']if q['id']==id0)
assert dg(old)==g['sourceGuard']['oldGroupCanonicalSha256']
oq=[q for q in p['questions']if q['groupId']==id0]
assert [q['id']for q in oq]==g['sourceGuard']['oldQuestionIds']
assert {q['id']:dg(q)for q in oq}==g['sourceGuard']['oldQuestionsCanonicalSha256']
idx=[i for i,m in enumerate(f0)if m.get('groupId')==id0]
prevframes=[f0[i]for i in idx]
def no_pace(fr):return [{k:v for k,v in z.items()if k!='at' and not(k=='duration'and z['role']=='answer')}for z in fr]
assert no_pace(prevframes)==no_pace(g['sourceGuard']['oldFrames'])
oldassets=g['sourceGuard']['oldSourceSha256']
for k,h in oldassets.items():timing.guarded_asset(a.assets,{'path':k,'sha256':h})
keepq='t03-q087';chart=next(q for q in p['groups']if q['id']=='t03-g050');assert chart['image']=='assets/graphics/t03-g050.svg'
chartsha=sha((a.assets/chart['image']).read_bytes())
ra=[(i,z)for i,z in enumerate(f0)if z.get('questionId')==keepq]
assert [z['duration']for _,z in ra if z['role']=='answer']==[9.82898]
last=next(i for i,z in enumerate(f0)if z.get('groupId')=='t03-g053-r2')
protect=[z for z in f0[last:]if z.get('groupId')=='t03-g053-r2']
assert [z['questionId']for z in protect if z['role']=='answer']==['t03-q095-r2','t03-q096-r2','t03-q097-r2']
chartq=p['questions'][86];assert chartq['id']==keepq and chartq['groupId']==chart['id']
end=p['listeningPlan']['duration']
sources={'test03-g045-courtyard-shared':Path('/workspace/shared/shift-azure-batch-1112'),'test03-q071-return-box-stem':Path('/workspace/shared/shift-azure-t03-candidate-1101'),
 'test03-q072-formal-stem':Path('/workspace/shared/shift-azure-adv-batch-1050'),'test03-q073-formal-stem':Path('/workspace/shared/shift-azure-adv-batch-1050')}
authorized=Path('/workspace/shared/shift-f0-active-1040/authorized-plan-1112.json').read_bytes()
ar=next(e for e in json.loads(authorized)['items']if e['name']=='test03-g045-courtyard-shared')
ss=g0['shared'];assert ar['turns']==[{k:ss[k]for k in ('voice','locale','text')}]
assert ss['text']==g['group']['audioScript']and sha(ss['text'].encode())==ss['textSha256']
out_assets={}
def asset(name,path,assert_sha,expected_seconds,chars):
 source=sources[name];r=next(z for z in map(json.loads,(source/'sha-receipt.jsonl').read_text().splitlines())if z['name']==name)
 assert r['sha256']==assert_sha and r['seconds']==expected_seconds and r['inputCharacters']==chars
 q=a.assets/path;q.parent.mkdir(parents=True,exist_ok=True)
 if not q.exists():shutil.copyfile(source/(name+'.wav'),q)
 cfg={'path':path,'sha256':assert_sha,'frames':r['samples'],'sampleRate':24000}
 out_assets[path]=cfg
 return timing.inspect_new(a.assets,cfg)
newg=deepcopy(old);newg.update(g['group']);assert newg['audioSpeakers']==old['audioSpeakers']
assert newg['turns']==[{'voice':'F1','text':ss['text']}]; newg['turns']=[{'voice':'female','speaker':'F1','text':ss['text']}]
shared=asset('test03-g045-courtyard-shared',f'audio/exams/test-03/groups/{id1}/passage.wav','b95aed42eeb844f9a53a3622cd2278f727a809f58cfc2b8b4aa2054676826290',41.1125,491)
newg.update(audio=shared['src'],audioStart=shared['start'],audioEnd=shared['end'],duration=shared['duration'])
n['groups'][next(i for i,z in enumerate(n['groups'])if z['id']==id0)]=newg
qs=deepcopy(g['questions']);assert [q['number']for q in qs]==[71,72,73]and [q['answer']for q in qs]==['A','C','B'] and all(q['difficulty']=='advanced'for q in qs)
stems={}
for i,(q,w,name) in enumerate(zip(qs,g0['reusableStems'],('test03-q071-return-box-stem','test03-q072-formal-stem','test03-q073-formal-stem'))):
 assert q['groupId']==id1 and q['id']==oq[i]['id']+'-r2' and q['id'] not in {x['id']for x in p['questions']+p.get('legacyQuestions',[])}
 q.setdefault('tags',['workplace','listening-inference'])
 assert w['script']==f'Number {q["number"]}. {q["prompt"]}'
 used='authorized-plan-1101-t03.json' if i==0 else 'authorized-plan-1050.json'
 pr=Path('/workspace/shared/shift-f0-active-1040')/used
 spec=next(r['turns']for r in json.loads(pr.read_bytes())['items']if r['name']==name)
 assert spec==[{'voice':w['voice'],'locale':'en-US','text':w['script']}]
 stems[oq[i]['id']]=asset(name,f'audio/exams/test-03/questions/Q{q["number"]:03}/formal-stem-r2.wav',w['sha256'],w['seconds'],len(w['script']))
 n['questions'][q['number']-1]=q
st0=idx[0]; delta=0
for i in idx:
 x=f[i]; role=x['role']; q=x.get('questionId'); x['groupId']=id1
 if q:x['questionId']=q+'-r2'
 if role in ('passage','question'):
  new=shared if role=='passage'else stems[q]
  delta+=timing.ticks(new['duration'])-timing.ticks(x['duration'])
  x.update(new)
assert delta==249092
ordinary=[i for i in range(st0,last)if f0[i]['role']=='answer'and f0[i].get('questionId')!=keepq]
assert len(ordinary)==23 and all(f[i]['part']==4 for i in ordinary)
unit,rem=divmod(delta,len(ordinary))
for j,i in enumerate(ordinary):
 t=timing.ticks(f[i]['duration'])-unit-int(j<rem)
 assert t>=634000,'Cannot preserve candidate floor and Q095 absolute anchor; leave held'
 f[i]['duration']=timing.sec(t)
acc=timing.ticks(f0[st0]['at'])
for i in range(st0,last):
 f[i]['at']=timing.sec(acc);acc+=timing.ticks(f[i]['duration'])
assert acc==timing.ticks(f0[last]['at'])
assert f[:st0]==f0[:st0]and f[last:]==f0[last:]
def strip_at(fr):return {k:v for k,v in fr.items()if k!='at'}
assert all(strip_at(f[i])==strip_at(z)for i,z in ra)
for i in range(st0,last):
 if i not in idx or f0[i]['role']not in ('passage','question'):
  assert all(f[i].get(k)==f0[i].get(k)for k in ('src','start','end'))
assert len(timing.audit(f))==100 and n['listeningPlan']['duration']==2700
assert all(n.get(k)==p.get(k)for k in ('previousListeningPlan','alternateListeningPlans','legacyQuestions'))
ops=[]
for i,(u,v) in enumerate(zip(f0,f)):
 if u!=v:ops.append({'index':i,'beforeSha256':dg(u),'updates':{k:x for k,x in v.items()if u.get(k)!=x}})
proof={'intervalFrom':f0[st0]['at'],'preservedAllFramesStartingAt':f0[last]['at'],'newSpeechDeltaSec':timing.sec(delta),
 'ordinaryWindowsAffected':len(ordinary),'minOrdinaryResponseSec':min(f[i]['duration']for i in ordinary),
 'ordinaryResponseSec':{f[i]['questionId']:f[i]['duration']for i in ordinary},
 'q087':{'qid':keepq,'oldChartSha256':chartsha,'image':chart['image'],'assetAndDurationsHash':dg([strip_at(z)for _,z in ra]),'oldAnswer':9.82898,'usedNewAnswer':9.82898},
 'q095GroupFramesSha256':dg(protect),'exact2700':end}
overlay={'status':'candidate-structural-and-guarded-pending-independent-audio-not-published','inputPackSha256':sha(raw),'oldListeningPlanSha256':dg(p['listeningPlan']),'newListeningPlanSha256':dg(n['listeningPlan']),
 'oldGroupId':id0,'oldGroupSha256':dg(old),'oldQuestionSha256':{str(q['number']):dg(q)for q in oq},'newGroup':newg,'newQuestions':qs,'oldMediaSha256':oldassets,
 'newAudioGuards':out_assets,'formalFrameOps':ops,'courtyardDraftSha256':sha(R),'authorizedPlanSha256':sha(authorized),'protected':proof}
hist={'oldGroup':old,'oldQuestions':oq,'oldFormalFrames':prevframes,'oldPlanEdition':p['listeningPlan']['audioEdition'],'oldContentNotPromoted':True}
for na,v in [('candidate.json',n),('overlay.json',overlay),('history-original-g045.json',hist)]:(a.out/na).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print(sha((a.out/'candidate.json').read_bytes()),overlay['newListeningPlanSha256'],proof)
