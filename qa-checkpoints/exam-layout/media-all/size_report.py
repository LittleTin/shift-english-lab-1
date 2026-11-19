#!/usr/bin/env python3
"""Count the media union and reject collisions with different content."""
import argparse
import json
from pathlib import Path
import hashlib

def sha(p):
    with p.open('rb') as fp:
        return hashlib.file_digest(fp,'sha256').hexdigest()

def totals(overlays):
    media = {}
    reports = []
    for root in overlays:
        report = json.loads((root/'migration-report.json').read_text(encoding='utf-8'))
        reports.append(report)
        for top in ('audio','assets'):
            for path in (root/top).rglob('*'):
                if not path.is_file():
                    continue
                key = path.relative_to(root).as_posix()
                if key in media:
                    prior = media[key]
                    if path.stat().st_size != prior.stat().st_size or sha(path) != sha(prior):
                        raise ValueError(f'Path collision has different contents: {key}')
                else:
                    media[key] = path
    count = len(media)
    wavbytes = sum(r['migratedWavBytes'] for r in reports)
    total = sum(p.stat().st_size for p in media.values())
    return {'exams': [{k:r[k] for k in ('testId','questions','formalFrames','formalSeconds','migratedWavs','migratedWavBytes')} for r in reports],
            'uniqueMediaPaths':count, 'wavBytes':wavbytes, 'mediaUnionBytes':total,
            'mediaUnionMiB':round(total/1024**2,2)}

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('overlays',type=Path,nargs='+')
    print(json.dumps(totals(parser.parse_args().overlays),indent=2))
