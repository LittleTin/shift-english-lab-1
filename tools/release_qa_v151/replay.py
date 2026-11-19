#!/usr/bin/env python3
"""Provisional active-only split/replay with independently audited media roles."""
import argparse, collections, hashlib, json, math, shutil
from pathlib import Path
from decimal import Decimal
import layout
from continuous_contract import geometry, role

def ck(ok, message):
    if not ok: raise ValueError(str(message))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def put(p,o):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def samples(s):
    return round(Decimal(str(s))*48000)
def path_for(t,q):return f'{t}/questions/Q{q["number"]:03}'
def run(site, report, root):
    source=root/'source'; rebuilt=root/'rebuilt'; root.mkdir(exist_ok=False,parents=True)
    report=load(report)
    layout.split(site,source,omit_legacy_questions=True)
    manifest=load(source/'manifest.json')
    physical=manifest['media']
    logical=collections.defaultdict(list)
    audience=collections.defaultdict(list)
    groups={}
    def add(url,owner,row,**meta):
        ck(url in physical,(url,meta))
        entry=dict(url=url,source=physical[url]['source'],**meta)
        logical[url].append((owner,entry))
        for qd in row: audience[qd].append(entry)
    for t in layout.EXAMS:
        p=load(site/f'data/{t}.json');qs=p['questions']
        ck(len(qs)==200 and {x['number'] for x in qs}==set(range(1,201)),t)
        ck(not ({'legacyQuestions','previousListeningPlan','alternateListeningPlans'}&p.keys()),t)
        byid={q['id']:path_for(t,q) for q in qs}
        bygroup=collections.defaultdict(list)
        for q in qs:
            qd=path_for(t,q);audience[qd]
            if q.get('groupId'):bygroup[q['groupId']].append(qd)
            for url in sorted(layout.refs(q)):add(url,qd,[qd],role='question-asset',question=q['id'])
        for g in p['groups']:
            gid=g['id'];uu=bygroup[gid]; gd=f'{t}/groups/{gid}';groups[gd]=uu
            owner=uu[0] if len(uu)==1 else gd
            for url in sorted(layout.refs(g)):
                if url==g.get('audio'):
                    a,b=g['audioStart'],g['audioEnd']
                    add(url,owner,uu,role='practice-audio',group=gid,start=a,end=b,startSample48k=samples(a),endSample48k=samples(b))
                else:add(url,owner,uu,role='group-visual',group=gid)
        for gid,entry in geometry(p['listeningPlan'],t).items():
            rr=role(entry,gid)
            url=rr.pop('url')
            add(url,f'{t}/groups/{gid}',bygroup[gid],**rr)
        for i,f in enumerate(p['listeningPlan']['frames']):
            url=f.get('src')
            if not url:continue
            r,g,q=f['role'],f.get('groupId'),f.get('questionId'); uu=bygroup[g]
            if r in {'intro','direction','example','cue','closing'}: owner=f'{t}/common'
            elif q:owner=byid[q]
            elif len(uu)==1:owner=uu[0]
            elif uu:owner=f'{t}/groups/{g}'
            else:raise ValueError((t,i,r))
            a,b=f['start'],f['end']
            add(url,owner,[byid[q]] if q in byid else uu,role=r,group=g,question=q,
                frame=i,timelineAt=f['at'],start=a,end=b,startSample48k=samples(a),endSample48k=samples(b))
        ck(abs(sum(f['duration'] for f in p['listeningPlan']['frames'])-2700)<1e-6,t)
    cases=collections.Counter()
    for url,uses in sorted(logical.items()):
        owners={owner for owner,_ in uses}
        tests={x.split('/')[0] for x in owners}
        if len(owners)==1: target=next(iter(owners))
        elif len(tests)>1:target='common'
        else:
            # A single shared group stays a group even when the same container
            # also carries one of its question-specific ranges.
            match=[gd for gd,uu in groups.items() if gd in owners and owners<={gd,*uu}]
            target=match[0] if len(match)==1 else f'{next(iter(tests))}/common'
        prev=physical[url]['source']; expected=f'{target}/media/{url}'
        if prev!=expected:
            a=source/prev;b=source/expected; b.parent.mkdir(parents=True,exist_ok=True);a.rename(b)
            physical[url]['source']=expected
            for _,entry in uses:entry['source']=expected
        scope='question' if '/questions/' in expected else 'group' if '/groups/' in expected else 'common'
        cases[scope]+=1
        physical[url]['ownership']=scope
        physical[url]['uses']=[dict(owner=own,role=x['role'],**{k:x[k] for k in ('question','group','frame') if x.get(k) is not None}) for own,x in uses]
        ck(sha(source/expected)==physical[url]['sha256'],url)
    # Replace legacy sidecar schema with same top-level files plus explicit roles.
    # Also write a sidecar for every question and group even if there is no media.
    for qd,uses in sorted(audience.items()):
        urls=sorted({x['url'] for x in uses})
        question=load(source/qd/'question.json')
        gd=f"{question['testId']}/groups/{question['groupId']}/group.json" if question.get('groupId') else None
        if gd: ck((source/gd).is_file(),gd)
        put(source/qd/'media.json',dict(question=question['id'],groupSource=gd,files=[dict(url=u,source=physical[u]['source']) for u in urls],roles=uses))
    for gd,uu in sorted(groups.items()):
        urls=sorted({u for u,uses in logical.items() if any(o==gd or (x.get('group')==gd.rsplit('/',1)[1] and x['role'] in {'group-visual','practice-audio','formal-group-audio'}) for o,x in uses)})
        put(source/gd/'media.json',dict(files=[dict(url=u,source=physical[u]['source']) for u in urls]))
    for d in [source/'common',*(source/t/'common' for t in layout.EXAMS)]:
        rel=d.relative_to(source).as_posix();urls=sorted(u for u,v in physical.items() if str(v['source']).startswith(rel+'/media/'))
        put(d/'media.json',dict(files=[dict(url=u,**physical[u]) for u in urls]))
    encoded={v['path']:v for v in report['assets'].values()}
    sample_urls=[report['mapping'][u] for u in report['samples']]
    ck(set(encoded)-set(physical)==set(sample_urls) and len(sample_urls)==14,'standalone accent audio closure')
    standalone={}
    for u in [*sample_urls,'assets/scenes/formal-example.svg']:
        a=site/u;b=source/'common'/'standalone'/u
        b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
        item=dict(source=b.relative_to(source).as_posix(),sha256=sha(b),bytes=b.stat().st_size,role='accent-preview' if u in encoded else 'formal-example-visual')
        if u in encoded:item.update(startSample48k=0,endSample48k=encoded[u]['decodedSamples'])
        standalone[u]=item
    for u,v in encoded.items():
        ck(sha(site/u)==v['encodedSha256'],u)
    manifest['standalone']=standalone
    put(source/'manifest.json',manifest)
    layout.build(source,rebuilt,omit_legacy_questions=True)
    for u,v in standalone.items():
        dest=rebuilt/u;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/v['source'],dest)
    verified={}
    for t in layout.EXAMS:
        for suffix in ('json','js'):
            u=f'data/{t}.{suffix}';ck(sha(rebuilt/u)==sha(site/u),u);verified[u]=sha(site/u)
    for u in {*physical,*standalone}:ck(sha(rebuilt/u)==sha(site/u),u)
    ck(len({v['sha256'] for v in [*physical.values(),*standalone.values()]})==len(physical)+len(standalone),'duplicate physical media')
    ck(not any(p.name=='archive' or p.suffix.lower() in {'.wav','.mp3'} for p in source.rglob('*')),'raw or archive leaked')
    put(root/'proof.json',dict(status='provisional-scoped-not-final-locked-release',questions=len(audience),groups=len(groups),packMedia=len(physical),standaloneMedia=len(standalone),physicalOwnership=dict(cases),matchedPackSha256=verified,manifestSha256=sha(source/'manifest.json')))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--site',type=Path,required=True);p.add_argument('--asset-report',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.site,a.asset_report,a.out)
