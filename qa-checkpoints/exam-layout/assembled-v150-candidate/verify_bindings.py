#!/usr/bin/env python3
"""Audit all active exact item/difficulty/media binding for a private candidate."""
from pathlib import Path
import argparse,hashlib,json,sys,copy
from collections import Counter
P=argparse.ArgumentParser()
for k in ('stage','base-ledger','fresh-index','tools','out'):P.add_argument('--'+k,type=Path,required=True)
P.add_argument('--held-clone',action='store_true',help='only T01/T03; record that T02 is not qualified')
a=P.parse_args()
assert not a.out.exists()
sys.path[:0]=[str(a.tools/'reconcile'),str(a.tools/'difficulty')]
from reconcile import check_audio,want_audio,check_item_vocabulary
from difficulty_gate import check as check_review,summarize
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rd(p):return json.loads(p.read_bytes())
def dg(o):return hashlib.sha256(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
r=rd(a.stage/'asset-report.json');s=a.stage/'site'; fresh=rd(a.fresh_index)
source_by_raw={p:(h,x) for h,x in r['assets'].items() for p in x.get('sourcePaths',[])}
source_by_delivered={x['path']:x for x in r['assets'].values()}
def bind(rel,expected_sha=None):
 x=source_by_delivered.get(rel)
 if x:
  if expected_sha:assert expected_sha==x['encodedSha256'],rel
  return rel
 h,x=source_by_raw[rel];assert r['mapping'][rel]==x['path'],rel
 if expected_sha:assert expected_sha==h,(rel,expected_sha,h)
 return x['path']
def media_sha(rel,kind=None):
 x=source_by_delivered.get(rel)
 if x:assert sha(s/rel)==x['encodedSha256'],rel
 return sha(s/rel)
def check_level(raw,active):
 v={k:x for k,x in raw.items() if k!='difficulty'}
 assert v=={k:x for k,x in active.items() if k!='difficulty'}
out=dict(status='offline-content-difficulty-media-bindings-not-a-release-or-lock',exams={},packRevisions={},frozenReceiptSha256=sha(a.stage/'asset-report.json'),releaseReady=False)
for t in ('test-01','test-02','test-03'):
 if a.held_clone and t=='test-02':
  out['exams'][t]=dict(status='held-no-approved-T02-final-role-proof');continue
 p=rd(s/'data'/f'{t}.json');qs=p['questions'];gs={g['id']:g for g in p['groups']}; inv=Counter(); role=L={}
 existing=fresh[t]; exp={'test-01':18,'test-02':24,'test-03':9};assert len(existing)==exp[t]
 levels={}; proof=[]
 for i,q in enumerate(qs,1):
  assert q['number']==i
  paths={}
  for g in ('verified-items','difficulty'):
   if str(i) in existing:
    z=existing[str(i)][g];path=Path(z['path']);assert sha(path)==z['sha256']
   else:path=a.base_ledger/f'{g}/{t}/Q{i:03}.json'
   paths[g]=path
  vr=rd(paths['verified-items']);dr=rd(paths['difficulty']);qr=vr['activeQuestion'];gr=vr.get('group');go=gs.get(q.get('groupId'))
  assert vr['status']=='verified-item-not-published' and qr['testId']==t and qr['number']==i
  check_level(qr,q);check_item_vocabulary(q)
  if gr:
   z=copy.deepcopy(gr)
   if u:=z.get('audio'):z['audio']=bind(u)
   assert z==go,(t,i,'group')
  else:assert go is None
  level=check_review(dr,t,qr,gr);levels[i]=level;assert level==q['difficulty'],(t,i,'display label')
  audio=[]
  if q['part']<=4:
   rr=copy.deepcopy(vr);rr['group']=go;rr['activeQuestion']=q
   for row in rr['audio']:
    delivery=bind(row['path'],row['assetSha256']);row.update(path=delivery,assetSha256=media_sha(delivery))
   modes=want_audio(p,q,go,has_cue=any(row.get('mode')=='cue' for row in rr['audio']))
   done=check_audio(rr,modes,media_sha);inv.update(done.keys());audio=sorted(done.items())
  if go and go.get('image'):assert media_sha(go['image'])==vr['imageSha256']
  proof.append([i,q['id'],q['revision'],sha(paths['verified-items']),sha(paths['difficulty']),dg(q),dg(go),dg(audio),level])
 sections={}
 for name,lo,hi in [('listening',1,100),('reading',101,200)]:
  units={};parts={}
  for q in qs[lo-1:hi]:
   k=q.get('groupId') or q['id'];units.setdefault(k,[]).append(q['number']);parts[k]=q['part']
  units={k:v for k,v in units.items() if parts[k] not in (3,4,6) or len(v)=={3:3,4:3,6:4}[parts[k]]}
  v=summarize(units,{i:levels[i] for i in range(lo,hi+1)});num=v['reviewedCounts'];n=v['completePracticeQuestionCounts']
  assert num['intermediate']>max(num['foundation'],num['advanced']) and min(num['foundation'],num['advanced'],n['foundation'],n['advanced'])>=3
  sections[name]=v
 out['exams'][t]=dict(status='exact-offline-passed',reviewed=200,replaced=len(existing),displayLabelsVerified=True,sections=sections,audioModeCounts=dict(inv),perItemProof=proof)
 out['packRevisions'][t]=dict(packSha256=sha(s/'data'/f'{t}.json'),canonicalPlanSha256=dg(p['listeningPlan']))
out['offlineScopeCount']=sum(v.get('reviewed',0) for v in out['exams'].values())
a.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(out['offlineScopeCount'],{t:v['status'] for t,v in out['exams'].items()})
