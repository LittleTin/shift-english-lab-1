#!/usr/bin/env python3
"""Assemble candidate deploy-root files without touching the pinned browser tree."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
A=argparse.ArgumentParser()
for k in ('tested-site','site-stage-proof','repo','out'):A.add_argument('--'+k,type=Path,required=True)
a=A.parse_args(); assert not a.out.exists()
ref='043b91761f63062708d70f7cda3a6b2046cd4cf9'
sentinel=subprocess.check_output(['git','-C',str(a.repo),'show',ref+':.nojekyll'])
assert sentinel==b''
before=json.loads(a.site_stage_proof.read_bytes())
p=a.out/'site';p.mkdir(parents=True)
old="Authors can use Python 3.9 or later with <code>tools/add_pack.py</code> to validate JSON, create a JavaScript pack suitable for offline opening and update <code>data/catalog.js</code>. Learners do not need Python. See <a href=\"AUTHORING.md\">the authoring reference</a> for the pack format and commands."
new="In a checkout of the project source, authors can use Python 3.9 or later with <code>tools/add_pack.py</code> to validate JSON, create a JavaScript pack for offline opening and update <code>data/catalog.js</code>. The tool is in the source repository, not included in this web package. Learners do not need Python. See <a href=\"AUTHORING.md\">the authoring reference</a> for the pack format and Opus media requirements."
guide='使用說明.html'
sha=lambda b:hashlib.sha256(b).hexdigest()
diff={}; files={}
for x in sorted(a.tested_site.rglob('*')):
 if x.is_dir():continue
 assert x.is_file() and not x.is_symlink()
 rel=x.relative_to(a.tested_site).as_posix(); y=p/rel;y.parent.mkdir(parents=True,exist_ok=True)
 raw=x.read_bytes(); data=raw
 if rel==guide:
  assert raw.decode().count(old)==1;data=raw.decode().replace(old,new).encode()
  y.write_bytes(data);diff[rel]=dict(before=sha(raw),after=sha(data),kind='help-only-difference-no-behavior')
 else:
  try:os.link(x,y)
  except OSError:shutil.copyfile(x,y)
 assert sha(y.read_bytes())==sha(data)
 files[rel]=dict(sha256=sha(data),bytes=len(data))
assert sum(x.stat().st_size for x in a.tested_site.rglob('*') if x.is_file())==before['totalRuntimeBytes']
(p/'.nojekyll').write_bytes(sentinel); files['.nojekyll']=dict(sha256=sha(sentinel),bytes=0)
assert not (p/'tools').exists() and not (p/'data/resume').exists()
assert all(z.endswith('.ogg') for z in files if z.startswith('audio/'))
assert len([z for z in files if z.startswith('audio/')])==before['exactMediaAssets']
assert not (p/'qa-checkpoints').exists()
report=dict(status='deploy-root-preflight-only-not-lock-or-publication',version=before['tentativeVersion'],files=files,bytes=sum(x['bytes'] for x in files.values()),opusFiles=before['exactMediaAssets'],addedSentinelSourceCommit=ref,helpOnlyDiff=diff,actualLockFiles=0,releaseReady=False,nonRuntimeDiffExcludingDocs=['.nojekyll'])
(a.out/'deploy-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(report['bytes'],len(files),files['.nojekyll'],diff)
