#!/usr/bin/env python3
"""Local static-only projection. Refuse aliases unless only explicitly unpublished pack URLs can change."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import tempfile
from package import EXAMS, BINARY_EXT, copy, emit, inspect, layout, read, require, safe, sha

CURRENT_NAMESPACE=re.compile(r'(audio|assets)/exams/test-0[1-3]/.+')


def verify(candidate):
    receipt=json.loads(read(candidate,'receipt.json'))
    require(receipt['format']==1 and receipt['localCandidateOnly'] is True,'Not a candidate receipt')
    for url,item in receipt['runtime'].items():
        require(inspect(safe(candidate/'runtime',url))==item,f'Runtime drift {url}')
    for digest,size in receipt['objects'].items():
        require(inspect(safe(candidate/'objects',digest))=={'size':size,'sha256':digest},f'Object drift {digest}')
    require({r['sha256'] for r in receipt['routes'].values()}==set(receipt['objects']),'Object set not reachable')
    for url,r in receipt['routes'].items():
        require(Path(url).suffix.lower()==r['ext'] and r['ext'] in BINARY_EXT,f'Media URL extension: {url}')
    return receipt


def rewrite(obj, alias):
    if isinstance(obj,list):
        return [rewrite(v,alias) for v in obj]
    if isinstance(obj,dict):
        return {k:alias.get(v,v) if k in layout.MEDIA_FIELDS and isinstance(v,str) else rewrite(v,alias)
                for k,v in obj.items()}
    return obj


def static(candidate,out,unpublished):
    require(not out.exists() and not out.is_symlink(),'Choose new output path')
    p=verify(candidate)
    groups=defaultdict(list)
    for url,r in p['routes'].items():
        if url in unpublished:
            require(CURRENT_NAMESPACE.fullmatch(url) and r['roles']==['current-pack'],
                    f'Published, shared with shell, or history URL cannot be remapped: {url}')
        groups[r['sha256']].append(url)
    require(unpublished<=p['routes'].keys(),'Unknown URL in unpublished allowlist')
    aliases={}
    primary={}
    for digest, urls in sorted(groups.items()):
        urls.sort()
        protected=[url for url in urls if url not in unpublished]
        require(len(protected)<=1,f'Static aliases unavailable for protected paths: {protected}')
        target=protected[0] if protected else urls[0]
        primary[digest]=target
        for url in urls:
            if url!=target:
                require(p['routes'][url]['ext']==p['routes'][target]['ext'],f'Media type conflict: {url}, {target}')
                aliases[url]=target
    # Protect application, HTML, CSS, or snapshots referring to a candidate path
    # outside the modeled active pack media fields. Refuse; do not blindly edit them.
    packfiles={f'data/{exam}.{ext}' for exam in EXAMS for ext in ('json','js')}
    for url in set(p['runtime'])-packfiles:
        content=read(candidate/'runtime',url)
        for src in aliases:
            require(src not in content,f'Unexpected ancillary reference {url}: {src}')
    with tempfile.TemporaryDirectory(prefix='.shift-static-',dir=out.parent) as folder:
        staged=Path(folder)/'result'; site=staged/'site'
        for url in sorted(set(p['runtime'])-packfiles):
            copy(site,url,safe(candidate/'runtime',url))
        for exam in EXAMS:
            path=f'data/{exam}.json'
            original=json.loads(read(candidate/'runtime',path))
            amended=rewrite(original,aliases)
            require(set(layout.refs(amended))=={aliases.get(s,s) for s in layout.refs(original)},f'Reference drift {exam}')
            require(all(p['routes'][s]['sha256']==p['routes'][aliases.get(s,s)]['sha256'] for s in layout.refs(original)),
                    f'Changed runtime bytes {exam}')
            # Ensure only declared media fields changed, not role, timing, order or content.
            if aliases:
                emit(site,path,json.dumps(amended,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
                emit(site,f'data/{exam}.js',layout.js_pack(amended))
            else:
                for url in (path,f'data/{exam}.js'):
                    copy(site,url,safe(candidate/'runtime',url))
        for digest,url in sorted(primary.items()):
            copy(site,url,safe(candidate/'objects',digest))
        files={f.relative_to(site).as_posix():inspect(f) for f in sorted(site.rglob('*')) if f.is_file()}
        require({r['sha256'] for u,r in files.items() if Path(u).suffix.lower() in BINARY_EXT}==set(primary),
                'Projected object set drift')
        emit(staged,'static-receipt.json',json.dumps({'localCandidateOnly':True,'sourceReceiptSha256':sha(candidate/'receipt.json'),
            'unpublishedURLChanges':aliases,'files':files},ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        staged.rename(out)
    return aliases


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('candidate',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--unpublished',type=Path,help='Exact JSON list of as-yet never published active pack media URLs')
    a=p.parse_args()
    allowed=[] if not a.unpublished else json.loads(a.unpublished.read_text())
    require(isinstance(allowed,list) and all(isinstance(x,str) for x in allowed) and len(set(allowed))==len(allowed),
            'Expected unique unpublished paths')
    if not a.output.parent.exists():
        raise ValueError('Output parent must exist')
    print(f'{len(static(a.candidate,a.output,set(allowed)))} active-media URL aliases rewritten; no old paths changed.')
