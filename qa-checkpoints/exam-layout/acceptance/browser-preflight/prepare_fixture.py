#!/usr/bin/env python3
"""Assemble the exact local media draft plus separate, synthetic resume test data.

The output is a local-only fixture, not a deployable build. Existing source trees
and the actual live site are never changed or used as HTTP test destinations.
"""
from argparse import ArgumentParser
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

EXAMS = ('test-01','test-02','test-03')
PAGES = ('index.html','使用說明.html','語音試聽.html')
SYNTH = '1.4.2'
PRIOR = '1.4.1'
PRIOR_SHA = '043b91761f63062708d70f7cda3a6b2046cd4cf9'


def require(cond, cause):
    if not cond:
        raise ValueError(cause)


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def regular(base, ref):
    require(isinstance(ref,str) and ref and '\\' not in ref and '\0' not in ref, 'Unsafe path')
    pieces = ref.split('/')
    require(all(x and x not in ('.','..') for x in pieces), f'Unsafe path {ref!r}')
    p = base
    require(not p.is_symlink(), f'No symlinks: {p}')
    for part in pieces:
        p = p/part
        require(not p.is_symlink(), f'No symlinks: {p}')
    return p


def copy(base, site, ref, expected=None):
    src=regular(base,ref); dst=regular(site,ref)
    require(src.is_file(), f'Missing {src}')
    digest=sha(src)
    if expected is not None:
        require(digest==expected['sha256'] and src.stat().st_size==expected['size'],f'Bad manifest hash/size: {src}')
    if dst.exists():
        require(dst.is_file() and sha(dst)==digest, f'Local fixture collision: {ref}')
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src,dst)
    return digest


def snapshot_body(js_file, test):
    # Parse sole assigned JSON object rather than execute the snapshot in Python/Node.
    s=js_file.read_text(encoding='utf-8')
    marker='window.SHIFT_RESUME_SNAPSHOTS['+json.dumps(PRIOR)+']['+json.dumps(test)+']='
    require(s.count(marker)==1, f'Unexpected script wrapper {js_file}')
    payload=s.split(marker,1)[1].strip()
    require(payload.endswith(';'),f'Incomplete {js_file}')
    q=json.loads(payload[:-1])
    require(q['testId']==test and 'legacyQuestions' not in q and len(q['questions'])==200, f'Snapshot data drift {test}')
    return q


def inject_version(text):
    require(text.count("version:'"+PRIOR+"'")==1 and 'resumeSnapshots' not in text,'Unexpected staged catalog')
    return text.replace("version:'"+PRIOR+"'","version:'"+SYNTH+"'",1)


def compose_app(root, out, target, practice_filter=False, backup_readonly=False):
    """Compose only inside fresh staging; backup regressions gate final replacement."""
    site=target.parent.parent
    compat=root/'shift-media-migration/resume-compat'
    # Audit isolated patching – no production or existing checkout changes.
    patch=root/'shift-layout-stage/retired-results.patch'
    with patch.open('rb') as inp:
        subprocess.run(['patch','--batch','--fuzz=0','--dry-run','-p1'],cwd=site,stdin=inp,check=True)
    with patch.open('rb') as inp:
        subprocess.run(['patch','--batch','--fuzz=0','-p1'],cwd=site,stdin=inp,check=True)
    filter_helper=None
    if practice_filter:
        filter_helper=root/'shift-media-migration/practice-filter-proof/make_patch.py'
        tmp_filter=out/'practice-filter-patched.js'
        subprocess.run(['python3',str(filter_helper),str(target),str(tmp_filter),str(out/'practice-filter.patch')],check=True)
        tmp_filter.replace(target)
    tmp=out/'resume-patched.js'
    subprocess.run(['python3',str(compat/'make_patch.py'),str(target),str(tmp)],check=True)
    tmp.replace(target)
    evidence={
        'retiredPatchSha256':sha(patch),
        'resumePatchHelperSha256':sha(compat/'make_patch.py'),
        'practiceFilterHelperSha256':sha(filter_helper) if filter_helper else None,
    }
    if backup_readonly:
        backup=root/'shift-layout-stage/backup-readonly'
        helper, regressions=backup/'apply.py', backup/'test_backup_cross_tab.cjs'
        tmp=out/'backup-readonly-patched.js'
        subprocess.run(['python3',str(helper),str(target),str(tmp)],check=True)
        result=subprocess.run(['node',str(regressions),str(tmp)],
                              capture_output=True,text=True)
        require(result.returncode==0,'Backup regressions failed:\n'+result.stdout+result.stderr)
        require(re.search(r'^(?:#|ℹ) tests 8$',result.stdout,re.M) and
                re.search(r'^(?:#|ℹ) pass 8$',result.stdout,re.M) and
                re.search(r'^(?:#|ℹ) fail 0$',result.stdout,re.M),
                'Expected exactly eight passing backup regressions')
        candidate=sha(tmp)
        tmp.replace(target)
        require(sha(target)==candidate,'Backup regression-tested asset changed')
        evidence['backupReadonly']={
            'helperSha256':sha(helper),'regressionsSha256':sha(regressions),
            'testedAppSha256':candidate,'offlineRegressionsPassed':8,
        }
    return evidence


def prepare(root, out, practice_filter=False, backup_readonly=False):
    require(not out.exists() and not out.is_symlink(), 'Choose a new output path')
    exact=root/'shift-media-migration/acceptance/rebuilt'
    base=root/'shift-media-migration/acceptance/staged'
    compat=root/'shift-media-migration/resume-compat'
    overlay=compat/'fixture'
    old_manifest=regular(overlay,'resume-overlay-manifest.json')
    old=json.loads(old_manifest.read_text())
    require(old['commit']==PRIOR_SHA and set(old['catalogEntries'])==set(EXAMS),'Wrong previous fixture commit or entries')
    for test,entry in old['catalogEntries'].items():
        require((entry['version'],entry['from'],entry['until'])==(PRIOR,1000000000000,2000000000000),
                f'{test} is not the known synthetic interval fixture')
    site=out/'site'; site.mkdir(parents=True)
    # Keep all exact rebuilt packs and assets, never copy all old audio blindly.
    current_files={}
    for f in sorted(exact.rglob('*')):
        require(not f.is_symlink(),f'No symlinks: {f}')
        if f.is_file():
            rel=f.relative_to(exact).as_posix()
            current_files[rel]=copy(exact,site,rel)
    for test in EXAMS:
        pack=json.loads((site/'data'/f'{test}.json').read_text(encoding='utf-8'))
        require(pack['testId']==test and len(pack['questions'])==200 and 'legacyQuestions' not in pack, f'Active pack mismatch {test}')
    shell_assets={'assets/app.js','assets/favicon.svg','assets/style.css','assets/release-label.js',
                  'assets/scenes/formal-example.svg','data/catalog.js','data/example-pack.json',*PAGES}
    preview=regular(base,'語音試聽.html').read_text(encoding='utf-8')
    demos=set(re.findall(r'src="(audio/preview/azure/[A-Za-z0-9_-]+\.mp3)"',preview))
    require(len(demos)==14,'Expected exactly 14 known voice demos')
    shell={x:copy(base,site,x) for x in sorted(shell_assets|demos)}
    shell['AUTHORING.md']=copy(root/'shift-qa',site,'AUTHORING.md')
    app_evidence=compose_app(root,out,site/'assets/app.js',practice_filter,backup_readonly)
    for ref,digest in sorted(old['assets'].items()):
        copy(overlay,site,ref,digest)
    snap={}
    for test,entry in old['catalogEntries'].items():
        ref=entry['path']
        require(ref==f'data/resume/v1_4_1/{test}.js', f'Unexpected snapshot path {ref}')
        copy(overlay,site,ref)
        snap[test]=snapshot_body(site/ref,test)
    catalog_file=site/'data/catalog.js'; text=inject_version(catalog_file.read_text(encoding='utf-8'))
    catalog_file.write_text(text+'\nwindow.SHIFT_CATALOG.resumeSnapshots='+json.dumps(old['catalogEntries'],separators=(',',':'))+';\n',encoding='utf-8')
    for name in PAGES:
        f=site/name
        s=f.read_text(encoding='utf-8')
        f.write_text(s.replace('?v='+PRIOR,'?v='+SYNTH),encoding='utf-8')
    qp=next(q for q in snap['test-01']['questions'] if q['number']==1)
    new=json.loads((site/'data/test-01.json').read_text())
    require(qp['id'] not in {q['id'] for q in new['questions']},'Requires verifiably retired prior Q1')
    g=next(g for g in snap['test-01']['groups'] if g['id']==qp['groupId'])
    frames=[f for f in snap['test-01']['listeningPlan']['frames'] if f['groupId']==g['id']]
    passage_index=next(i for i,f in enumerate(frames) if f['kind']=='audio' and f['role']=='passage')
    current_after={k:sha(site/k) for k in current_files}
    require(current_after==current_files,'Exact active draft files changed')
    all_files={}
    for b in sorted(site.rglob('*')):
        if b.is_file():
            rel=b.relative_to(site).as_posix()
            all_files[rel]={'sha256':sha(b),'size':b.stat().st_size}
    old_entry=old['catalogEntries']['test-01']
    out_meta={
      'fixtureOnly':True,'doNotDeploy':True,'syntheticVersion':SYNTH,
      'priorCommit':old['commit'],'priorVersion':PRIOR,
      'activePathsVerifiedUnchanged':len(current_files),'activeDraftMajors':{test:current_files[f'data/{test}.json'] for test in EXAMS},
      'priorManifestSha256':sha(old_manifest),'stagedShellSha256':shell,
      **app_evidence,
      'oldResume':{'entry':old_entry,'question':qp,'questionIds':[q['id'] for q in snap['test-01']['questions']],
                   'image':g['image'],'groupId':g['id'],'passageIndex':passage_index,'passage':frames[passage_index]},
      'files':all_files
    }
    if backup_readonly:
        require(out_meta['backupReadonly']['testedAppSha256']==all_files['assets/app.js']['sha256'],
                'Receipt does not bind tested backup app')
    meta=out/'fixture.json'
    meta.write_text(json.dumps(out_meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Local fixture {site}: {len(all_files)} static files, {sum(x["size"] for x in all_files.values()):,} bytes; identity {sha(meta)}')
    print('SYNTHETIC interval and local review candidate only. NEVER deploy this output.')

if __name__=='__main__':
    a=ArgumentParser(description=__doc__)
    a.add_argument('output',type=Path)
    a.add_argument('--workspace',type=Path,default=Path.cwd())
    a.add_argument('--practice-filter',action='store_true')
    a.add_argument('--backup-readonly',action='store_true')
    opts=a.parse_args()
    prepare(opts.workspace.resolve(),opts.output.absolute(),opts.practice_filter,opts.backup_readonly)
