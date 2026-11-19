#!/usr/bin/env python3
"""Materialize and assemble the SHIFT question-by-question source layout.

All media references retain their existing browser-facing URLs. Each byte file has
one canonical source location; manifests express shared dependencies rather than
copying a sound bank into each question folder.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile

EXAMS = ('test-01', 'test-02', 'test-03')
MEDIA_FIELDS = {'audio', 'image', 'archivedImage', 'src'}
RECORDS = ('questions', 'groups', 'legacyQuestions')
SAFE = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\Z')
MEDIA = re.compile(r'(?:assets|audio)/.+\Z')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_rel(value):
    require(isinstance(value, str) and bool(value), 'Empty/non-text path')
    parts = value.split('/')
    require(all(SAFE.fullmatch(p) for p in parts), f'Unsafe path: {value!r}')
    return PurePosixPath(*parts)


def locate(root, value):
    parts = safe_rel(value).parts
    p = root
    for part in parts:
        p = p / part
        require(not p.is_symlink(), f'Symlink not allowed: {p}')
    return p


def init(root):
    require(not root.is_symlink(), f'Symlink output root not allowed: {root}')
    root.mkdir(parents=True, exist_ok=True)
    require(not any(root.iterdir()), f'Output directory must be empty: {root}')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    path.write_text(data, encoding='utf-8')


def js_pack(value):
    js = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    js = js.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return 'window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push(' + js + ');\n'


def file_hash(path):
    with path.open('rb') as fp:
        h = hashlib.sha256()
        for b in iter(lambda: fp.read(2**20), b''):
            h.update(b)
        return h.hexdigest()


def refs(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k in MEDIA_FIELDS and isinstance(v, str) and MEDIA.fullmatch(v):
                safe_rel(v)
                yield v
            yield from refs(v)
    elif isinstance(value, list):
        for v in value:
            yield from refs(v)


def q_dir(exam, number):
    require(type(number) is int and 1 <= number <= 200, f'Invalid question number: {number}')
    return f'{exam}/questions/Q{number:03d}'


def id_dir(value):
    p = safe_rel(value)
    require(len(p.parts) == 1, f'Invalid record ID: {value}')
    return value


def layout(pack, exam):
    require(pack.get('testId') == exam, f'{exam}: mismatched testId')
    questions, groups = pack.get('questions'), pack.get('groups')
    require(isinstance(questions,list) and isinstance(groups,list), f'{exam}: missing records')
    require(len(questions) == 200, f'{exam}: expected 200 questions')
    require([q['number'] for q in questions] == list(range(1,201)), f'{exam}: invalid order')
    qmap, gmap, legacy_ids = {}, {}, set()
    by_group = defaultdict(list)
    for g in groups:
        gid = id_dir(g['id'])
        require(gid not in gmap, f'{exam}: duplicate group id {gid}')
        gmap[gid] = g
    for q in questions:
        qid = id_dir(q['id'])
        require(qid not in qmap, f'{exam}: duplicate question id {qid}')
        qmap[qid] = q
        gid = q.get('groupId')
        if gid is not None:
            require(gid in gmap, f'{qid}: unknown group {gid}')
            by_group[gid].append(q)
    for q in pack.get('legacyQuestions', []):
        qid = id_dir(q['id'])
        require(qid not in qmap and qid not in legacy_ids, f'{exam}: duplicate archived id {qid}')
        legacy_ids.add(qid)
    return qmap, gmap, by_group


def split(site, source, omit_legacy_questions=False):
    init(source)
    owners = defaultdict(set)
    needed = defaultdict(set)
    for exam in EXAMS:
        pack = load(locate(site, f'data/{exam}.json'))
        qmap, gmap, by_group = layout(pack, exam)
        if omit_legacy_questions:
            pack.pop('legacyQuestions',None)
        def record_deps(owner, values):
            for url in refs(values):
                owners[url].add(owner)
                needed[owner].add(url)

        indexes = defaultdict(list)
        for q in pack['questions']:
            dest = q_dir(exam,q['number'])
            indexes['questions'].append(dest + '/question.json')
            dump(locate(source,dest + '/question.json'), q)
            record_deps(dest,q)
        archive = f'{exam}/archive'
        for q in pack.get('legacyQuestions',[]):
            dest = f'{archive}/questions/{q["id"]}.json'
            indexes['legacyQuestions'].append(dest)
            dump(locate(source,dest),q)
            record_deps(archive,q)

        for gid,g in gmap.items():
            dest = f'{exam}/groups/{gid}'
            indexes['groups'].append(dest + '/group.json')
            dump(locate(source,dest + '/group.json'),g)
            audience = by_group[gid]
            if len(audience)==1:
                qdest = q_dir(exam,audience[0]['number'])
                record_deps(qdest,g)
                needed[dest].update(refs(g))
            else:
                record_deps(dest,g)
                for q in audience:
                    needed[q_dir(exam,q['number'])].update(refs(g))

        meta = {k:v for k,v in pack.items() if k not in RECORDS}
        for key in ('listeningPlan','previousListeningPlan','alternateListeningPlans'):
            if key not in meta:
                continue
            plans = meta[key].values() if key=='alternateListeningPlans' else (meta[key],)
            for plan in plans:
                for frame in plan.get('frames',[]):
                    if key != 'listeningPlan':
                        owner = archive
                    elif frame.get('role') in {'intro','direction','example','cue'}:
                        owner = f'{exam}/common'
                        for q in by_group[frame.get('groupId')]:
                            needed[q_dir(exam,q['number'])].update(refs(frame))
                    elif frame.get('questionId') in qmap:
                        owner = q_dir(exam,qmap[frame['questionId']]['number'])
                    elif frame.get('groupId') in gmap:
                        gid = frame['groupId']
                        audience = by_group[gid]
                        owner = (q_dir(exam,audience[0]['number']) if len(audience)==1
                                 else f'{exam}/groups/{gid}')
                        for q in audience:
                            needed[q_dir(exam,q['number'])].update(refs(frame))
                    else:
                        owner = f'{exam}/common'
                    record_deps(owner, frame)
        # Catch ancillary top-level media fields while preserving precise ownership above.
        record_deps(f'{exam}/common', {k:v for k,v in meta.items() if k not in
                    {'listeningPlan','previousListeningPlan','alternateListeningPlans'}})
        exam_manifest = {'version': 1, 'testId':exam, 'keyOrder':list(pack),
                         'metadata':meta, 'records':{k:indexes[k] for k in RECORDS if k in pack}}
        dump(locate(source,f'{exam}/exam.json'),exam_manifest)
    media_items = {}
    for url, path_owners in sorted(owners.items()):
        if len(path_owners)==1:
            holder, = path_owners
        else:
            exams = {p.split('/')[0] for p in path_owners}
            # Sharing between active content and archive must not move current media into archive.
            visible = {p for p in path_owners if not p.endswith('/archive')}
            holder = next(iter(visible)) if len(visible)==1 else (
                f'{next(iter(exams))}/common' if len(exams)==1 else 'common')
        rel = f'{holder}/media/{url}'
        original = locate(site,url)
        target = locate(source,rel)
        require(original.is_file(), f'Missing source media {url}')
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(original,target)
        media_items[url] = {'source':rel,'sha256':file_hash(target),'bytes':target.stat().st_size}
    for owner, assets in sorted(needed.items()):
        if assets:
            dump(locate(source, f'{owner}/media.json'),
                 {'files':[{'url':u, 'source':media_items[u]['source']} for u in sorted(assets)]})
    dump(locate(source,'manifest.json'),{'version':1,'exams':list(EXAMS),'media':media_items})


def build(source, site, omit_legacy_questions=False):
    root = load(locate(source,'manifest.json'))
    require(root.get('version') == 1 and root.get('exams') == list(EXAMS), 'Invalid root manifest')
    init(site)
    required = set()
    for exam in EXAMS:
        manifest = load(locate(source, f'{exam}/exam.json'))
        require(manifest.get('version') == 1 and manifest.get('testId') == exam, f'{exam}: malformed manifest')
        merged = dict(manifest['metadata'])
        require(not set(merged)&set(RECORDS), f'{exam}: content embedded in metadata')
        for key, paths in manifest['records'].items():
            require(key in RECORDS and isinstance(paths,list), f'{exam}: unexpected record kind {key}')
            if key == 'legacyQuestions' and omit_legacy_questions:
                continue
            prefix = f'{exam}/' + {'questions':'questions/', 'groups':'groups/',
                                   'legacyQuestions':'archive/questions/'}[key]
            rows = []
            for part in paths:
                require(part.startswith(prefix), f'{exam}: {part} outside {key} directory')
                row = load(locate(source,part))
                if key=='questions':
                    expected = q_dir(exam,row['number']) + '/question.json'
                elif key=='groups':
                    expected = f'{exam}/groups/{id_dir(row["id"])}/group.json'
                else:
                    expected = f'{exam}/archive/questions/{id_dir(row["id"])}.json'
                require(part == expected, f'Unexpected path for record: {part} != {expected}')
                rows.append(row)
            merged[key]=rows
        layout(merged,exam)
        order = [k for k in manifest['keyOrder'] if k!='legacyQuestions' or not omit_legacy_questions]
        require(len(order)==len(merged) and set(order)==set(merged), f'{exam}: invalid field order')
        pack = {key:merged[key] for key in order}
        required.update(refs(pack))
        dump(locate(site,f'data/{exam}.json'),pack)
        locate(site,f'data/{exam}.js').write_text(js_pack(pack),encoding='utf-8')
    sources = set()
    for url in sorted(required):
        require(url in root['media'],f'Unregistered media {url}')
        item = root['media'][url]
        require(item['source'] not in sources,f'Reused source path {item["source"]}')
        sources.add(item['source'])
        file = locate(source,item['source'])
        require(file.is_file() and file.stat().st_size==item['bytes'] and file_hash(file)==item['sha256'],
                f'Invalid content for media {url}')
        dest = locate(site,url)
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(file,dest)


def refresh(source, urls):
    manifest_path = locate(source, 'manifest.json')
    manifest = load(manifest_path)
    require(manifest.get('version') == 1 and manifest.get('exams') == list(EXAMS),
            'Invalid root manifest')
    for url in urls:
        require(MEDIA.fullmatch(url), f'Not a pack media URL: {url}')
        safe_rel(url)
        require(url in manifest['media'], f'Unregistered media {url}')
        item = manifest['media'][url]
        path = locate(source,item['source'])
        require(path.is_file() and path.stat().st_size > 0, f'Missing or empty media {url}')
        item.update(sha256=file_hash(path),bytes=path.stat().st_size)
    fd, tmp = tempfile.mkstemp(prefix='.manifest-',dir=source)
    try:
        os.close(fd)
        dump(Path(tmp),manifest)
        os.replace(tmp,manifest_path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True,dest='action')
    s = sub.add_parser('split')
    s.add_argument('--site',type=Path,required=True)
    s.add_argument('--source',type=Path,required=True)
    s.add_argument('--omit-legacy-questions',action='store_true',help='Exclude archived question records from editable source and generated packs')
    b = sub.add_parser('build')
    b.add_argument('--source',type=Path,required=True)
    b.add_argument('--site',type=Path,required=True)
    b.add_argument('--omit-legacy-questions',action='store_true',help='Prototype active validation only; historical UI not yet adapted')
    r = sub.add_parser('refresh-media',help='Recompute manifest digest for intentionally replaced registered media')
    r.add_argument('--source',type=Path,required=True)
    r.add_argument('urls',nargs='+',help='Existing browser-facing paths, e.g. assets/graphics/t01-g039.svg')
    a = parser.parse_args()
    try:
        if a.action=='split':
            split(a.site,a.source,a.omit_legacy_questions)
        elif a.action=='build':
            build(a.source,a.site,a.omit_legacy_questions)
        else:
            refresh(a.source,a.urls)
    except (OSError,ValueError,TypeError,KeyError) as e:
        print(f'Error: {e}',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
