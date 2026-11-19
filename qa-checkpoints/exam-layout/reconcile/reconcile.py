#!/usr/bin/env python3
"""Fail-closed materialization of independently reviewed SHIFT evidence.

This gate attests evidence reconciliation, not website or deployment readiness.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import wave

EXAMS = ('test-01', 'test-02', 'test-03')
COUNTS = {1:6,2:25,3:39,4:30,5:30,6:16,7:54}
PASS='verified-item-not-published'
ID=re.compile(r'[a-zA-Z0-9_-]{1,110}\Z')
PATH_TOKEN=re.compile(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z')
IS_SHA=re.compile('[a-f0-9]{64}\\Z')
MEDIA_FIELDS={'audio','image','archivedImage','src'}

def strict(p):
    def pairs(seq):
        out={}
        for k,v in seq:
            if k in out: raise ValueError(f'duplicate JSON key {k!r}')
            out[k]=v
        return out
    def invalid(s):
        raise ValueError(f'Nonfinite JSON value: {s}')
    return json.loads(p.read_text('utf-8'),object_pairs_hook=pairs,parse_constant=invalid)

def dig(j):
    return sha256(json.dumps(j,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def file_sha(p):
    with p.open('rb') as f:
        return __import__('hashlib').file_digest(f,'sha256').hexdigest()

def rel(root,s,kind=None):
    if not isinstance(s,str):raise ValueError(f'not a path: {s!r}')
    p=s.split('/')
    if p[0] not in ({kind} if kind else {'assets','audio'}) or len(p)<2 or not all(PATH_TOKEN.fullmatch(t) for t in p):
        raise ValueError(f'unsafe media path {s!r}')
    ans=root
    for part in p:
        ans/=part
        if ans.is_symlink():raise ValueError(f'symlink path {ans}')
    if not ans.is_file():raise ValueError(f'absent media path {s!r}')
    return ans

def assets(j):
    if isinstance(j,dict):
        for k,v in j.items():
            if k in MEDIA_FIELDS and isinstance(v,str):yield v
            else:yield from assets(v)
    elif isinstance(j,list):
        for x in j:yield from assets(x)

def d(v):
    if isinstance(v,bool):raise ValueError('Boolean range')
    try:
        x=Decimal(str(v))
        if not x.is_finite(): raise ValueError('Nonfinite range')
        return x
    except InvalidOperation:raise ValueError(f'bad numeric range: {v!r}') from None

def isequal(a,b):
    # Prior ledgers rounded paths to microseconds; use sub-sample tolerance.
    return abs(d(a)-d(b))<=Decimal('0.000010')

def evidence_range(row):
    if 'start' in row or 'end' in row:
        if 'from' in row or 'to' in row:raise ValueError('ambiguous interval schema')
        start,end=row.get('start'),row.get('end')
    else:start,end=row.get('from'),row.get('to')
    if not 0<=d(start)<d(end):raise ValueError('bad interval')
    return start,end

def same_window(a,b):
    return a[0]==b[0] and isequal(a[1],b[1]) and isequal(a[2],b[2])

def pair_number(q,test,n,base):
    if not isinstance(q,dict) or q.get('testId')!=test or type(q.get('number')) is not int or q['number']!=n or not ID.fullmatch(q.get('id','')):
        raise ValueError('item ID/test/number mismatch')
    if q.get('part')!=base.get('part') or q.get('groupId')!=base.get('groupId'):
        raise ValueError('item differs in baseline section or group; explicit layout change required')
    options=q.get('options')
    letters='ABC' if q['part']==2 else 'ABCD'
    if not isinstance(options,list) or any(not isinstance(o,dict) for o in options) or [o.get('id') for o in options]!=list(letters) or q.get('answer') not in letters:
        raise ValueError('invalid options or key')
    for k in ('prompt','promptZh','explanationZh'):
        if not isinstance(q.get(k),str) or not q[k].strip():raise ValueError(f'missing {k}')
    for o in options:
        for k in ('text','zh','whyZh'):
            if not isinstance(o.get(k),str) or not o[k].strip():raise ValueError(f'missing choice {k}')
    if not q.get('evidence'):raise ValueError('missing source evidence')
    return q

def want_audio(pack, q, group, has_cue=False):
    base=next(x for x in pack['questions'] if x['number']==q['number'])
    frames=[f for f in pack['listeningPlan']['frames'] if f.get('groupId')==group['id'] and f.get('kind')=='audio']
    req={}
    for role in (('cue','passage','question') if has_cue else ('passage','question')):
        if role=='question' and q['part']<3:continue
        hits=[f for f in frames if f.get('role')==role and (role!='question' or f.get('questionId') in (q['id'],base['id']))]
        if len(hits)!=1:raise ValueError(f'need one formal {role} for this item (got {len(hits)})')
        req[role]=(hits[0]['src'],hits[0]['start'],hits[0]['end'])
    req['practice']=(group['audio'],group['audioStart'],group['audioEnd'])
    return req

def check_audio(rec, required, verify):
    rows=rec.get('audio')
    if not isinstance(rows,list) or len(rows)!=len(required):raise ValueError('wrong number of reviewed audio evidence intervals')
    verified={}
    for row in rows:
        if not isinstance(row,dict):raise ValueError('invalid audio row')
        lo,hi=evidence_range(row)
        window=(row.get('path'),lo,hi)
        mode=row.get('mode')
        candidates=[k for k,w in required.items() if same_window(window,w) and (mode is None or mode==k) and k not in verified]
        if len(candidates)!=1:raise ValueError(f'audio role/range does not uniquely match formal/practice timeline: {mode} {window}')
        mode=candidates[0]
        expected=row.get('assetSha256')
        if not isinstance(expected,str) or not IS_SHA.fullmatch(expected) or verify(window[0],'audio')!=expected:
            raise ValueError(f'{mode} source hash mismatch: {window[0]}')
        verified[mode]={'path':window[0],'start':str(lo),'end':str(hi),'sha256':expected}
    return verified

def run(site, ledger, decisions):
    if not isinstance(decisions,dict):raise ValueError('Group decisions object required')
    reports={}
    packs={}
    hashcache={}
    cross={}
    used_decisions=set()
    def verify(s,kind=None):
        v=rel(site,s,kind)
        if s not in hashcache:hashcache[s]=file_sha(v)
        return hashcache[s]
    for test in EXAMS:
        pack=strict(site/'data'/f'{test}.json')
        report={'missing':[],'holds':[],'issues':[],'accepted':[],'groups':{},'verifiedMedia':{},'verifiedItems':{}}
        reports[test]=report
        errors=report['issues']
        if pack.get('testId')!=test:raise ValueError(f'bad input pack ID {test}')
        if Counter(q['part'] for q in pack['questions'])!=COUNTS or sorted(q['number'] for q in pack['questions'])!=list(range(1,201)):
            raise ValueError(f'{test} baseline does not have correct active numbering or section sizes')
        old={q['number']:q for q in pack['questions']}
        groups={g['id']:g for g in pack['groups']}
        if len(groups)!=len(pack['groups']):raise ValueError(f'duplicate base groups {test}')
        checked={}
        group_sources=defaultdict(lambda:defaultdict(dict))
        tdir=ledger/test
        if tdir.is_symlink():raise ValueError('symlink ledger')
        for p in sorted(tdir.glob('*.json')):
            if not re.fullmatch(r'Q[0-9]{3}\.json',p.name) or not 1<=int(p.stem[1:])<=200:
                errors.append(f'Unexpected evidence name {p.name}')
        for n,b in old.items():
            p=tdir/f'Q{n:03}.json'
            if p.is_symlink():
                errors.append(f'Q{n:03}: symlink evidence');continue
            if not p.is_file():
                report['missing'].append(n);continue
            try:
                rec=strict(p)
                if rec.get('status')!=PASS:
                    report['holds'].append(n);continue
                q=pair_number(rec.get('activeQuestion'),test,n,b)
                if not rec.get('checks'):raise ValueError('no positive QA decision evidence')
                if rec.get('scope')!=('listening' if q['part']<=4 else 'reading'):
                    raise ValueError('section/scope mismatch')
                prior=rec.get('originalQuestion')
                if q['id']==b['id'] and q['answer']!=b['answer']:
                    raise ValueError('answer key changed under the same active ID')
                if q['id']!=b['id']:
                    if not isinstance(prior,dict) or (prior.get('id'),prior.get('testId'),prior.get('number'),prior.get('part'))!=(b['id'],test,n,b['part']):
                        raise ValueError('changed ID has no matching prior identity')
                    if (q.get('revision') or 0)<=(b.get('revision') or 0):
                        raise ValueError('changed ID did not increase revision')
                gid=q.get('groupId')
                gr=rec.get('group')
                if gid:
                    if not isinstance(gr,dict) or gid not in groups or (gr.get('id'),gr.get('testId'),gr.get('part'))!=(gid,test,q['part']):
                        raise ValueError('group snapshot missing or not the reviewed group')
                    group_sources[gid][dig(gr)][n]=gr
                elif gr:raise ValueError('solo evidence must not supply group snapshot')
                elif q['part']!=5:raise ValueError('non-Part5 item missing group')
                if q['id'] in cross:
                    raise ValueError(f"duplicate authoritative ID, also at {cross[q['id']]}")
                if q['id'] in {x['id'] for x in pack.get('legacyQuestions',[])}:
                    raise ValueError('active ID matches archive-only identity')
                cross[q['id']]=f'{test}/Q{n:03}'
                checked[n]=(q,rec)
            except (ValueError,TypeError,KeyError,AttributeError) as exc:
                errors.append(f'Q{n:03}: {exc}')
        selected={}
        for gid,map_ in group_sources.items():
            variants={k: sorted(v) for k,v in map_.items()}
            report['groups'][gid]=variants
            if len(map_)==1:
                key=next(iter(map_))
            else:
                decision=decisions.get(test+'/'+gid)
                key=(decision or {}).get('canonicalSha256')
                affected=sorted(n for k,qs in map_.items() if k!=key for n in qs)
                if (not isinstance(decision,dict) or key not in map_ or
                    sorted(decision.get('seenSha256',[]))!=sorted(map_) or
                    sorted(decision.get('reverifiedQuestionNumbers',[]))!=affected or
                    not isinstance(decision.get('reason'),str) or not decision['reason'].strip()):
                    errors.append(f'{gid}: conflicting reviewed group snapshots; exact explicit re-verification required')
                    continue
                used_decisions.add(test+'/'+gid)
            selected[gid]=next(iter(map_[key].values()))
        clean=[]
        for n,(q,rec) in sorted(checked.items()):
            gid=q.get('groupId')
            if gid and gid not in selected:continue
            g=selected.get(gid)
            media={}
            try:
                if g and g.get('image'):
                    want=rec.get('imageSha256')
                    got=verify(g['image'],'assets')
                    if not isinstance(want,str) or not IS_SHA.fullmatch(want) or got!=want:
                        raise ValueError('reviewed picture hash does not match candidate path')
                    media['image']={'path':g['image'],'sha256':got}
                if q['part']<=4:
                    rows=rec.get('audio')
                    has_cue=isinstance(rows,list) and any(isinstance(row,dict) and row.get('mode')=='cue' for row in rows)
                    media['audio']=check_audio(rec,want_audio(pack,q,g,has_cue=has_cue),verify)
                if media:report['verifiedMedia'][str(n)]=media
                report['verifiedItems'][str(n)]={'id':q['id'],'questionSha256':dig(q),'evidenceSha256':dig(rec),'groupSha256':dig(g) if g else None}
                report['accepted'].append(n)
                clean.append(q)
            except (ValueError,TypeError,KeyError,AttributeError) as exc:
                errors.append(f'Q{n:03}: {exc}')
        if len(clean)!=200 or any(report[k] for k in ('missing','holds','issues')):continue
        pack=deepcopy(pack)
        pack.pop('legacyQuestions',None)
        old_id={n:q['id'] for n,q in old.items()}
        remap={old_id[q['number']]:q['id'] for q in clean}
        pack['questions']=clean
        pack['groups']=[selected[g['id']] for g in pack['groups']]
        # Change active frame metadata *only* as required for the authoritative
        # same-number ID; old fallback/resume snapshots are not modified.
        for f in pack['listeningPlan']['frames']:
            if f.get('questionId') in remap:
                f['questionId']=remap[f['questionId']]
        for path in set(assets(pack)):
            try:verify(path)
            except ValueError as exc:errors.append(f'candidate asset: {exc}')
        if not errors:packs[test]=pack
    unused=sorted(set(decisions)-used_decisions)
    return dict(exams=reports,evidenceComplete=len(packs)==3 and not unused,unusedDecisions=unused,mediaSha256=hashcache),packs

def freeze_json(p,j):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(j,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def build(site, out, packs, layout_script, validator):
    if out.exists() or out.is_symlink() or out.resolve().is_relative_to(site.resolve()):
        raise ValueError('Output must be new and outside candidate site')
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.parent.resolve()!=out.parent.absolute():raise ValueError('Symlink parent is not allowed')
    with tempfile.TemporaryDirectory(prefix='.reconcile-',dir=out.parent) as tmp:
        stage=Path(tmp)/'output'
        assembled=stage/'assembled-candidate'
        for test,p in packs.items():
            q=assembled/'data'/f'{test}.json'
            freeze_json(q,p)
            body=json.dumps(p,ensure_ascii=False,allow_nan=False,separators=(',',':'))
            body=body.replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
            q.with_suffix('.js').write_text('window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('+body+');\n',encoding='utf-8')
        for ref in set(ref for p in packs.values() for ref in assets(p)):
            src=rel(site,ref)
            dest=assembled/ref
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dest)
            if file_sha(src)!=file_sha(dest):raise ValueError(f'Candidate asset copy changed: {ref}')
        subprocess.run([sys.executable,str(validator),'--site',str(assembled)],check=True,stdout=sys.stderr)
        # Explicitly stage independently editable source instead of treating
        # copied single-file packs or evidence JSON as canonical authoring.
        subprocess.run([sys.executable,str(layout_script),'split','--site',str(assembled),
                        '--source',str(stage/'authoring'),'--omit-legacy-questions'],check=True,stdout=sys.stderr)
        stage.rename(out)

def audit_migrated(site, canonical, overlay):
    """Cross-check the migrated overlay against canonical packs, not its own manifest alone."""
    out=strict(overlay/'data'/f'{canonical["testId"]}.json')
    proof=strict(overlay/'migration-report.json')
    no=lambda row,exclude:{k:v for k,v in row.items() if k not in exclude}
    def require(ok,message):
        if not ok:raise ValueError(message)
    test=canonical['testId']
    require(proof.get('testId')==test,'media proof test mismatch')
    require(no(canonical,{'groups','listeningPlan'})==no(out,{'groups','listeningPlan'}),'metadata, question, or retained-plan drift during moving')
    require(no(canonical['listeningPlan'],{'frames'})==no(out['listeningPlan'],{'frames'}),'active listening plan metadata drift')
    require(len(canonical['groups'])==len(out['groups']),'group count drift')
    require(len(canonical['listeningPlan']['frames'])==len(out['listeningPlan']['frames']),'frame count drift')
    by_path={x['target']:x for x in proof['verifiedPcmClips']}
    require(len(by_path)==len(proof['verifiedPcmClips']),'duplicate relocated audio proof targets')
    used=set()
    ff_cache={}
    def clip(old,lo,hi,new,newlo,newhi):
        require(new in by_path and new.startswith('audio/exams/'+test+'/'),'untracked relocated audio '+new)
        row=by_path[new]
        require(same_window((row['source'],row['sourceStart'],row['sourceEnd']),(old,lo,hi)) and
                isequal(newlo,0) and isequal(newhi,d(hi)-d(lo)),'location/range proof mismatch: '+new)
        if old not in ff_cache:
            source=rel(site,old,'audio')
            streams=subprocess.check_output(['ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=sample_rate,channels','-of','json',str(source)])
            native=json.loads(streams)['streams'][0]
            pcm=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(source),'-map','0:a:0','-f','s16le','-acodec','pcm_s16le','-'])
            ff_cache[old]=(file_sha(source),int(native['sample_rate']),int(native['channels']),pcm)
        digest,rate,channels,pcm=ff_cache[old]
        require(row['sourceSha256']==digest and row['sampleRate']==rate and row['channels']==channels,'source-audio proof hash/layout mismatch: '+new)
        first,last=(round(d(x)*rate) for x in (lo,hi))
        require((row['sampleStart'],row['sampleEnd'])==(first,last),'invalid sample boundaries in proof: '+new)
        stride=2*channels
        require(0<=first<last<=len(pcm)//stride,'source sample window outside file: '+new)
        part=pcm[first*stride:last*stride]
        with wave.open(str(rel(overlay,new,'audio')),'rb') as wav:
            require((wav.getframerate(),wav.getnchannels(),wav.getsampwidth(),wav.getnframes())==(rate,channels,2,last-first),'invalid staged WAV PCM layout: '+new)
            samples=wav.readframes(wav.getnframes())
        require(samples==part and sha256(part).hexdigest()==row['pcmSha256'],'relocated PCM differs from verified source: '+new)
        used.add(new)
    for before,after in zip(canonical['groups'],out['groups']):
        require(no(before,{'audio','audioStart','audioEnd','image'})==no(after,{'audio','audioStart','audioEnd','image'}),'group changed content/order')
        if before.get('audio'):
            clip(before['audio'],before['audioStart'],before['audioEnd'],after['audio'],after['audioStart'],after['audioEnd'])
        else:require(not after.get('audio'),'unreviewed new group audio')
        if before.get('image'):
            require(after['image'].startswith('assets/exams/'+test+'/'),'unexpected relocated picture path')
            require(file_sha(rel(site,before['image'],'assets'))==file_sha(rel(overlay,after['image'],'assets')),'relocated picture changed data')
        else:require(not after.get('image'),'unreviewed new picture')
    for before,after in zip(canonical['listeningPlan']['frames'],out['listeningPlan']['frames']):
        fields={'src','start','end'} if before['kind']=='audio' else set()
        require(no(before,fields)==no(after,fields),'formal timeline/frame/order changed')
        if fields:clip(before['src'],before['start'],before['end'],after['src'],after['start'],after['end'])
    require(used==set(by_path),'extra/unreferenced relocated audio proof')
    # Fallback audio still deliberately uses original relative URLs.
    for key in ('previousListeningPlan','alternateListeningPlans'):
        for ref in set(assets(canonical.get(key))):
            require(file_sha(rel(site,ref))==file_sha(rel(overlay,ref)),f'legacy playback asset changed: {ref}')
    return {'verifiedAudioPaths':len(used)}

def main():
    x=argparse.ArgumentParser(description=__doc__)
    x.add_argument('--site',type=Path,required=True)
    x.add_argument('--ledger',type=Path,required=True)
    x.add_argument('--decisions',type=Path)
    x.add_argument('--difficulty-ledger',type=Path,help='Verified content-bound §1.1 reviews; required for final candidate output')
    x.add_argument('--out',type=Path)
    x.add_argument('--layout-script',type=Path)
    x.add_argument('--validator',type=Path)
    x.add_argument('--overlays',type=Path,help='Parent containing test-01, test-02, test-03 migrated proofs')
    x.add_argument('--report',type=Path)
    ns=x.parse_args()
    site=ns.site.resolve(); report,packs=run(site,ns.ledger,strict(ns.decisions) if ns.decisions else {})
    report['releaseReady']=False
    difficulty_complete=False
    if ns.difficulty_ledger:
        sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'difficulty'))
        from difficulty_gate import report as difficulty_report, apply_accepted as apply_difficulty
        level_report,_=difficulty_report(ns.ledger,ns.difficulty_ledger)
        report['difficultyReview']=level_report
        difficulty_complete=level_report['difficultyGateComplete']
        if difficulty_complete and report['evidenceComplete']:
            packs,_=apply_difficulty(packs,ns.ledger,ns.difficulty_ledger)
    elif ns.out:
        x.error('--out requires --difficulty-ledger; labels are a release gate')
    report['stillRequired']=['final answer-key QA on candidate revisions','§1.1 exact difficulty audit and genuine distribution','browser playback, storage and retirement acceptance','actual release size/deploy check']
    if ns.overlays and report['evidenceComplete'] and (not ns.difficulty_ledger or difficulty_complete):
        report['postMove']={}
        for exam,p in packs.items():
            try:report['postMove'][exam]=audit_migrated(site,p,ns.overlays/exam)
            except (ValueError,KeyError,TypeError,OSError,subprocess.CalledProcessError) as exc:
                report['postMove'][exam]={'error':str(exc)}
        report['postMoveComplete']=all('error' not in v for v in report['postMove'].values())
    if ns.report:
        if ns.report.exists() or ns.report.is_symlink():raise ValueError('Report file must be new')
        freeze_json(ns.report,report)
    summary={'evidenceComplete':report['evidenceComplete'],'releaseReady':False,'exams':{
        k:{name:len(v[name]) for name in ('missing','holds','issues','accepted')} for k,v in report['exams'].items()}}
    if ns.difficulty_ledger:
        summary['difficultyReviewed']=report['difficultyReview']['reviewed']
        summary['difficultyGateComplete']=difficulty_complete
    print(json.dumps(summary,indent=2))
    good=report['evidenceComplete'] and (not ns.overlays or report.get('postMoveComplete'))
    if ns.difficulty_ledger:good=good and difficulty_complete
    if ns.out and good:
        if not ns.layout_script or not ns.validator:x.error('--out requires --layout-script and --validator')
        build(site,ns.out,packs,ns.layout_script.resolve(),ns.validator.resolve())
    return 0 if good else 2

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,TypeError,KeyError,OSError,subprocess.CalledProcessError) as exc:
        print(f'Reconciliation stopped: {exc}',file=sys.stderr);sys.exit(1)
