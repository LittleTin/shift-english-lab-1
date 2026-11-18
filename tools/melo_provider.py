"""Local MeloTTS official EN_INDIA provider. Run with shift_indian/.venv/bin/python.
Gender is ignored: this model offers ONE documented speaker per accent.
No voice cloning, pitch transforms, HTTP synthesis or paid APIs are used.
"""
import os, sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
os.environ.setdefault('HF_HOME',str(BASE/'cache/hf'))
os.environ.setdefault('XDG_CACHE_HOME',str(BASE/'cache'))
os.environ.setdefault('NLTK_DATA',str(BASE/'cache/nltk'))
sys.path.insert(0,str(BASE/'MeloTTS'))
_model=None

def render(text, gender=None, locale='IN'):
    global _model
    voice={'IN':'EN_INDIA','AU':'EN-AU'}[locale]
    import torch
    torch.set_num_threads(1)
    if _model is None:
        import nltk
        nltk.data.path.insert(0,os.environ['NLTK_DATA'])
        from melo.api import TTS
        _model=TTS(language='EN',device='cpu')
    if voice not in _model.hps.data.spk2id:
        raise ValueError('Unsupported official voice: '+voice)
    result=_model.tts_to_file(text,_model.hps.data.spk2id[voice],output_path=None,speed=1.0,quiet=True)
    return result,_model.hps.data.sampling_rate,voice

if __name__ == '__main__':
    # Persistent JSON-lines worker. Input {id,text,locale,gender,out}; response
    # {id,ok,path,sample_rate,modelVoice,duration,seconds} to stdout.
    import json,time,contextlib,traceback
    import soundfile as sf
    for line in sys.stdin:
        try:
            req=json.loads(line); started=time.perf_counter()
            with contextlib.redirect_stdout(sys.stderr):
                audio,sr,voice=render(req['text'],req.get('gender'),req.get('locale','IN'))
            out=Path(req['out']).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
            sf.write(out,audio,sr,subtype='FLOAT')
            response=dict(id=req.get('id'),ok=True,path=str(out),sample_rate=sr,modelVoice=voice,duration=len(audio)/sr,seconds=time.perf_counter()-started)
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            response=dict(id=req.get('id'),ok=False,error=str(e))
        print(json.dumps(response),flush=True)
