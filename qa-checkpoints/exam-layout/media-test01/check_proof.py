#!/usr/bin/env python3
"""Independently inspect an existing Test 01 migration proof."""
import argparse, json, subprocess, wave
from collections import Counter
from hashlib import sha256
from pathlib import Path

def require(ok, message):
    if not ok:
        raise ValueError(message)

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def verify(site, out):
    old=read(site/'data/test-01.json')
    new=read(out/'data/test-01.json')
    report=read(out/'migration-report.json')
    require(new['questions']==old['questions'] and
            new['legacyQuestions']==old['legacyQuestions'] and
            new['previousListeningPlan']==old['previousListeningPlan'] and
            new['alternateListeningPlans']==old['alternateListeningPlans'], 'History or question change')
    if new['listeningPlan']['audioEdition'] != old['listeningPlan']['audioEdition']:
        raise ValueError('Audio edition changed')
    counts=Counter(q['part'] for q in new['questions'])
    require(sum(counts[i] for i in range(1,5)) == 100 and sum(counts[i] for i in range(5,8)) == 100, 'Bad question counts')
    entries=report['verifiedPcmClips']
    require(len(entries)==len({x['target'] for x in entries})==238, 'Unexpected staged WAV count')
    for x in entries:
        with wave.open(str(out/x['target']), 'rb') as w:
            require(w.getframerate() == x['sampleRate'] and w.getnchannels() == x['channels'] and w.getsampwidth()==2 and w.getnframes() == x['sampleEnd']-x['sampleStart'], x['target'])
            require(sha256(w.readframes(w.getnframes())).hexdigest() == x['pcmSha256'], x['target'])
    for x in report['relocatedImages']:
        data=(out/x['target']).read_bytes()
        require(data==(site/x['source']).read_bytes() and sha256(data).hexdigest()==x['sha256'], x['target'])
    for p in report['retainedMediaPaths']:
        require((out/p).read_bytes()==(site/p).read_bytes(), p)
    prefixes=['common/','questions/Q003/','questions/Q032/','groups/t01-g039/']
    def ffdecode(p):
        return subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(p),'-map','0:a:0','-f','s16le','-acodec','pcm_s16le','-'])
    reps=[next(x for x in entries if 'audio/exams/test-01/'+p in x['target']) for p in prefixes]
    for x in reps:
        lo,hi=x['sampleStart'],x['sampleEnd']
        stride=x['channels']*2
        src=ffdecode(site/x['source'])
        require(sha256((site/x['source']).read_bytes()).hexdigest() == x['sourceSha256'], x['source'])
        require(ffdecode(out/x['target'])==src[lo*stride:hi*stride], x['target'])
    print(f'PCM and WAV metadata verified: {len(entries)} clips, {len(reps)} independently decoded source/range comparisons')
    print(f'Picture copies verified: {len(report["relocatedImages"])}; preserved old paths: {len(report["retainedMediaPaths"])}')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    o=p.parse_args()
    verify(o.site,o.out)
