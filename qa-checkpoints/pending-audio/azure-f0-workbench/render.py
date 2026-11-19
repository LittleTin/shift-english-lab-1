#!/usr/bin/env python3
"""Validated Azure Speech F0 candidate renderer, no publication or billing controls."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request
import wave
from xml.sax.saxutils import escape

MAX_BYTES = 6_000_000
VOICE = re.compile(r'([a-z]{2,3}-[A-Z]{2})-[A-Za-z0-9]+Neural\Z')
SLUG = re.compile(r'[a-z0-9][a-z0-9-]{1,79}\Z')
REGION = re.compile(r'[a-z][a-z0-9]{2,24}\Z')
OPTION = re.compile(r'(?<!\w)([ABCD])\. ')

def require(ok, label):
    if not ok:
        raise ValueError(label)

def speech(turn):
    name, text = turn.get('voice'), turn.get('text')
    match = VOICE.fullmatch(name) if isinstance(name, str) else None
    require(match is not None and match[1] == turn.get('locale'), 'Invalid standard voice/locale pair')
    require(isinstance(text, str) and 0 < len(text.strip()) <= 2_500, 'Empty or oversized turn')
    option_count = turn.get('optionCount', 0)
    require(type(option_count) is int and option_count in (0, 3, 4), 'Invalid option count')
    if option_count:
        parts = OPTION.split(text)
        require(parts[0] == '' and parts[1::2] == list('ABCD'[:option_count])
                and all(v.strip() for v in parts[2::2]), 'Expected exact ordered option letters')
        body = '<break time="550ms"/>'.join(
            f'<say-as interpret-as="characters">{letter}</say-as><break time="170ms"/>{escape(line.strip())}'
            for letter, line in zip(parts[1::2], parts[2::2]))
    else:
        body = escape(text.strip())
    tail = turn.get('afterMs', 0)
    require(type(tail) is int and 0 <= tail <= 750, 'Invalid tail pause')
    if tail:
        body += f'<break time="{tail}ms"/>'
    return f'<voice name="{name}">{body}</voice>'

def prepare(plan):
    require(isinstance(plan, dict) and plan.get('status') == 'editorial-ready-f0-candidate',
            'Use an explicitly editorial-ready, QA-scoped render plan')
    items = plan.get('items')
    require(isinstance(items, list) and 1 <= len(items) <= 16, 'Batch must contain one to sixteen items')
    seen = set()
    out = []
    for item in items:
        name = item.get('name')
        require(isinstance(name, str) and SLUG.fullmatch(name) and name not in seen,
                'Output names must be unique simple slugs')
        seen.add(name)
        turns = item.get('turns')
        require(isinstance(turns, list) and 1 <= len(turns) <= 12, 'Unexpected number of turns')
        utterances = ''.join(speech(t) for t in turns)
        spoken = sum(len(t['text']) for t in turns)
        require(spoken <= 3_000, 'Item exceeds bounded input')
        locale = turns[0]['locale']
        ssml = (f'<speak version="1.0" xml:lang="{locale}" '
                f'xmlns="http://www.w3.org/2001/10/synthesis">{utterances}</speak>').encode()
        out.append((name, spoken, ssml))
    return out

def validate_pcm(data):
    require(44 < len(data) <= MAX_BYTES and data[:4] == b'RIFF' and data[8:12] == b'WAVE'
            and int.from_bytes(data[4:8], 'little') + 8 == len(data), 'Incomplete or invalid RIFF')
    with wave.open(io.BytesIO(data), 'rb') as wav:
        require((wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getcomptype())
                == (24000, 1, 2, 'NONE'), 'Expected PCM 24 kHz mono signed 16 bit')
        frames = wav.getnframes()
        require(frames > 0 and len(wav.readframes(frames)) == frames * 2, 'Incomplete PCM payload')
    return frames

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan', type=Path)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--confirmed-f0', action='store_true')
    p.add_argument('--out', type=Path)
    a = p.parse_args(argv)
    with a.plan.open('rb') as f:
        raw = f.read(128_001)
    require(len(raw) <= 128_000, 'Oversized render plan')
    batch = prepare(json.loads(raw))
    plan_sha = hashlib.sha256(raw).hexdigest()
    print(json.dumps({'planSha256':plan_sha, 'dryRun':not a.execute,
                      'items':[{'name':n,'inputCharacters':c, 'ssmlSha256':hashlib.sha256(s).hexdigest()}
                               for n,c,s in batch]}), flush=True)
    if not a.execute:
        return 0
    require(a.confirmed_f0, 'Execution requires independent verification of F0 resource and availability')
    require(a.out and not a.out.exists(), 'Use a fresh local output directory')
    region = os.environ.get('AZURE_SPEECH_REGION', '')
    key = os.environ.get('AZURE_SPEECH_KEY', '')
    require(REGION.fullmatch(region) and re.fullmatch(r'[A-Za-z0-9_-]{24,160}',key),
            'Configure approved AZURE_SPEECH_REGION and AZURE_SPEECH_KEY in the execution environment')
    a.out.mkdir(mode=0o700)
    opener = urllib.request.build_opener(NoRedirect)
    endpoint = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1'
    receipt = a.out/'sha-receipt.jsonl'
    failed = False
    for i, (name, chars, body) in enumerate(batch):
        if i:
            time.sleep(3.5)
        request = urllib.request.Request(endpoint, data=body, headers={
            'Ocp-Apim-Subscription-Key':key,'Content-Type':'application/ssml+xml',
            'X-Microsoft-OutputFormat':'riff-24khz-16bit-mono-pcm','User-Agent':'SHIFT English Lab audio QA'})
        try:
            with opener.open(request,timeout=25) as response:
                data = response.read(MAX_BYTES+1)
            frames = validate_pcm(data)
            dest = a.out/(name+'.wav')
            with dest.open('xb') as f:
                f.write(data)
            record={'name':name, 'inputCharacters':chars, 'samples':frames,
                    'seconds':frames/24000, 'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest(),
                    'status':'rendered-candidate-not-validated'}
        except urllib.error.HTTPError as e:
            record={'name':name,'status':'render-error','http':e.code}
            failed=True
        except (urllib.error.URLError, OSError, wave.Error, EOFError, ValueError) as e:
            record={'name':name,'status':'render-error','errorType':type(e).__name__}
            failed=True
        line=json.dumps(record)
        with receipt.open('a') as f:
            f.write(line+'\n')
        print(line,flush=True)
        if failed:
            break
    return 2 if failed else 0

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, TypeError, AttributeError) as e:
        print('Preflight failed: '+type(e).__name__,file=sys.stderr)
        raise SystemExit(2)
