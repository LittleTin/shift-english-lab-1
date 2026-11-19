#!/usr/bin/env python3
"""Stage active Test 01 media as exact PCM WAVs and byte-identical pictures.

The output is a fresh overlay, not a deployment. Historical plan metadata is
not rewritten; every media reference retained by this pack is copied.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path, PurePosixPath
import json
import re
import shutil
import subprocess
import tempfile
import wave

EXAM = 'test-01'
MEDIA_FIELDS = {'audio', 'image', 'archivedImage', 'src'}
SAFE = re.compile(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def locate(root, name):
    require(isinstance(name, str), f'Not a relative path: {name!r}')
    parts = name.split('/')
    require(all(SAFE.fullmatch(part) for part in parts), f'Unsafe path: {name!r}')
    p = root
    for part in parts:
        p /= part
        require(not p.is_symlink(), f'Symlink not supported: {p}')
    return p


def media_ref(name, kind=None):
    require(isinstance(name, str) and name.split('/')[0] in ({kind} if kind else {'audio', 'assets'}), f'Invalid media reference: {name!r}')
    return name


def refs(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in MEDIA_FIELDS and isinstance(v, str):
                yield media_ref(v)
            else:
                yield from refs(v)
    elif isinstance(obj, list):
        for sub in obj:
            yield from refs(sub)


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n', encoding='utf-8')


def pack_js(value):
    body = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    body = body.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return 'window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('+body+');\n'


def digest(value):
    return sha256(value).hexdigest()


class Stage:
    def __init__(self, src, out):
        self.src, self.out = src, out
        self.masters = {}
        self.wavs = []
        self.images = []
        self.copied = set()
        self.created = set()

    def copy(self, source, target=None):
        target = target or source
        if target == source and target in self.copied:
            return
        src = locate(self.src, media_ref(source))
        dst = locate(self.out, media_ref(target))
        require(src.is_file() and not dst.exists(), f'Invalid copy {source} -> {target}')
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        data_sha = digest(src.read_bytes())
        require(digest(dst.read_bytes()) == data_sha, f'Copy failed {target}')
        self.copied.add(target)
        return data_sha

    def wav(self, source, start, end, target):
        source = media_ref(source, 'audio')
        target = media_ref(target, 'audio')
        src = locate(self.src, source)
        dst = locate(self.out, target)
        require(not dst.exists(), f'Asset collision: {target}')
        if source not in self.masters:
            meta = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-select_streams', 'a:0',
                '-show_entries', 'stream=sample_rate,channels', '-of', 'json', str(src)
            ]))['streams'][0]
            decoded = subprocess.check_output([
                'ffmpeg', '-nostdin', '-v', 'error', '-i', str(src), '-map', '0:a:0',
                '-acodec', 'pcm_s16le', '-f', 's16le', '-'
            ])
            self.masters[source] = int(meta['sample_rate']), int(meta['channels']), decoded, digest(src.read_bytes())
        rate, channels, pcm, source_sha = self.masters[source]
        start, end = Decimal(str(start)), Decimal(str(end))
        lo, hi = round(start*rate), round(end*rate)
        stride = channels*2
        require(0 <= lo < hi <= len(pcm)//stride, f'Invalid interval {source}: {start}-{end}')
        expected = pcm[lo*stride:hi*stride]
        dst.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(dst), 'wb') as f:
            f.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
            f.writeframes(expected)
        with wave.open(str(dst), 'rb') as f:
            require((f.getframerate(), f.getnchannels(), f.getsampwidth(), f.getnframes()) == (rate,channels,2,hi-lo), f'WAV header verification failed: {target}')
            require(f.readframes(f.getnframes()) == expected, f'PCM roundtrip failed: {target}')
        self.created.add(target)
        self.wavs.append(dict(source=source, sourceSha256=source_sha, sourceStart=str(start), sourceEnd=str(end),
                              sampleStart=lo,sampleEnd=hi,sampleRate=rate,channels=channels,pcmSha256=digest(expected),
                              target=target, bytes=dst.stat().st_size))
        return float(end-start)


def migrate(src, out):
    src, out = Path(src).resolve(), Path(out).absolute()
    require(out.resolve() != src and not out.resolve().is_relative_to(src), 'Output must be outside the input site.')
    require(not out.exists() and not out.is_symlink(), 'Output directory must not already exist.')
    out.parent.mkdir(parents=True, exist_ok=True)
    require(out.parent.resolve() == out.parent, 'Output parent cannot be symlinked.')
    original = json.loads(locate(src,f'data/{EXAM}.json').read_text(encoding='utf-8'))
    work = deepcopy(original)
    require(work['testId'] == EXAM, 'Unexpected exam ID.')
    q_by_id = {q['id']:q for q in work['questions']}
    q_by_group = defaultdict(list)
    for q in work['questions']:
        q_by_group[q.get('groupId')].append(q)

    def q_dir(q):
        n = q['number']
        require(type(n) is int and 1 <= n <= 200, f'Invalid question {n!r}')
        return f'questions/Q{n:03}'

    def group_dir(gid):
        return q_dir(q_by_group[gid][0]) if len(q_by_group[gid]) == 1 else f'groups/{gid}'

    with tempfile.TemporaryDirectory(prefix='.exam01-', dir=out.parent) as tmp:
        stage = Stage(src, Path(tmp)/'site')
        for g in work['groups']:
            gid = g['id']
            folder = group_dir(gid)
            if 'image' in g:
                old = g['image']
                name = PurePosixPath(old).name
                new = f'assets/exams/{EXAM}/{folder}/image{PurePosixPath(name).suffix}'
                asset_sha = stage.copy(old, new)
                stage.created.add(new)
                stage.images.append(dict(groupId=gid, source=old, target=new, sha256=asset_sha))
                g['image'] = new
            if g['part'] <= 4:
                path = f'audio/exams/{EXAM}/{folder}/practice.wav'
                length = stage.wav(g['audio'], g['audioStart'], g['audioEnd'], path)
                g.update(audio=path,audioStart=0,audioEnd=length)
        for i, f in enumerate(work['listeningPlan']['frames'],1):
            if f['kind'] != 'audio':
                continue
            role = f['role']
            if role in {'intro','direction','example','closing'}:
                folder = 'common'
            elif f.get('questionId'):
                folder = q_dir(q_by_id[f['questionId']])
            else:
                folder = group_dir(f['groupId'])
            path = f'audio/exams/{EXAM}/{folder}/formal-{i:03}-{role}.wav'
            end = stage.wav(f['src'], f['start'], f['end'], path)
            f.update(src=path,start=0,end=end)

        # Prove ordering, timing, semantic metadata, plan editions, and
        # history are unchanged; only the actual locations/ranges may differ.
        orig_plan = original['listeningPlan']
        new_plan = work['listeningPlan']
        require({k:v for k,v in orig_plan.items() if k!='frames'} ==
                {k:v for k,v in new_plan.items() if k!='frames'}, 'Plan-level metadata changed.')
        def without(row, names):
            return {k:v for k,v in row.items() if k not in names}
        require(len(orig_plan['frames']) == len(new_plan['frames']), 'Frame count changed.')
        for before, after in zip(orig_plan['frames'], new_plan['frames']):
            names = {'src','start','end'} if before['kind']=='audio' else set()
            require(without(before, names)==without(after,names), 'Unexpected frame change.')
        require(len(original['groups'])==len(work['groups']), 'Group count changed.')
        for before,after in zip(original['groups'],work['groups']):
            names={'audio','audioStart','audioEnd','image'}
            require(without(before,names)==without(after,names), 'Unexpected group change.')
        require(without(original,{'groups','listeningPlan'})==without(work,{'groups','listeningPlan'}), 'Question or history data changed.')
        require({g['id'] for g in work['groups'] if g['part']<=4}=={f['groupId'] for f in new_plan['frames']}, 'Group coverage changed.')

        for ref in sorted(set(refs(work))-stage.created):
            stage.copy(ref)
        for ref in set(refs(work)):
            require(locate(stage.out,ref).is_file(), f'Incomplete output ref: {ref}')
        dump(stage.out/f'data/{EXAM}.json', work)
        (stage.out/f'data/{EXAM}.js').write_text(pack_js(work), encoding='utf-8')
        report = dict(testId=EXAM, questions=len(work['questions']), listeningGroups=len(q_by_group.keys() & {f['groupId'] for f in new_plan['frames']}),
                      formalFrames=len(new_plan['frames']), formalSeconds=round(sum(f['duration'] for f in new_plan['frames']),6),
                      migratedWavs=len(stage.wavs), migratedWavBytes=sum(x['bytes'] for x in stage.wavs),
                      verifiedPcmClips=stage.wavs, relocatedImages=stage.images,
                      retainedMediaPaths=sorted(stage.copied-stage.created))
        dump(stage.out/'migration-report.json',report)
        stage.out.rename(out)
    return {k:v for k,v in report.items() if not isinstance(v,list)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(migrate(args.site,args.out),ensure_ascii=False))
