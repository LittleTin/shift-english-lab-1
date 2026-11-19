#!/usr/bin/env python3
"""Build local, content-addressed SHIFT release candidates from canonical media."""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

WORKSPACE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('shift_layout', WORKSPACE/'shift-layout-stage/layout.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
EXAMS = layout.EXAMS
PAGES = ('index.html', '使用說明.html', '語音試聽.html')
SHELL = (*PAGES, 'assets/app.js', 'assets/favicon.svg', 'assets/style.css',
         'assets/release-label.js', 'assets/scenes/formal-example.svg',
         'data/catalog.js', 'data/example-pack.json', 'AUTHORING.md')
BINARY_EXT = {'.mp3','.wav','.svg','.png','.jpg','.jpeg','.webp','.ogg','.m4a'}
VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+\Z')
HEX = re.compile('[a-f0-9]{64}\\Z')
SYNTH_INTERVAL = (1000000000000,2000000000000)
require, sha = layout.require, layout.file_hash


def safe(root, url):
    require(isinstance(url,str) and re.fullmatch(r"[A-Za-z0-9_./\-\u3400-\u9fff]+",url),
            f'Invalid URL: {url}')
    p = root
    require(not p.is_symlink(), f'Symlink root: {p}')
    for part in url.split('/'):
        require(part not in ('','.','..') and (not part.startswith('.') or url=='.nojekyll'), f'Invalid URL: {url}')
        p /= part
        require(not p.is_symlink(), f'Symlink: {p}')
    return p


def require_public_path(url):
    require(not any(part.casefold() == 'question-reserve' for part in str(url).split('/')),
            f'Question reserve is not a publication input: {url}')


def require_no_reserve_tree(root):
    for path in root.rglob('*'):
        require_public_path(path.relative_to(root).as_posix())


def inspect(path):
    require(path.is_file() and not path.is_symlink(),f'Missing regular file: {path}')
    return {'sha256':sha(path),'size':path.stat().st_size}


def read(root,url):
    file=safe(root,url)
    require(file.is_file(),f'Missing {file}')
    return file.read_text(encoding='utf-8')


def emit(root,url,body):
    target=safe(root,url)
    require(not target.exists(),f'Duplicate output {url}')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(body,encoding='utf-8')


def copy(root,url,src):
    target=safe(root,url)
    require(not target.exists(),f'Duplicate output {url}')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,target)


def verify_receipt(source, assets):
    for url, item in sorted(assets.items()):
        require(inspect(safe(source,url))==item,f'Hash/size mismatch {url}')


def canonical_media(source, built):
    manifest = json.loads(read(source,'manifest.json'))
    out={}
    for exam in EXAMS:
        pack=json.loads(read(built,f'data/{exam}.json'))
        require('legacyQuestions' not in pack,f'Archive embedded in active {exam}')
        for url in set(layout.refs(pack)):
            bm=inspect(safe(built,url))
            item=manifest['media'][url]
            direct=inspect(safe(source,item['source']))
            require(bm==direct=={'sha256':item['sha256'],'size':item['bytes']},f'Canonical mismatch: {url}')
            out[url]=bm
    return out


def old_policy(policy_path, overlay, current_version):
    if not policy_path:
        require(not overlay,'Prior overlay needs a separate independently verified deployment policy')
        return {}, {}, {}
    require(overlay is not None,'Missing prior overlay')
    policy = json.loads(policy_path.read_text())
    require(set(policy)=={'commit','version','from','until','manifestSha256','deploymentEvidence'} and
            isinstance(policy['deploymentEvidence'],str) and bool(policy['deploymentEvidence'].strip()),'Incomplete prior policy')
    require(re.fullmatch('[a-f0-9]{40}',policy['commit']) and VERSION.fullmatch(policy['version']) and
            policy['version']!=current_version and all(type(policy[k]) is int for k in ('from','until')) and
            0<policy['from']<policy['until']<2**53 and (policy['from'],policy['until'])!=SYNTH_INTERVAL,
            'Unknown, current, invalid, or synthetic prior epoch')
    manifest_path=safe(overlay,'resume-overlay-manifest.json')
    require(inspect(manifest_path)['sha256']==policy['manifestSha256'],'Prior manifest not pinned')
    manifest=json.loads(read(overlay,'resume-overlay-manifest.json'))
    require(manifest['commit']==policy['commit'] and set(manifest['catalogEntries'])==set(EXAMS),'Prior manifest not pinned commit or exams')
    expected_media=set()
    scripts={}
    for exam, entry in sorted(manifest['catalogEntries'].items()):
        for k in ('version','from','until'):
            require(entry[k]==policy[k],f'Prior {exam} wrong {k}')
        path=f"data/resume/v{entry['version'].replace('.','_')}/{exam}.js"
        require(entry['path']==path,f'Unexpected snapshot path: {entry}')
        text=read(overlay,path)
        v=json.dumps(entry['version']); e=json.dumps(exam)
        prefix=("window.SHIFT_RESUME_SNAPSHOTS=window.SHIFT_RESUME_SNAPSHOTS||{};\n"
                f"window.SHIFT_RESUME_SNAPSHOTS[{v}]=window.SHIFT_RESUME_SNAPSHOTS[{v}]||{{}};\n"
                f"window.SHIFT_RESUME_SNAPSHOTS[{v}][{e}]=")
        require(text.startswith(prefix) and text.endswith(';\n'),f'Invalid snapshot script {path}')
        pack=json.loads(text[len(prefix):-2])
        require(pack['testId']==exam and 'legacyQuestions' not in pack and len(pack['questions'])==200,
                f'Unexpected snapshot body {path}')
        layout.layout(pack,exam)
        expected_media.update(layout.refs(pack))
        require(set(entry)=={'version','from','until','path','scriptSha256'} and
            HEX.fullmatch(entry['scriptSha256']) and sha(safe(overlay,path))==entry['scriptSha256'],
            f'Unpinned prior script {path}. Generate a separate hash-bound manifest first.')
        scripts[path]=text
    require(expected_media==set(manifest['assets']),'Prior manifest contains missing or unused media')
    verify_receipt(overlay,manifest['assets'])
    entries={k:{x:v for x,v in entry.items() if x!='scriptSha256'} for k,entry in manifest['catalogEntries'].items()}
    return entries, manifest['assets'], scripts


def package(source,shell,compatible_app,out,version,old=None,policy=None,authoring=None):
    require(VERSION.fullmatch(version) and not out.exists() and not out.is_symlink(),'Choose valid new version and new output')
    app=compatible_app.read_text(encoding='utf-8')
    require(all(marker in app for marker in ('function loadResumeSnapshot(', 'async function prepareResume(',
      's.startedAt>=entry.until','s.contentVersion!==contentVersion()', 'archivedIds')),
      'Compatibility app not positively identified; no source-only app fallback')
    catalog=read(shell,'data/catalog.js')
    require("resumeSnapshots" not in catalog, "Expected clean base catalog")
    catalog,n=re.subn(r"version:'([0-9]+\.[0-9]+\.[0-9]+)'",lambda m:f"version:'{version}'",catalog)
    require(n==1,'Expected one clean prior catalog version')
    base=re.search(r"version:'([0-9]+\.[0-9]+\.[0-9]+)'",read(shell,'data/catalog.js')).group(1)
    require(base!=version,'Current candidate must have a new version to fail closed on older sessions')
    entries, old_media, scripts=old_policy(policy,old,version)
    catalog+='\nwindow.SHIFT_CATALOG.resumeSnapshots='+json.dumps(entries,sort_keys=True,separators=(',',':'))+';\n'
    demos=set(re.findall(r'src="(audio/preview/azure/[A-Za-z0-9_-]+\.mp3)"',read(shell,'語音試聽.html')))
    require(len(demos)==14,'Unexpected voice demo list')
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.shift-overlay-',dir=out.parent) as temp:
        tmp=Path(temp); built=tmp/'built'; stage=tmp/'stage'; runtime=stage/'runtime'; objects=stage/'objects'
        layout.build(source,built,omit_legacy_questions=True)
        current=canonical_media(source,built)
        routes={}
        object_rows={}
        role_counts=defaultdict(int)
        def asset(url, item, src, role):
            require_public_path(url)
            suffix=Path(url).suffix.lower()
            require(suffix in BINARY_EXT,f'Unknown media suffix {url}')
            digest=item['sha256']
            require(HEX.fullmatch(digest) and item['size']>0,f'Invalid media digest: {url}')
            if url in routes:
                require(routes[url]['sha256']==digest,f'Incompatible same-URL content: {url}')
                routes[url]['roles'].append(role)
            else:
                routes[url]={'sha256':digest,'ext':suffix,'roles':[role]}
            if digest not in object_rows:
                copy(objects,digest,src)
                object_rows[digest]=item['size']
            else:
                require(object_rows[digest]==item['size'], f'Hash size conflict {url}')
            role_counts[role]+=1
        for url,item in sorted(current.items()):
            asset(url,item,safe(built,url),'current-pack')
        for url,item in sorted(old_media.items()):
            asset(url,item,safe(old,url),'supported-resume')
        for url in sorted(set(SHELL)|demos):
            p=authoring if url=='AUTHORING.md' and authoring else safe(shell,url)
            if p.suffix.lower() in BINARY_EXT:
                asset(url,inspect(p),p,'shell')
            elif url=='assets/app.js':
                emit(runtime,url,app)
            elif url=='data/catalog.js':
                emit(runtime,url,catalog)
            elif url in PAGES:
                emit(runtime,url,read(shell,url).replace('?v='+base,'?v='+version))
            else:
                copy(runtime,url,p)
        # Preserve the current static-only GitHub Pages behavior.
        emit(runtime,'.nojekyll','')
        for exam in EXAMS:
            for ext in ('json','js'):
                url=f'data/{exam}.{ext}'
                copy(runtime,url,safe(built,url))
        for url,body in sorted(scripts.items()):
            emit(runtime,url,body)
        require_no_reserve_tree(stage)
        textfiles={p.relative_to(runtime).as_posix():inspect(p) for p in sorted(runtime.rglob('*')) if p.is_file()}
        object_bytes=sum(object_rows.values())
        route_bytes=sum(object_rows[r['sha256']] for r in routes.values())
        payload={'format':1,'localCandidateOnly':True,'version':version,'activePackSha256':{
          exam:textfiles[f'data/{exam}.json']['sha256'] for exam in EXAMS},
          'snapshotPolicySha256':sha(policy) if policy else None,'resumeSupported':bool(entries),
          'routes':routes,'objects':object_rows,'runtime':textfiles,'roles':dict(role_counts),
          'mediaPhysicalBytes':object_bytes,'mediaLogicalBytes':route_bytes,'mediaAvoidedBytes':route_bytes-object_bytes}
        emit(stage,'receipt.json',json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        stage.rename(out)
    return payload


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    for option in ['source','shell','app','output']:
        cli.add_argument('--'+option,type=Path,required=True)
    cli.add_argument('--version',required=True)
    cli.add_argument('--old-overlay',type=Path)
    cli.add_argument('--authoring',type=Path)
    cli.add_argument('--old-policy',type=Path)
    a=cli.parse_args()
    p=package(a.source,a.shell,a.app,a.output,a.version,a.old_overlay,a.old_policy,a.authoring)
    print(f"{len(p['routes'])} stable media URLs -> {len(p['objects'])} objects, {p['mediaAvoidedBytes']:,} duplicate bytes avoided.")

if __name__=='__main__':
    main()
