#!/usr/bin/env python3
"""Verify that every local asset reference in the selected runtime packs exists.

Supply the browser pack JSON directory and either a full Git tree inventory
(from the exact candidate commit) or a package checkout. This is a structural
check, not an HTTP, codec, playback, or lock verification.
"""
import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import re


def references(obj):
    if isinstance(obj, dict):
        for value in obj.values():
            yield from references(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from references(value)
    elif isinstance(obj, str) and obj.startswith(('audio/', 'assets/')):
        yield obj


def safe_path(path):
    return re.fullmatch(r'[A-Za-z0-9._/-]+', path) and all(
        part not in ('', '.', '..') for part in path.split('/')
    )


def git_inventory(path):
    tree = json.loads(path.read_bytes())
    if tree.get('truncated') is not False or not isinstance(tree.get('tree'), list):
        raise ValueError('expected a complete recursive Git tree, not a truncated inventory')
    return {
        row['path'] for row in tree['tree']
        if row['type'] == 'blob' and row['mode'] in ('100644', '100755')
        and row.get('size', 0) > 0
    }


def local_inventory(root, path):
    candidate = root.joinpath(*PurePosixPath(path).parts)
    if any(p.is_symlink() for p in (candidate, *candidate.parents) if p != root and root in p.parents):
        return False
    return candidate.is_file() and candidate.stat().st_size > 0


def verify(packs, test_ids, exists):
    all_refs = Counter()
    result = {}
    for test_id in test_ids:
        if not re.fullmatch(r'test-[0-9]{2,}', test_id) or test_id in result:
            raise ValueError(f'invalid or duplicate test ID: {test_id}')
        pack = json.loads((packs / f'{test_id}.json').read_bytes())
        if pack.get('testId') != test_id or not isinstance(pack.get('groups'), list):
            raise ValueError(f'invalid runtime pack: {test_id}')
        counts = Counter(references(pack))
        if not counts:
            raise ValueError(f'no asset references in runtime pack: {test_id}')
        result[test_id] = {'occurrences': sum(counts.values()), 'distinctPaths': len(counts)}
        all_refs.update(counts)
    failures = {
        path: ('invalid path' if not safe_path(path) else 'missing, empty, or not a regular file')
        for path in sorted(all_refs)
        if not safe_path(path) or not exists(path)
    }
    return {'packs': result, 'occurrences': sum(all_refs.values()),
            'distinctPaths': len(all_refs), 'failures': failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packs', required=True, type=Path)
    parser.add_argument('--test', required=True, action='append')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--root', type=Path)
    mode.add_argument('--git-tree', type=Path)
    args = parser.parse_args()
    if args.git_tree:
        exists = git_inventory(args.git_tree).__contains__
    else:
        root = args.root.resolve()
        if not root.is_dir():
            parser.error('checkout root must be a directory')
        def exists(path):
            return local_inventory(root, path)
    report = verify(args.packs, args.test, exists)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return int(bool(report['failures']))


if __name__ == '__main__':
    raise SystemExit(main())
