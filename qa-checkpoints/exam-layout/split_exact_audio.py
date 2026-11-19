#!/usr/bin/env python3
"""Prototype: extract a sample-exact phase from the decoded source.
Uses installed FFmpeg/FFprobe. Confirm target browsers before choosing ALAC.
"""
import argparse
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import wave

def run(*parts):
    return subprocess.check_output(parts)

def decode(path):
    return run('ffmpeg','-nostdin','-v','error','-i',str(path),
               '-map','0:a:0','-f','s16le','-acodec','pcm_s16le','-')

def clip(source,start,end,dest):
    if dest.suffix.lower() not in ('.wav','.m4a') or dest.exists():
        raise ValueError('Use a new target ending in .wav or .m4a.')
    meta=json.loads(run('ffprobe','-v','error','-select_streams','a:0',
                       '-show_entries','stream=sample_rate,channels','-of','json',str(source)))['streams'][0]
    rate,channels=int(meta['sample_rate']),int(meta['channels'])
    def sample(s):
        return int((s*rate).to_integral_value(rounding=ROUND_HALF_EVEN))
    lo,hi=sample(start),sample(end)
    pcm=decode(source);stride=channels*2
    if lo<0 or hi<=lo or hi*stride>len(pcm):
        raise ValueError('The requested sound range is outside the source.')
    segment=pcm[lo*stride:hi*stride]
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        ref=Path(tmp)/'reference.wav'
        output=Path(tmp)/dest.name
        with wave.open(str(ref),'wb') as w:
            w.setnchannels(channels)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(segment)
        if dest.suffix.lower()=='.wav':
            ref.rename(output)
        else:
            run('ffmpeg','-nostdin','-v','error','-i',str(ref),
                '-map','0:a:0','-c:a','alac','-sample_fmt','s16p','-movflags','+faststart',str(output))
        if decode(output)!=segment:
            raise ValueError('The resulting clip is not PCM-identical to the decoded source range.')
        output.rename(dest)
    return dict(sampleRate=rate,channels=channels,startSample=lo,endSample=hi,
                samples=hi-lo,pcmSha256=hashlib.sha256(segment).hexdigest())

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('start',type=Decimal)
    p.add_argument('end',type=Decimal)
    p.add_argument('destination',type=Path)
    a=p.parse_args()
    print(json.dumps(clip(a.source,a.start,a.end,a.destination)))
