#!/usr/bin/env python3
"""Validate bundled exam structure, JS parity and the listening timeline."""
from collections import Counter,defaultdict
from pathlib import Path
import argparse,json,math,re,subprocess
from add_pack import validate_pack, PACK_WRAPPER, parse_json
from release_qa_v151.group_layout import (require_contiguous_groups, require_part7_layout,
                                          uses_source_document_count)

COUNTS={1:6,2:25,3:39,4:30,5:30,6:16,7:54}

def check(condition, message):
    if not condition:
        raise ValueError(message)

def load_json(path):
    return parse_json(path.read_text(encoding='utf-8'),str(path))

def duration_for(root, ref, durations):
    if ref not in durations:
        path=(root/ref).resolve()
        check(path.is_relative_to(root/'audio') and path.is_file(),f'Missing or unsafe audio: {ref}')
        d=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)],text=True))
        check(d>0 and math.isfinite(d),f'Invalid audio: {ref}')
        durations[ref]=d
    return durations[ref]

def source_document_count(authoring, test_id, group):
    gid=group['id']
    path=authoring/test_id/'groups'/gid/'group.json'
    check(path.is_file(),f'{gid}: missing Part 7 authoring record: {path}')
    source=load_json(path)
    check(isinstance(source,dict) and all(source.get(key)==group[key]
          for key in ('id','testId','part','passage','passageZh')),
          f'{gid}: Part 7 authoring record differs from candidate')
    count=source.get('documentCount')
    check('documentCount' not in group or (type(group['documentCount']) is int
          and group['documentCount']==count),
          f'{gid}: candidate documentCount differs from authoring record')
    return count


def validate_group_layout(pack, filename, authoring):
    def layout_check(condition, message):
        check(condition, f'{filename}: {message}')

    by=require_contiguous_groups(pack['questions'],layout_check)
    test_id=pack['testId']
    if uses_source_document_count(test_id):
        require_part7_layout(pack['groups'],by,
                             lambda row: source_document_count(authoring,test_id,row),layout_check)
    else:
        # Preserve the existing historical format check without new metadata.
        passages=Counter()
        for row in pack['groups']:
            if row['part']!=7:
                continue
            gid=row['id']
            n=max(1,len(re.findall(r'(?m)^DOCUMENT [1-3]\b',row['passage'])))
            check(n in (1,2,3),f'{gid}: wrong passage count')
            passages[n]+=len(by[gid])
            if n>1:
                check(len(by[gid])==5,f'{gid}: each multiple passage group has 5 questions')
        layout_check(passages=={1:29,2:10,3:15},f'wrong single/double/triple: {passages}')
    return by


def exam(root,filename,durations,allow_no_plan,authoring=None):
    p=load_json(filename)
    match=PACK_WRAPPER.fullmatch(filename.with_suffix('.js').read_text(encoding='utf-8'))
    check(match is not None and json.loads(match[1])==p,f'{filename.name}: JSON and JS differ')
    ids=validate_pack(p,root)
    g={x['id']:x for x in p['groups']}
    q=sorted(p['questions'],key=lambda x:x['number'])
    check(Counter(x['part'] for x in q)==COUNTS,f'{filename.name}: wrong Part counts')
    check([x['number'] for x in q]==list(range(1,201)),f'{filename.name}: non-contiguous numbering')
    check([x['part'] for x in q]==sorted(x['part'] for x in q),f'{filename.name}: questions out of section order')
    by=validate_group_layout(p,filename.name,authoring or root/'authoring')
    for part,cnt,length in [(1,6,1),(2,25,1),(3,13,3),(4,10,3),(6,4,4)]:
        rows=[(gid,x) for gid,x in g.items() if x['part']==part]
        check(len(rows)==cnt and all(len(by[gid])==length for gid,_ in rows),f'{filename.name}: wrong group sizing in Part {part}')
    check(not any(x.get('groupId') for x in q if x['part']==5),f'{filename.name}: Part 5 must be independent')
    archived=p.get('legacyQuestions',[])
    active={x['number']:x for x in q}
    for x in archived:
        other=active[x['number']]
        check(x['id'] not in ids and x['groupId']==other['groupId'] and x['part']==other['part'],f'{x["id"]}: invalid compatibility question')
        ids.add(x['id'])
    for gid,grp in g.items():
        if grp['part']>4:continue
        end=grp.get('audioEnd'); start=grp.get('audioStart')
        if end is not None or start is not None:
            d=duration_for(root,grp['audio'],durations)
            check(0<=start<end<=d+.12 and abs(end-start-grp['duration'])<.04,f'{gid}: invalid practice audio range')
    plan=p.get('listeningPlan')
    if not plan and allow_no_plan:return ids
    check(bool(plan and plan.get('frames')),f'{filename.name}: missing formal audio plan')
    order=[]; lengths=0
    frames_by_group=defaultdict(list)
    for frame in plan['frames']:
        gid=frame['groupId']
        check(gid in g and frame.get('part')==g[gid]['part']<5,f'{gid}: bad audio frame ownership')
        if not order or gid!=order[-1]:order.append(gid)
        frames_by_group[gid].append(frame)
        check(abs(frame['at']-lengths)<.02,f'{gid}: inconsistent timeline position')
        d=frame['duration']
        check(isinstance(d,(int,float)) and 0<d<180,f'{gid}: invalid frame duration {d}')
        lengths+=d
        if frame.get('src'):
            actual=duration_for(root,frame['src'],durations)
            start=frame.get('start',0); end=frame.get('end',start+d)
            check(0<=start<end<=actual+.15 and abs(end-start-d)<.15,f'{gid}: invalid source range {frame}')
    expected=list(dict.fromkeys(x['groupId'] for x in q if x['part']<5))
    check(order==expected,f'{filename.name}: wrong group playback order')
    direction_parts=[]
    for gid in order:
        f=frames_by_group[gid]
        roles=Counter(x['role'] for x in f)
        nums=[x['id'] for x in by[gid]]
        check(roles.get('passage')==1 and roles.get('answer')==len(nums),f'{gid}: passage/answer window mismatch')
        check([x.get('questionId') for x in f if x['role']=='answer']==nums,f'{gid}: answer window wrong questions')
        if g[gid]['part']>=3:
            check([x.get('questionId') for x in f if x['role'] in ('question','question-cue') or (x['role']=='cue' and x.get('questionId'))]==nums,f'{gid}: missing or misplaced spoken stems')
        if 'direction' in roles:
            check(roles['direction']==1 and next((t for t in f if t['role']!='intro'),{}).get('role')=='direction',f'{gid}: bad part direction')
            direction_parts.append(g[gid]['part'])
    check(direction_parts==[1,2,3,4],f'{filename.name}: incorrect section directions')
    check(abs(lengths-2700)<.25,f'{filename.name}: formal listening is {lengths:.3f}s (expected 2700)')
    print(f'{p["testId"]}: 200 questions; {len(order)} listening groups; {len(plan["frames"])} frames; {lengths:.3f}s; {len(archived)} archived IDs retained.')
    return ids

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--site',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--authoring',type=Path,
                        help='source root for Part 7 group documentCount for Test 10+ (default: SITE/authoring)')
    parser.add_argument('--no-plan',action='store_true',help='allow missing formal manifests during authoring')
    parser.add_argument('packs',nargs='*')
    a=parser.parse_args()
    root=a.site.resolve(); d={}
    seen=set()
    for p in ([(root/'data'/name) for name in a.packs] if a.packs else sorted((root/'data').glob('test-*.json'))):
        ids=exam(root,p,d,a.no_plan,a.authoring)
        check(not(duplicate:=seen&ids),f'Cross-pack ID collision: {duplicate}')
        seen|=ids
    print(f'Verified {len(d)} distinct ranged audio assets.')
