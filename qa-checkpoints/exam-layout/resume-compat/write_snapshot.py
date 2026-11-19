#!/usr/bin/env python3
"""Create resume-only built-in packs from the exact version deployed before migration.

Run only after independently confirming the deployed commit and its interval.
Does not alter the current catalog, source, or deployment; creates a new overlay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

RELEASES = ('test-01', 'test-02', 'test-03')
MEDIA_FIELDS = {'audio', 'image', 'src'}
SAFE = re.compile(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z')

def media(obj):
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in MEDIA_FIELDS and isinstance(v,str):
                if v.split('/')[0] not in {'audio','assets'} or not all(SAFE.fullmatch(x) for x in v.split('/')):
                    raise ValueError('Bad media ref: '+v)
                yield v
            else:
                yield from media(v)
    elif isinstance(obj,list):
        for v in obj:
            yield from media(v)

def emit(repo, commit, version, deployment_start, deployment_end, out):
    if not re.fullmatch('[a-f0-9]{40}',commit) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version):
        raise ValueError('Specify an exact commit SHA and semver.')
    if out.exists() or out.is_symlink() or deployment_start<0 or not deployment_start<deployment_end<8640000000000000:
        raise ValueError('Supply independently verified interval in epoch milliseconds and a new output.')
    def git(path):
        return subprocess.check_output(['git','-C',str(repo),'show',f'{commit}:{path}'])
    catalog=git('data/catalog.js').decode()
    if f"version:'{version}'" not in catalog and f'version:"{version}"' not in catalog:
        raise ValueError('Commit catalog version mismatch.')
    meta={}
    seen={}
    with tempfile.TemporaryDirectory(prefix='.resume-',dir=out.parent) as tmp:
        stage=Path(tmp)/'site'
        folder=stage/'data'/'resume'/('v'+version.replace('.','_'))
        folder.mkdir(parents=True)
        for exam in RELEASES:
            body=json.loads(git(f'data/{exam}.json'))
            if body['testId']!=exam or len(body['questions'])!=200:
                raise ValueError(f'Unexpected snapshot pack: {exam}')
            # Copies already obsolete in this deployment do not tell us which
            # earlier full pack a much older session used. Do not use them.
            body.pop('legacyQuestions',None)
            raw=json.dumps(body,ensure_ascii=True,allow_nan=False,separators=(',',':')).replace('<','\\u003c')
            name=folder/f'{exam}.js'
            name.write_text("window.SHIFT_RESUME_SNAPSHOTS=window.SHIFT_RESUME_SNAPSHOTS||{};\n"
                            f"window.SHIFT_RESUME_SNAPSHOTS[{json.dumps(version)}]=window.SHIFT_RESUME_SNAPSHOTS[{json.dumps(version)}]||{{}};\n"
                            f"window.SHIFT_RESUME_SNAPSHOTS[{json.dumps(version)}][{json.dumps(exam)}]={raw};\n")
            meta[exam]={'version':version,'from':deployment_start,'until':deployment_end,'path':name.relative_to(stage).as_posix()}
            for ref in sorted(set(media(body))-set(seen)):
                blob=git(ref)
                target=stage/ref
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(blob)
                seen[ref]={'size':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}
        (stage/'resume-overlay-manifest.json').write_text(json.dumps({'commit':commit,'catalogEntries':meta,'assets':seen},indent=2)+'\n')
        stage.rename(out)
    return len(meta),len(seen),sum(d['size'] for d in seen.values())

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--commit',required=True)
    p.add_argument('--version',required=True)
    p.add_argument('--from-ms',type=int,required=True)
    p.add_argument('--until-ms',type=int,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    print(emit(a.repo,a.commit,a.version,a.from_ms,a.until_ms,a.out))
