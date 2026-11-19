"""Receive difficulty reviews bound to content hashes. Never changes a score or publishes."""
from collections import defaultdict, Counter
from copy import deepcopy
from hashlib import sha256
import json
import re
from pathlib import Path

LEVELS=('foundation','intermediate','advanced')
TESTS=('test-01','test-02','test-03')
SHA=re.compile(r'[0-9a-f]{64}\Z')
REVIEW='difficulty-reviewed-not-published'

def digest(value):
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()

def open_same(root,test,num):
    if test not in TESTS or type(num) is not int or not 1<=num<=200:raise ValueError('Out-of-scope review')
    path=root/test/f'Q{num:03d}.json'
    for p in (root,root/test,path):
        if p.is_symlink():raise ValueError('Symlink path')
    return json.loads(path.read_text())

def review_record(test,num,source,level,reason,provenance):
    q, g=source['activeQuestion'],source.get('group')
    if source['status']!='verified-item-not-published' or (q['testId'],q['number'])!=(test,num):
        raise ValueError('Source item must already be verified')
    if level not in LEVELS or q.get('difficulty') not in LEVELS or not reason.strip() or not provenance.strip():raise ValueError('Invalid level, reason or provenance')
    if bool(q.get('groupId'))!=bool(g) or g and (g['id'],g['testId'])!=(q['groupId'],test):
        raise ValueError('Exact shared group must be audited')
    return {'status':REVIEW,'testId':test,'number':num,'questionId':q['id'],'revision':q.get('revision',1),
            'sourceQuestionSha256':digest(q),'sourceGroupSha256':digest(g) if g is not None else None,
            'fromDifficulty':q['difficulty'],'toDifficulty':level,'reason':reason,'provenance':provenance}

def check(row,test,q,g):
    if (row['status'],row['testId'],row['number'],row['questionId'],row['revision'])!=(REVIEW,test,q['number'],q['id'],q.get('revision',1)):
        raise ValueError('Active identity mismatch or review not final')
    if row['sourceQuestionSha256']!=digest(q) or row['sourceGroupSha256']!=(digest(g) if g is not None else None):
        raise ValueError('Question/group content changed; re-review difficulty')
    if row['fromDifficulty']!=q.get('difficulty') or row['toDifficulty'] not in LEVELS or not row['reason'].strip():
        raise ValueError('Missing exact label or justification')
    return row['toDifficulty']

def summarize(units, selected):
    """Evaluate final label distribution plus whole-group selectable reach."""
    count={k:0 for k in LEVELS}
    complete={k:0 for k in LEVELS}
    groupcounts={k:0 for k in LEVELS}
    for i,d in selected.items():count[d]+=1
    for ids in units.values():
        degrees={selected.get(i) for i in ids}
        if len(degrees)==1:
            d=next(iter(degrees))
            if d is not None:complete[d]+=len(ids);groupcounts[d]+=1
    return {'reviewedCounts':count,'completePracticeQuestionCounts':complete,
            'completePracticeGroupCounts':groupcounts}

def report(verified_root, review_root):
    """This is a checkpoint report, not a complete-site readiness claim."""
    results={}; rows=0; whole=0;evidence={}
    for test in TESTS:
        sections={}
        for label,start,end in (('listening',1,100),('reading',101,200)):
            assigned={};units=defaultdict(list);unit_parts={};unverified=[];missing=[];issues=[]
            for num in range(start,end+1):
                maybe=review_root/test/f'Q{num:03d}.json'
                try: a=open_same(verified_root,test,num)
                except FileNotFoundError:
                    unverified.append(num)
                    if maybe.exists():issues.append(f'Q{num:03d}: review has no verified content')
                    continue
                try:
                    q,g=a['activeQuestion'],a.get('group')
                    if a['status']!='verified-item-not-published' or (q['number'],q['testId'])!=(num,test):raise ValueError('Content not verified for active identity')
                    unit=('group',q['groupId']) if q.get('groupId') else ('question',num)
                    units[unit].append(num)
                    unit_parts[unit]=q['part']
                    try: row=open_same(review_root,test,num)
                    except FileNotFoundError:
                        missing.append(num)
                        continue
                    assigned[num]=check(row,test,q,g)
                    evidence[(test,num)]=row
                except (ValueError,KeyError,TypeError,AttributeError) as exc:issues.append(f'Q{num:03d}: {exc}')
            eligible_units={}
            for unit,nums in units.items():
                part=unit_parts[unit]
                if unit[0]=='group' and part in (3,4,6) and len(nums)!=(4 if part==6 else 3):continue
                if unit[0]=='group' and part==7 and unverified:continue  # group size unknown in incomplete reading
                eligible_units[unit]=nums
            score=summarize(eligible_units,assigned)
            all_reviewed=len(assigned)==100 and not issues
            problems=[]
            if all_reviewed:
                # Spec says endpoints must not be symbolic (one or two items),
                # and each endpoint needs actual whole-group practice reach.
                for d in (LEVELS[0],LEVELS[2]):
                    if score['reviewedCounts'][d]<3:problems.append(f'{d} has only zero, one or two items')
                    if score['completePracticeQuestionCounts'][d]<3:
                        problems.append(f'{d} has no meaningful set of complete eligible units')
                if score['reviewedCounts']['intermediate']<=max(score['reviewedCounts']['foundation'],score['reviewedCounts']['advanced']):
                    problems.append('intermediate not the largest level')
            rows+=len(assigned)
            whole+=int(all_reviewed and not problems)
            sections[label]=dict(reviewed=len(assigned),contentUnverified=unverified,reviewMissing=missing,
                                 issues=issues,distributionIssues=problems,**score,
                                 reviewComplete=all_reviewed,distributionAccepted=all_reviewed and not problems,
                                 practiceHint='10 is the smallest target shown by the current UI; shortfall is permitted, not a pass by padding.')
        results[test]=sections
    return dict(status='difficulty-review-not-browser-acceptance',reviewed=rows,total=600,exams=results,
                evidenceComplete=rows==600,difficultyGateComplete=rows==600 and whole==6,releaseReady=False),evidence

def apply_accepted(packs,verified_root,review_root):
    summary,rows=report(verified_root,review_root)
    if not summary['difficultyGateComplete']:raise ValueError('Difficulty reviews or distribution are incomplete')
    clone=deepcopy(packs)
    for test in TESTS:
        p=clone[test];g={x['id']:x for x in p['groups']}
        if len(p['questions'])!=200:raise ValueError('Bad assembled pack')
        for q in p['questions']:
            row=rows[(test,q['number'])]
            # Confirm exactly the same assembled item/group observed at review.
            q['difficulty']=check(row,test,q,g.get(q.get('groupId')))
    return clone,summary
