#!/usr/bin/env python3
"""Fail-closed local scoped amendment audit. Never writes or replaces an exam-lock."""
import argparse, copy, io, re
from pathlib import Path
import exam_lock as L
from continuous_contract import geometry
from PIL import Image
TESTS={'test-01','test-02','test-03'}
SCENE='assets/scenes/'
CHART='assets/graphics/'
JPEG=re.compile(r'(?:assets/(?:scenes|graphics)/)[a-f0-9]{12,64}\.jpg\Z')
def need(x,m):L.need(x,m)
def h(root,rel):return L.sha(L.bytes_at(root,rel))
def data(root,test):return L.read_json(L.bytes_at(root,f'data/{test}.json'))
def scope_load(path,digest):
 m=L.pinned(path,digest)
 need(set(m)=={'format','approvalRef','release','tests'} and m['format']=='shift-approved-continuous-jpg-scope-v1','invalid approval scope envelope')
 need(L.text(m['approvalRef']) and L.text(m['release']) and set(m['tests'])==TESTS,'approval, exact release and Tests01–03 required')
 for test,scope in m['tests'].items():
  need(set(scope)=={'oldLockSha256','newPackSha256','formalAssetHashes','images'},'invalid per-exam approval scope')
  need(L.is_sha(scope['oldLockSha256']) and L.is_sha(scope['newPackSha256']),'exact source and destination must be pinned')
  need(type(scope['formalAssetHashes'])==dict and scope['formalAssetHashes'] and all(L.is_sha(x) for x in scope['formalAssetHashes'].values()),'missing exact Opus byte identities')
  need(type(scope['images'])==dict,'bad JPEG scope records')
  for gid,x in scope['images'].items():
   need(set(x) in ({'oldPath','newPath','jpegSha256'},{'oldPath','newPath','jpegSha256','imageAltAfter'}),'unapproved image fields')
   need(L.is_sha(x['jpegSha256']) and JPEG.fullmatch(x['newPath']) and x['jpegSha256'].startswith(Path(x['newPath']).stem),'expected an opaque JPEG name matching its content fingerprint')
   need(L.need_path(x['oldPath']).endswith('.svg') and x['oldPath'].split('/')[1]==x['newPath'].split('/')[1],'image family must be unchanged')
   if 'imageAltAfter' in x:need(x['imageAltAfter']=='Question photograph','disallowed owner alt replacement')
 return m
def verify_jpeg(site,asset,claimed):
 data=L.bytes_at(site,asset);need(L.sha(data)==claimed and data[:2]==b'\xff\xd8' and data[-2:]==b'\xff\xd9','exact JPEG bytes or container signature differ')
 with Image.open(io.BytesIO(data)) as photo:
  need(photo.format=='JPEG' and photo.mode in {'RGB','L'} and photo.width>=360 and photo.height>=100,'JPEG must be decodable and sized for the question')
  need(not (set(photo.info)&{'comment','exif','xmp','icc_profile'}),'JPEG metadata disclosure')
  dimensions=(photo.width,photo.height);photo.load()
 return dimensions
def allowed_pack(old,new,scope,t):
 expect=copy.deepcopy(old)
 plan=expect['listeningPlan'];need('groupAudio' not in plan and 'groupAudio' in new['listeningPlan'],'only additive active groupAudio allowed')
 plan['groupAudio']=copy.deepcopy(new['listeningPlan']['groupAudio'])
 shape=geometry(plan,t)
 need({r['src'] for r in shape.values()}==set(scope['formalAssetHashes']),'Opus inventory differs from allowed paths')
 image_bind={}
 scored={g['id'] for g in expect['groups'] if g.get('image','').startswith((SCENE,CHART)) and g['image'].endswith('.svg')}
 need(scored==set(scope['images']),'scope omits or adds scored group SVG references')
 for g in expect['groups']:
  gid=g['id']
  if gid not in scored:continue
  a=scope['images'][gid];need(g['image']==a['oldPath'],'JPEG predecessor is not exact active group image')
  need((g['part']==1 and a['oldPath'].startswith(SCENE)) or (g["part"] in (3,4,7) and a['oldPath'].startswith(CHART)),'unexpected raster replacement group part')
  if 'imageAltAfter' in a:
   need(g['part']==1,'chart alt/caption change not approved')
   g['imageAlt']=a['imageAltAfter']
  g['image']=a['newPath'];image_bind[gid]=a
 need(expect==new,'unauthorized question, group, metadata, alt, chart or logical frame change')
 return shape,image_bind
def audit(oldsrc,oldsite,newsrc,newsite,baseline_policy,manifest,out,codec=True,strict_global=True,inventory_sink=None):
 need(set(baseline_policy['expectedExams'])==TESTS and set(baseline_policy['baselineLocks'])==TESTS,'prior policy must fix all three existing exam locks')
 L.check_site_scope(newsite,TESTS)
 summary={};pair={};rev={};seen_formal=set();all_formal_bytes=set()
 for test,s in sorted(manifest['tests'].items()):
  old_pin=L.check_lock(oldsrc,oldsite,test,baseline_policy,check_codec=codec)
  need(old_pin==s['oldLockSha256'],'amendment is not tied to original trusted exam lock')
  old_asset=L.read_json(L.bytes_at(oldsrc,f'{test}/exam-lock.json'))['inventory']
  if (newsrc/test/'exam-lock.json').exists():need(h(newsrc,f'{test}/exam-lock.json')==old_pin,'attempted rewrite of immutable original lock')
  need(h(newsite,f'data/{test}.json')==s['newPackSha256'],'tentative new pack outside approval')
  old,new=data(oldsite,test),data(newsite,test)
  shape,images=allowed_pack(old,new,s,test)
  inv=L.inventory(newsrc,newsite,test,check_codec=codec)
  if inventory_sink is not None:inventory_sink[test]=inv
  for u,prev in old_asset['runtimeFiles'].items():
   if u in {f'data/{test}.json',f'data/{test}.js'} or u in {r['oldPath'] for r in images.values()}:continue
   need(inv['runtimeFiles'].get(u)==prev,f'old non-image, non-pack dependency changed: {u}')
  for u,dig in s['formalAssetHashes'].items():
   need(u not in seen_formal and dig not in all_formal_bytes and inv['runtimeFiles'][u]['sha256']==dig,'formal URL/bytes alias across exams or out of scope')
   seen_formal.add(u);all_formal_bytes.add(dig)
  proofs={}
  for gid,r in images.items():
   u,v=r['oldPath'],r['newPath'];dig=r['jpegSha256']
   need(u not in pair or pair[u]==(v,dig),'inconsistent replacement of same source SVG')
   need(v not in rev or rev[v]==u,'two old SVGs alias new JPEG')
   pair[u]=(v,dig);rev[v]=u
   need(u not in inv['runtimeFiles'],'old SVG still an active scored dependency')
   predicted=old_asset['mediaSource'][u][:-len(u)]+v
   need(inv['mediaSource'][v]==predicted,'raster replacement moved unrelated source ownership')
   proofs[gid]={'oldPath':u,'newPath':v,'sha256':dig,'dimensions':verify_jpeg(newsite,v,dig),**({'imageAltAfter':r['imageAltAfter']}if 'imageAltAfter'in r else {})}
  summary[test]=dict(priorLockSha256=old_pin,newPackSha256=s['newPackSha256'],proposedInventorySha256=L.sha(L.canonical(inv)),logicalFramesUnchanged=True,questionObjectsUnchanged=True,practiceAndExistingTimelineAssetsUnchanged=True,groups=len(shape),formalDecodedSamples48k=sum(r['size'] for r in shape.values()),imageReplacements=proofs)
 if strict_global:
  need(len(seen_formal)==162 and len(pair)==25 and sum(k.startswith(SCENE)for k in pair)==13 and sum(k.startswith(CHART)for k in pair)==12,'expected exact 162 Opus and 25 approved scored JPEGs (13 scenes + 12 charts)')
  need(sum(sum(r['oldPath'].startswith(SCENE)for r in x['imageReplacements'].values())for x in summary.values())==18,'expected exact 18 scored Part 1 references')
 payload=dict(status=('scoped-amendment-audited-not-a-lock-or-publication' if codec else 'structure-only-no-codec-not-a-lock-or-publication'),physicalCodecAndGapChecks=bool(codec),strictWholeScope=bool(strict_global),approvalRef=manifest['approvalRef'],approvalScopeCanonicalSha256=L.sha(L.canonical(manifest)),baselinePolicyCanonicalSha256=L.sha(L.canonical(baseline_policy)),release=manifest['release'],exams=summary,formalUrls=len(seen_formal),uniqueScoredImages=len(pair),allReleaseGatesStillRequired=True)
 need(out.name!='exam-lock.json' and all(not out.resolve().is_relative_to(x) for x in (oldsrc,oldsite,newsrc,newsite)),'audit output must be separate and cannot be a lock')
 L.output(out,L.canonical(payload));return payload
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ('old-source','old-site','new-source','new-site','trusted-baseline-policy','scope','out'):ap.add_argument('--'+k,required=True,type=Path)
 ap.add_argument('--trusted-baseline-policy-sha256',required=True);ap.add_argument('--scope-sha256',required=True)
 a=ap.parse_args()
 audit(L.norm(a.old_source),L.norm(a.old_site),L.norm(a.new_source),L.norm(a.new_site),L.policy_load(a.trusted_baseline_policy,a.trusted_baseline_policy_sha256),scope_load(a.scope,a.scope_sha256),a.out)
