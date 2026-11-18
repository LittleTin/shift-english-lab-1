#!/usr/bin/env python3
"""Render bundled SHIFT listening files. Run on the authoring machine only."""
from __future__ import annotations
import argparse, atexit, json, os, re, subprocess, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

SR = 24000
VOICES = {
    'US': {'female': ('af_heart', 'af_sarah'), 'male': ('am_michael', 'am_puck')},
    'UK': {'female': ('bf_emma', 'bf_isabella'), 'male': ('bm_george', 'bm_fable')},
    'IN': {'female': ('EN_INDIA',), 'male': ('EN_INDIA',)},
    'AU': {'female': ('EN-AU',), 'male': ('EN-AU',)},
}
PATTERNS = {1: ('US','UK','IN','US','UK','US'), 2: ('US/UK','UK/US','IN/US','US/IN','UK/UK','US/US','UK/IN','IN/UK'),
            3: ('US/UK','UK/IN','IN/US','UK/US','US/IN','UK/UK','US/US','IN/UK'),
            4: ('UK','US','IN','UK','US','IN','US','UK')}
engine = indian = None
letter_pattern = re.compile(r'(?<!\w)([A-D])\.\s+')
acronym = re.compile(r'\b(?:PDF|ID|IT)\b')

class MeloBridge:
    """One local model process per renderer; text never leaves the VM."""
    def __init__(self, python, provider, workdir):
        self.outfile = (workdir / f'melo-{os.getpid()}.wav').resolve()
        self.proc = subprocess.Popen([str(python), '-u',str(provider.resolve())], stdin=subprocess.PIPE,
                      stdout=subprocess.PIPE,text=True,encoding='utf-8',bufsize=1,
                      env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
        atexit.register(self.close)

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            try:
                self.proc.wait(timeout=12)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                self.proc.wait(timeout=5)
        self.outfile.unlink(missing_ok=True)

    def render(self,text,gender,locale):
        req=dict(id='turn',text=text,gender=gender,locale=locale,out=str(self.outfile))
        self.proc.stdin.write(json.dumps(req,ensure_ascii=False)+'\n')
        self.proc.stdin.flush()
        line=self.proc.stdout.readline()
        if not line:
            raise RuntimeError('MeloTTS worker ended before replying')
        reply=json.loads(line)
        if not reply.get('ok'):
            raise RuntimeError('MeloTTS: '+reply.get('error','unknown error'))
        sr=reply['sample_rate']
        pcm=subprocess.run(['ffmpeg','-v','error','-i',str(self.outfile),'-ar',str(SR),'-ac','1',
                             '-f','f32le','pipe:1'],stdout=subprocess.PIPE,check=True).stdout
        return np.frombuffer(pcm,dtype='<f4'),SR,reply['modelVoice']

def setup(modeldir, indian_path, indian_python, threads, workdir):
    global engine, indian
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = threads
    opts.inter_op_num_threads = 1
    engine = Kokoro.from_session(ort.InferenceSession(str(modeldir/'kokoro-v1.0.onnx'), sess_options=opts,
                                                       providers=['CPUExecutionProvider']), str(modeldir/'voices-v1.0.bin'))
    if indian_path:
        indian=MeloBridge(indian_python,indian_path,workdir)

def clear_speech(x, source_sr):
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if not len(x) or not np.isfinite(x).all():
        raise RuntimeError('TTS output contains no usable waveform')
    if source_sr != SR:
        x = np.frombuffer(subprocess.run(['ffmpeg','-v','error','-f','f32le','-ar',str(source_sr),'-ac','1',
                             '-i','pipe:0','-ar',str(SR),'-f','f32le','pipe:1'],
                             input=x.astype('<f4').tobytes(),stdout=subprocess.PIPE,check=True).stdout,dtype='<f4')
    mask = np.flatnonzero(np.abs(x) > 0.006)
    if not len(mask):
        raise RuntimeError('Silent TTS output')
    x = x[max(0,mask[0]-720):min(len(x),mask[-1]+1441)].copy()
    active = x[np.abs(x)>0.013]
    rms = float(np.sqrt(np.mean(active**2)))
    gain = min(3.0, 0.118/max(rms,1e-6), 0.86/np.max(np.abs(x)))
    n = min(144, len(x)//2)
    if n:
        x[:n] *= np.linspace(0,1,n)
        x[-n:] *= np.linspace(1,0,n)
    return x*gain

def synth(text, locale, gender, index):
    text = acronym.sub(lambda m: ' '.join(m.group()), text)
    voices = VOICES[locale][gender]
    voice = voices[index % len(voices)]
    if locale in ('IN','AU'):
        raw, sr, voice = indian.render(text, gender, locale)
    else:
        raw, sr = engine.create(text, voice=voice, speed=(0.98,1.0,1.02)[index%3], lang={'US':'en-us','UK':'en-gb'}[locale])
    return clear_speech(raw,sr), voice

def plan(g,index,second):
    accents = PATTERNS[g['part']][(index+2*second)%len(PATTERNS[g['part']])].split('/')
    needs_in = 'IN' in accents
    if needs_in and g['part']==3:
        # The source question bank refers to the woman/man in many dialogues.
        # The two single-speaker Melo voices are not gender-labeled, so preserve
        # the dialogue roles using Kokoro's explicitly labeled voices.
        other = next(loc for loc in accents if loc!='IN')
        accents = [('UK' if other=='US' else 'US') if loc=='IN' else loc for loc in accents]
    elif needs_in and (index + 2*second) % 3 == 1:
        accents = ['AU' if locale=='IN' else locale for locale in accents]
    return accents, ('indian' if any(x in ('IN','AU') for x in accents) else 'us-uk')

def speaker_plan(g,index,second):
    accents,_=plan(g,index,second)
    unique={}
    for j, turn in enumerate(g['turns']):
        locale=accents[j%len(accents)]
        voices=VOICES[locale][turn['voice']]
        voice=voices[(index+second+j%len(accents))%len(voices)]
        unique.setdefault((voice,locale),{'modelVoice':voice,'locale':'en-'+{'US':'US','UK':'GB','IN':'IN','AU':'AU'}[locale],
                           **({'role':turn['voice']} if locale in ('US','UK') else {})})
    return list(unique.values())

def render(task):
    g, index, second, destination, workdir, wanted = task
    accents, kind = plan(g,index,second)
    if wanted!='all' and wanted!=kind:
        return None
    if kind=='indian' and indian is None:
        raise RuntimeError('MeloTTS provider required for '+g['id'])
    p = destination / g['audio']
    pcm = [np.zeros(int(.26*SR),np.float32)]
    for j, turn in enumerate(g['turns']):
        locale = accents[j%len(accents)]
        voice_index = index+second+j%len(accents)
        segments = [(turn['text'], .39 if g['part'] in (1,2) else .26)]
        if g['part'] in (1,2) and turn['text'].startswith('A.'):
            split = letter_pattern.split(turn['text'])
            segments = [(f'{letter}. {body.strip()}', .67 if g['part']==1 else .55)
                        for letter,body in zip(split[1::2],split[2::2])]
        for line, pause in segments:
            xs, voice = synth(line, locale,turn['voice'],voice_index)
            expected = VOICES[locale][turn['voice']][voice_index % len(VOICES[locale][turn['voice']])]
            if voice != expected:
                raise RuntimeError(f'Voice mismatch for {g["id"]}: {voice} != {expected}')
            pcm.extend((xs, np.zeros(round(pause*SR),np.float32)))
    pcm[-1] = np.zeros(int(.42*SR),np.float32)
    audio = np.concatenate(pcm)
    tmp = workdir/f"{g['id']}.tmp.mp3"
    subprocess.run(['ffmpeg','-v','error','-y','-f','s16le','-ar',str(SR),'-ac','1','-i','pipe:0',
                    '-c:a','libmp3lame','-b:a','64k',str(tmp)],
                    input=np.round(audio*32767).astype('<i2').tobytes(),check=True)
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration',
                         '-of','default=noprint_wrappers=1:nokey=1',str(tmp)],text=True))
    tmp.replace(p)
    result=dict(id=g['id'], duration=round(duration,3), speakers=speaker_plan(g,index,second), audio=g['audio'])
    mark=workdir / f"{g['id']}.json"
    tmp_mark=mark.with_suffix('.tmp')
    tmp_mark.write_text(json.dumps(result)+'\n')
    tmp_mark.replace(mark)
    return result

def tasks_for(root, workdir, select):
    for t, file in enumerate(sorted((root/'data').glob('test-*.json'))):
        pack=json.loads(file.read_text())
        offsets={}
        for g in pack['groups']:
            if not g.get('audio'):
                continue
            i=offsets.get(g['part'],0)
            offsets[g['part']]=i+1
            yield (g,i,t,root,workdir,select)

def finalize(root, workdir):
    results = {}
    for path in sorted(workdir.glob('t*-g*.json')):
        row=json.loads(path.read_text())
        assert row['id'] not in results
        results[row['id']]=row
    assert set(results)=={a[0]['id'] for a in tasks_for(root,workdir,'all')}, 'Missing group results; will not rewrite packs'
    for file in sorted((root/'data').glob('test-*.json')):
        data=json.loads(file.read_text())
        for g in data['groups']:
            if g['id'] in results:
                m=results[g['id']]
                g['duration']=m['duration']
                g['audioSpeakers']=m['speakers']
        file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
        file.with_suffix('.js').write_text('window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('+
             json.dumps(data,ensure_ascii=False,separators=(',',':'))+');\n', encoding='utf-8')
    (root/'data'/'audio-manifest.json').write_text(json.dumps(list(results.values()),indent=2)+'\n')
    print('Updated',len(results),'audio groups;',round(sum(r['duration'] for r in results.values())/60,2),'minutes')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--site',type=Path, required=True)
    p.add_argument('--models',type=Path)
    p.add_argument('--scratch',type=Path, required=True)
    p.add_argument('--indian-provider',type=Path)
    p.add_argument('--indian-python',type=Path)
    p.add_argument('--workers',type=int,default=3)
    p.add_argument('--threads',type=int,default=2)
    p.add_argument('--select',choices=['all','us-uk','indian'],default='all')
    p.add_argument('--finalize',action='store_true')
    a=p.parse_args()
    a.scratch.mkdir(parents=True,exist_ok=True)
    if a.finalize:
        finalize(a.site,a.scratch)
    else:
        if not a.models:
            p.error('--models is required when rendering')
        if a.select!='us-uk' and not (a.indian_provider and a.indian_python):
            p.error('--indian-provider and --indian-python are required for Indian English')
        tasks=[t for t in tasks_for(a.site,a.scratch,a.select)
               if a.select in ('all', plan(t[0],t[1],t[2])[1]) and not (a.scratch / (t[0]['id']+'.json')).exists()]
        start=time.monotonic()
        results=[]
        with ProcessPoolExecutor(a.workers,initializer=setup,initargs=(a.models,a.indian_provider,a.indian_python,a.threads,a.scratch)) as pool:
            for row in pool.map(render,tasks):
                if row:
                    results.append(row)
                    print(row['id'],row['duration'],','.join(s['locale'] for s in row['speakers']),round(time.monotonic()-start,1),flush=True)
        print('Completed',len(results),'new groups',flush=True)
