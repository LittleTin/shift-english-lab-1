#!/usr/bin/env python3
"""Replay hash-bound text-only reading rotations into offline reconciliation inputs."""
import argparse, copy, hashlib, json, re, subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

EXAMS=tuple(f'test-{n:02}' for n in range(1,4))
MEDIA={'audio','image','archivedImage','src'}
KIND='replace-whole-reading-group-by-exact-old-scope'
def need(ok,msg):
    if not ok: raise ValueError(msg)
def dump(x):
    return json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
def dig(x):
    return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def pairs(seq):
    out={}
    for k,v in seq:
        need(k not in out,f'duplicate JSON key: {k}')
        out[k]=v
    return out
def strict(b):
    return json.loads(b,object_pairs_hook=pairs,parse_constant=lambda k: (_ for _ in ()).throw(ValueError(k)))
def media(x):
    if isinstance(x,dict):
        for k,v in x.items():
            if k in MEDIA and isinstance(v,str) and v: yield v
            yield from media(v)
    elif isinstance(x,list):
        for v in x:yield from media(v)

class Repo:
    def __init__(self,path):self.path=path
    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.path),*args])
    def read(self,rev,path):
        need(re.fullmatch(r'[a-f0-9]{40}',rev) and re.fullmatch(r'[a-zA-Z0-9_./-]+',path) and '..' not in path.split('/'),'invalid immutable reference')
        return self.git('show',f'{rev}:{path}')
    def row(self,ref,path):return strict(self.read(ref,path))

def rotate(repo,ref,baseline,index,exact_old_overrides=None):
    overrides=dict(exact_old_overrides or {})
    def old_equal(key, current, original):
        if current==original:
            need(key not in overrides,'unused override '+key)
            return True
        if not all(current.get(k)==original.get(k) for k in ('number','testId','part','groupId')):return False
        return overrides.pop(key,None)=={'observedSha256':dig(current),'verifiedSha256':dig(original)}
    need(repo.git('rev-parse','--verify','--end-of-options',ref+'^{commit}').decode().strip()==ref,'pin the full reconstruction commit')
    need(set(baseline)==set(EXAMS),'baseline must contain all three packs')
    packs=copy.deepcopy(baseline); retained={}; splices=[]; retired_legacy={t:set() for t in EXAMS}; extra_retired_ids=set()
    dirs=repo.git('ls-tree','-r','--name-only',ref,'qa-checkpoints/reconstructions').decode().splitlines()
    candidates={}
    for p in dirs:
        match=re.fullmatch(r'qa-checkpoints/reconstructions/(test-0[1-3])/([a-z0-9-]+)\.json',p)
        r=repo.row(ref,p)
        if r.get('kind')!=KIND:continue
        need(match and r.get('sourceGroupId')==match[2] and r.get('notPublished') is True,'bad scope '+p)
        candidates[(match[1],match[2])]=r
    seen=set()
    for it in index['groups']:
        t,gid=it['sourceTest'],it['groupId']
        need(t in EXAMS and re.fullmatch(r'[a-z0-9-]+',gid),'invalid reserve scope')
        key=(t,gid)
        need(key not in seen,'duplicate reserve group')
        seen.add(key)
        prefix=f'question-reserve/{t}/{gid}'; mp=prefix+'/manifest.json'
        need(it['path']==mp.removeprefix('question-reserve/'),'reserve index path mismatch')
        m=repo.row(ref,mp)
        need((m['sourceTest'],m['sourceGroupId'],m['status'],m['sourceQuestionNumbers'])==(t,gid,it['status'],it['numbers']),'reserve index mismatch')
        if it['status']=='saved-pending-replacement':
            need(m['sourceStillActive'] is True and key not in candidates,'inconsistent pending reserve')
            continue
        need(it['status']=='reserved-inactive-in-work-candidate' and m['format']=='complete-text-only-reading-group' and m['notActiveHere'] is True and m['sourceStillActive'] is False and m['media']==[],'unsupported reserve status or media')
        r=candidates.pop(key); nums=it['numbers']; ng=r['newGroupId']
        need(nums and nums==list(range(nums[0],nums[-1]+1)) and all(type(n) is int and 147<=n<=200 for n in nums),'invalid numbered scope')
        need(r['questionNumbers']==nums and r['previousReserve']==mp and m['replacementGroupId']==ng and ng!=gid,'rotation scope drift')
        expect=[f'qa-checkpoints/verified-items/{t}/Q{n:03}.json' for n in nums]
        need(r['replacementEvidence']==expect and len(m['questions'])==len(nums) and len(r['questionCanonicalSha256'])==len(nums) and len(m['replacementQuestionIds'])==len(nums),'evidence list drift')
        pack=packs[t]; gpos=[i for i,g in enumerate(pack['groups']) if g['id']==gid]
        qpos=[i for i,q in enumerate(pack['questions']) if q.get('groupId')==gid]
        oldg=repo.row(ref,prefix+'/group.json')
        need(len(gpos)==1 and old_equal(t+'/'+gid,pack['groups'][gpos[0]],oldg) and [pack['questions'][i]['number'] for i in qpos]==nums,'stale/incomplete old group '+gid)
        need((oldg['id'],oldg['testId'],oldg['part'])==(gid,t,7) and not list(media(oldg)),'not text-only part 7')
        need(re.fullmatch(r'[a-z0-9-]+',ng) and ng not in {g['id'] for p in packs.values() for g in p['groups']},'replacement group already present')
        prior=m['sourceCommit']; source_group=None; replacements=[]
        for i,n in enumerate(nums):
            path=expect[i]; row=m['questions'][i]; qdir=f'questions/Q{n:03}'; v=qdir+'/verification.json'
            need(row['number']==n and row['verificationPath']==v and row['sourceEvidencePath']==path,'old numbered source mismatch')
            encoded=repo.read(prior,path)
            need(repo.git('rev-parse',f'{prior}:{path}').decode().strip()==row['sourceEvidenceGitBlob'] and hashlib.sha256(encoded).hexdigest()==row['sourceEvidenceSha256'] and encoded==repo.read(ref,prefix+'/'+v),'old verification lost provenance')
            src=strict(encoded); old=src['activeQuestion']
            need(src['status']=='verified-item-not-published' and src['scope']=='reading' and src['group']==oldg and old==repo.row(ref,prefix+'/'+qdir+'/question.json') and old_equal(t+f'/Q{n:03}',pack['questions'][qpos[i]],old) and not list(media(old)),'stale or incorrect old item '+path)
            need((old['number'],old['testId'],old['part'],old['groupId'],old['id'],old['revision'],old['answer'])==(n,t,7,gid,row['questionId'],row['revision'],row['answer']),'old identity mismatch')
            replacement=repo.row(ref,path); q=replacement['activeQuestion']; g=replacement['group']
            need(bool(replacement.get('checks')) and replacement['status']=='verified-item-not-published' and replacement['scope']=='reading' and replacement['originalQuestion']==old and replacement['retiredSourceReference']==prefix+'/'+v,'replacement verification link mismatch')
            need((q['number'],q['testId'],q['part'],q['groupId'],q['revision'])==(n,t,7,ng,old['revision']+1) and q['id']==m['replacementQuestionIds'][i] and q['id']!=old['id'],'replacement numbered identity mismatch')
            need((g['id'],g['testId'],g['part'])==(ng,t,7) and g['passage']!=oldg['passage'] and g['passageZh']!=oldg['passageZh'] and not list(media([q,g])),'invalid replacement group or media')
            need(dig(g)==r['newGroupCanonicalSha256'] and dig(q)==r['questionCanonicalSha256'][i] and (source_group is None or source_group==g),'replacement hash/staging mismatch')
            source_group=g; replacements.append(q)
            retained[prefix+'/'+v]=encoded
            retained[prefix+'/'+qdir+'/question.json']=repo.read(ref,prefix+'/'+qdir+'/question.json')
        archive_path=f'qa-checkpoints/reconstructions/history/{t}/{gid}.json'
        legacy=[q for q in pack.get('legacyQuestions',[]) if q.get('groupId')==gid]
        if r.get('retiredLegacyHistory'):
            need(r['retiredLegacyHistory']==archive_path,'wrong history location')
            history=repo.row(ref,archive_path)
            need((history['status'],history['testId'],history['sourceGroupId'],history['sourceActiveScope'],
                  history['retiredWorkGroup'],history['noHistoricalRegrade'])==
                 ('historical-only-never-active-not-for-deploy',t,gid,nums,oldg,True),'historical scope/record mismatch')
            prev_ref=history['priorDeployedCommit']
            need(history['priorDeployedPack']==f'data/{t}.json','historical pack path mismatch')
            previous=repo.read(prev_ref,history['priorDeployedPack'])
            need(hashlib.sha256(previous).hexdigest()==history['priorDeployedPackSha256'],'historical prior pack SHA mismatch')
            past=strict(previous)
            need(past['testId']==t and [x for x in past['groups'] if x['id']==gid]==[history['priorDeployedGroup']],
                 'historical prior group mismatch')
            previous_records=past['questions']+past.get('legacyQuestions',[])
            resolved=history['legacyQuestions']; historic_ids={q['id'] for q in resolved}
            need(bool(resolved) and len(historic_ids)==len(resolved) and
                 all(q['testId']==t and q['number'] in nums and q['groupId']==gid and
                     [x for x in previous_records if x['id']==q['id']]==[q] for q in resolved),
                 'historical items do not match previous pack exactly')
            extra_retired_ids.update(historic_ids)
            base_rows=baseline[t]['questions']+baseline[t].get('legacyQuestions',[])
            need(all([x for x in base_rows if x['id']==q['id']]==[q] for q in resolved) and
                 all(q in resolved for q in legacy),'original historical question unavailable or uncovered')
            if legacy:
                pack['legacyQuestions']=[q for q in pack['legacyQuestions'] if q.get('groupId')!=gid]
                retired_legacy[t].update(q['id'] for q in legacy)
            retained[archive_path]=repo.read(ref,archive_path)
            retained[f'historical-snapshots/{prev_ref}/data/{t}.json']=previous
        else:
            need(not legacy,'retired group still referenced by legacy questions without hash-bound history')
        pack['groups'][gpos[0]]=source_group
        for pos,q in zip(qpos,replacements):pack['questions'][pos]=q
        retained[mp]=repo.read(ref,mp)
        retained[prefix+'/group.json']=repo.read(ref,prefix+'/group.json')
        splices.append({'testId':t,'numbers':nums,'oldGroupId':gid,'newGroupId':ng,'reservedManifest':mp,'oldIds':[v['questionId'] for v in m['questions']],'newIds':[q['id'] for q in replacements]})
    need(not candidates,'unmatched reconstruction')
    need(not overrides,'unused baseline override: '+','.join(overrides))
    active=set()
    all_retired={q['id'] for p in baseline.values() for q in p.get('legacyQuestions',[])}|extra_retired_ids
    for t,p in packs.items():
        qs=p['questions']; gs=p['groups']
        need(p['testId']==t and [q['number'] for q in qs]==list(range(1,201)),f'{t}: numbering drift')
        need(len({g['id'] for g in gs})==len(gs) and {q['groupId'] for q in qs if q.get('groupId')}=={g['id'] for g in gs},f'{t}: orphan/duplicate group')
        group_ids={g['id'] for g in gs}
        need(all(not q.get('groupId') or q['groupId'] in group_ids for q in p.get('legacyQuestions',[])),f'{t}: orphan legacy group')
        ids={q['id'] for q in qs}
        need(len(ids)==200 and not ids & (active|all_retired),f'{t}: duplicate/archived active ID')
        active|=ids
        need(set(media(p))==set(media(baseline[t])),f'{t}: media route drift')
        need(p.get('legacyQuestions',[])==[q for q in baseline[t].get('legacyQuestions',[]) if q['id'] not in retired_legacy[t]] and p['listeningPlan']==baseline[t]['listeningPlan'],f'{t}: historical route or listening plan drift')
    need(not active&{qid for row in splices for qid in row['oldIds']},'retired ID remains active')
    return packs,splices,retained

def check_site_and_ledger(repo,base,ref,site,ledger,splices):
    for t in EXAMS:
        rel=f'data/{t}.json'; f=site/rel
        need(not f.is_symlink() and not f.parent.is_symlink() and f.read_bytes()==repo.read(base,rel),'site baseline pack not exact Git source: '+t)
    for splice in splices:
        t=splice['testId']
        for n in splice['numbers']:
            q=f'Q{n:03}.json'; f=ledger/t/q
            need(not f.is_symlink() and not f.parent.is_symlink() and f.read_bytes()==repo.read(ref,f'qa-checkpoints/verified-items/{t}/{q}'),'rotation ledger not exact Git evidence: '+t+'/'+q)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--reconstruction-commit',required=True)
    p.add_argument('--base-commit',required=True,help='Exact old full Git commit providing the three baseline packs')
    p.add_argument('--exact-old-overrides',type=Path,help='Explicit reviewed pairs of canonical digests for older runtime text vs verified old records')
    p.add_argument('--output',type=Path,required=True,help='New local offline directory; never deploy wholesale')
    a=p.parse_args(); repo=Repo(a.repo)
    need(not a.output.exists() and not a.output.is_symlink(),'choose a new output')
    need(repo.git('rev-parse','--verify','--end-of-options',a.base_commit+'^{commit}').decode().strip()==a.base_commit,'pin the full baseline commit')
    baseline={t:repo.read(a.base_commit,f'data/{t}.json') for t in EXAMS}
    ref=a.reconstruction_commit
    overrides=strict(a.exact_old_overrides.read_bytes()) if a.exact_old_overrides else {}
    packs,splices,retained=rotate(repo,ref,{t:strict(v) for t,v in baseline.items()},repo.row(ref,'question-reserve/index.json'),overrides)
    need(a.output.parent.absolute()==a.output.parent.resolve(),'choose a non-symlink output parent')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=a.output.parent) as temp:
        staged=Path(temp)/'rotation'
        for t,q in packs.items():
            f=staged/'reconcile-input'/'data'/f'{t}.json'; f.parent.mkdir(parents=True,exist_ok=True); f.write_text(dump(q))
            f=staged/'offline-history'/'baseline'/f'{t}.json'; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(baseline[t])
        for path,body in retained.items():
            f=staged/'offline-history'/path; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(body)
        (staged/'rotation-receipt.json').write_text(dump(dict(localReplayOnly=True,baseCommit=a.base_commit,reconstructionCommit=ref,exactOldOverrides=overrides,baselineRawSha256={t:hashlib.sha256(v).hexdigest() for t,v in baseline.items()},splices=splices)))
        staged.rename(a.output)
if __name__=='__main__':
    main()
