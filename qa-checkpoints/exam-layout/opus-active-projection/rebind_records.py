#!/usr/bin/env python3
"""Rebind only reviewed changed rows, with compact associations for all active slots."""
from pathlib import Path
import argparse,copy,hashlib,json,shutil,sys
from collections import Counter
def j(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dj(o):return hashlib.sha256(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def wr(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
p=argparse.ArgumentParser()
for k in ('proof','base-ledger','reconcile','difficulty-tool','new-inputs','out'):p.add_argument('--'+k,type=Path,required=True)
p.add_argument('--include-opus',action='store_true',help='Optional staged binaries; default is compact proof only')
for k in ('raw-pack','reserve'):p.add_argument('--'+k,type=Path,action='append',default=[])
a=p.parse_args()
sys.path[:0]=[str(a.reconcile),str(a.difficulty_tool)]
from reconcile import want_audio,check_audio,check_item_vocabulary,run,isequal
from difficulty_gate import check,review_record,summarize
assert not a.out.exists()
meta=j(a.proof/'asset-report.json');mapping=meta['mapping'];site=a.proof/'site'; by_raw={r:(s,u) for s,u in meta['assets'].items() for r in u['sourcePaths']}; assert set(by_raw)==set(mapping)
raw={x['testId']:(y,x) for y in a.raw_pack for x in [j(y)]}
new=j(a.new_inputs)
for t,x in meta['packs'].items():
 f,b=raw[t];assert sha(f)==x['sourcePackSha256'] and dj(b['listeningPlan'])==x['beforePlanSha256']
 out=site/'data'/f'{t}.json';assert sha(out)==x['opusPackSha256'] and dj(j(out)['listeningPlan'])==x['opusPlanSha256']
for r,(s,b) in by_raw.items():assert b['path']==mapping[r] and sha(site/b['path'])==b['encodedSha256']
seen=set();eligible={}; allitems={};changed={};usedchanged=set();totals={}
scratch=a.out/'mounted-checks'
top=a.out/'transfer'; qroot=top/'qa-checkpoints'; proof=qroot/'exam-layout/opus-active-projection'; rebound=proof/'scoped-rebound'
for t,(filename,p0) in raw.items():
 p1=j(site/'data'/f'{t}.json');g0={g['id']:g for g in p0['groups']};g1={g['id']:g for g in p1['groups']};assert set(g0)==set(g1)
 units={};levels={}
 for i,q in enumerate(p0['questions'],1):
  slot=f'{i:03}';assert q==p1['questions'][i-1] and q['number']==i
  key=q.get('groupId'); gr=g0.get(key); go=g1.get(key)
  if gr:
   expected=copy.deepcopy(gr)
   if r:=gr.get('audio'):expected['audio']=mapping[r]
   assert expected==go
  m=new.get(t,{}).get(str(i))
  ver=(Path(m['verified-items']['path']) if m else a.base_ledger/f'verified-items/{t}/Q{slot}.json')
  dif=(Path(m['difficulty']['path']) if m else a.base_ledger/f'difficulty/{t}/Q{slot}.json')
  if m:assert sha(ver)==m['verified-items']['sha256'] and sha(dif)==m['difficulty']['sha256'];seen.add((t,i))
  row=j(ver); d=j(dif);assert row['activeQuestion']==q and row.get('group')==gr
  lev=check(d,t,q,gr);levels[i]=lev;units.setdefault(('listening' if i<=100 else 'reading',key or q['id']),[]).append(i)
  if gr and gr.get('image'):
   im=gr['image'];assert sha(site/im)==row['imageSha256']
  ru=copy.deepcopy(row);ru['group']=go
  if q['part']<=4:
   rn=ru['audio'];cue=any(u.get('mode')=='cue' for u in rn)
   expected=want_audio(p0,q,gr,has_cue=cue); actual=want_audio(p1,q,go,has_cue=cue)
   check_audio(row,expected,lambda f,*_:by_raw[f][0])
   for r in rn:
    s,x=by_raw[r['path']]; rawpath=r['path']; assert r['assetSha256']==s
    p16=r.pop('pcm16kMonoSha256',None)
    r.update(path=x['path'],assetSha256=x['encodedSha256'],sourceAudioProvenance=dict(path=rawpath,sha256=s,decodedSamples48k=x['decodedSamples'],sourceCodec=x['sourceCodec'],deliveryCodec='opus',preSkipSamples=x['preSkipSamples'],sourceEvidencePcm16kMonoSha256=p16))
    if m:usedchanged.add(x['path'])
   check_audio(ru,actual,lambda f,*_:sha(site/f))
  check_item_vocabulary(q)
  if m:
   ru['checks']['codecProjection']='Both modes use the exact deterministic 48kHz Ogg Opus delivery bytes/ranges; raw hashes remain provenance. Source and decoded Opus samples match in duration; Ogg gapless pre-skip/final granule and unmodified timetable verified. Original semantic decision was made on the checked source clips.'
   rr=review_record(t,i,ru,lev,d['reason'],d['provenance']+' Exact Opus association only; no difficulty reasoning change.')
   assert check(rr,t,q,go)==lev
   wr(rebound/f'verified-items/{t}/Q{slot}.json',ru);wr(rebound/f'difficulty/{t}/Q{slot}.json',rr)
   changed[(t,i)]={'markers':[sha(rebound/f'verified-items/{t}/Q{slot}.json'),sha(rebound/f'difficulty/{t}/Q{slot}.json')],'rawRecordSha256':[sha(ver),sha(dif)]}
  allitems.setdefault(t,[]).append([i,q['id'],sha(ver),sha(dif),dj(go),lev])
 for k in ('listening','reading'):
  x={u:v for u,v in units.items() if u[0]==k}; vals={i:v for i,v in levels.items() if (i<=100)==(k=='listening')}
  tot=summarize(x,vals); c=tot['reviewedCounts']; cp=tot['completePracticeQuestionCounts']
  pass_=c['intermediate']>max(c['foundation'],c['advanced']) and all(c[l]>=3 and cp[l]>=3 for l in ('foundation','advanced'))
  totals.setdefault(t,{})[k]=dict(**tot,distributionAccepted=pass_)
assert sum(map(len,allitems.values()))==600 and len(seen)==sum(map(len,new.values()))
for f in a.reserve:
 x=j(f)
 assert set(x)=={'test','group','history'}
 wr(top/'question-reserve'/x['test']/x['group']/'original-medium-rotation-snapshot.json',x['history'])
if a.include_opus:
 for path in usedchanged:
  row=next(x for x in meta['assets'].values() if x['path']==path)
  target=top/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(site/path,target)
  assert sha(target)==row['encodedSha256']
output=dict(status='scoped-delivery-opus-binding-not-difficulty-or-publish',rawPathProjectionSha256=sha(a.proof/'asset-report.json'),packs=meta['packs'],items=allitems,changed={f'{t}/Q{i:03}':k for (t,i),k in changed.items()},counts=totals,allDifficultyDistributionAccepted=all(x['distributionAccepted'] for y in totals.values() for x in y.values()),requiredOpusAudioSha256={x['path']:x['encodedSha256'] for x in meta['assets'].values() if x['path'] in usedchanged})
wr(proof/'association-proof.json',output)
print(len(seen),len(usedchanged),output['allDifficultyDistributionAccepted'])
print(json.dumps(totals,indent=2))
