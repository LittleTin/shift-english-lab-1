#!/usr/bin/env python3
"""Verify independent local builds, exact old URL behavior and export exclusions."""
import collections
import json
from pathlib import Path
import sys
import tempfile

from package import EXAMS, BINARY_EXT, old_policy, read, sha
from static_export import static, verify, rewrite

HERE=Path(__file__).resolve().parent
WS=HERE.parent
a,b,projected=(Path(x) for x in sys.argv[1:])
receipt=verify(a)
assert sha(a/'receipt.json')==sha(b/'receipt.json')
assert receipt==verify(b)
assert not receipt['resumeSupported'] and 'resumeSnapshots={};' in read(a/'runtime','data/catalog.js')
assert len(list((a/'objects').iterdir()))==len(receipt['objects'])
assert (a/'runtime/.nojekyll').read_bytes()==b''
assert (projected/'site/.nojekyll').read_bytes()==b''
assert len(receipt['routes'])-len(receipt['objects'])==158
assert receipt['mediaAvoidedBytes']==receipt['mediaLogicalBytes']-receipt['mediaPhysicalBytes']
assert not any(set(url.split('/'))&{'archive','qa-checkpoints','fixture','source','authoring','reconcile'}
               for url in (*receipt['routes'],*receipt['runtime']))
exact=WS/'shift-media-migration/acceptance/rebuilt'
for exam in EXAMS:
    for ext in ('json','js'):
        path=f'data/{exam}.{ext}'
        assert sha(exact/path)==receipt['runtime'][path]['sha256']
for url,item in receipt['routes'].items():
    reference=(exact if item['roles']==['current-pack'] else WS/'shift-media-migration/acceptance/staged')/url
    assert sha(reference)==item['sha256']
p=json.loads(read(projected,'static-receipt.json'))
assert p['sourceReceiptSha256']==sha(a/'receipt.json')
assert p['unpublishedURLChanges'] and all('/exams/' in k for k in p['unpublishedURLChanges'])
physical=collections.Counter()
for url,row in p['files'].items():
    assert sha(projected/'site'/url)==row['sha256']
    if Path(url).suffix.lower() in BINARY_EXT:
        physical[row['sha256']]+=1
assert len(physical)==len(receipt['objects']) and set(physical.values())=={1}
for exam in EXAMS:
    path=f'data/{exam}.json'
    baseline=json.loads(read(a/'runtime',path))
    assert json.loads(read(projected/'site',path))==rewrite(baseline,p['unpublishedURLChanges'])
for url,item in receipt['routes'].items():
    target=p['unpublishedURLChanges'].get(url,url)
    assert p['files'][target]['sha256']==item['sha256']

def fails(fn, text):
    try:
        fn()
    except ValueError as exc:
        assert text in str(exc), str(exc)
    else:
        raise AssertionError(f'Unexpected success: {text}')

overlay=WS/'shift-media-migration/resume-compat/fixture'
meta=json.loads(read(overlay,'resume-overlay-manifest.json'))
fails(lambda:old_policy(None,overlay,'9.9.1'),'independently verified')
with tempfile.TemporaryDirectory(dir=HERE) as t:
    t=Path(t)
    sample=t/'policy.json'
    entry=meta['catalogEntries']['test-01']
    policy={k:entry[k] for k in ('version','from','until')}
    policy.update(commit=meta['commit'],manifestSha256=sha(overlay/'resume-overlay-manifest.json'),
        deploymentEvidence='known synthetic fixture; test expected to fail')
    sample.write_text(json.dumps(policy))
    fails(lambda:old_policy(sample,overlay,'9.9.1'),'synthetic prior epoch')
    fails(lambda:static(a,t/'out',set()),'Static aliases unavailable')
    assert not (t/'out').exists()
    fails(lambda:static(a,t/'out',{'audio/preview/azure/en-US-JennyNeural.mp3'}),'cannot be remapped'
          if 'audio/preview/azure/en-US-JennyNeural.mp3' in receipt['routes'] else 'Unknown URL')
    assert not (t/'out').exists()
print('PASS: stable URL bytes / two-build deterministic receipt / static one-blob projection / protected and unknown old routes')
