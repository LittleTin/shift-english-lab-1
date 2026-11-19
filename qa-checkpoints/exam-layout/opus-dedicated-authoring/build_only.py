#!/usr/bin/env python3
"""Build only from locked-or-provisional authoring inputs, not the old runtime."""
import argparse, hashlib, json, shutil
from pathlib import Path
import layout
def run(source,out):
    m=layout.load(source/'manifest.json')
    layout.build(source,out,omit_legacy_questions=True)
    for u,x in sorted(m['standalone'].items()):
        src=layout.locate(source,x['source'])
        if src.stat().st_size!=x['bytes'] or layout.file_hash(src)!=x['sha256']:
            raise ValueError(f'Standalone authoring asset drift: {u}')
        dst=layout.locate(out,u);dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,dst)
    for u,x in {**m['media'],**m['standalone']}.items():
        actual=layout.locate(out,u)
        if actual.stat().st_size!=x['bytes'] or layout.file_hash(actual)!=x['sha256']:
            raise ValueError(f'Compiled assigned media drift: {u}')
    print(f'Built 6 pack files and {len(m["media"])+len(m["standalone"])} current media from authoring only.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.source,a.out)
