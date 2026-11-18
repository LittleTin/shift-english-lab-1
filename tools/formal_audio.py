#!/usr/bin/env python3
"""Author original timed listening supplements; never overwrite practice audio/packs.
Produces compact MP3 cue banks plus a standalone plan JSON for UI integration.
All directions are newly written, not recordings or copied ETS test material.
"""
from pathlib import Path
import argparse,json,hashlib,subprocess,concurrent.futures,sys
import numpy as np
SR=24000
DIRECTIONS={
1:'This is the listening section. It has one hundred questions in four parts. Each recording will play once. Choose the best answer for every question. Part one. Look at the photograph. Listen to four descriptions, labeled A, B, C, and D. Select the description that best matches the picture. The descriptions appear only in the recording.',
2:'Part two. Listen to a question or statement, followed by three possible replies. Choose the reply that fits best. The question and the replies appear only in the recording.',
3:'Part three. Listen to each conversation. Then answer three questions about it. The questions and four answer choices are displayed. You will hear each question after the conversation. Choose the best answer. When a question includes a graphic, use both the graphic and the conversation.',
4:'Part four. Listen to each short talk. Then answer three questions about it. The questions and four answer choices are displayed. You will hear each question after the talk. Choose the best answer. When a question includes a graphic, use both the graphic and the talk.'}
_engine=None
_melo=None
_melo_args=None

def init(models,threads,melo_args=None):
 global _engine,_melo_args
 _melo_args=melo_args
 import onnxruntime as ort
 from kokoro_onnx import Kokoro
 opts=ort.SessionOptions();opts.intra_op_num_threads=threads;opts.inter_op_num_threads=1
 _engine=Kokoro.from_session(ort.InferenceSession(str(models/'kokoro-v1.0.onnx'),sess_options=opts,providers=['CPUExecutionProvider']),str(models/'voices-v1.0.bin'))

def produce(job):
 text,path=job
 if path.exists():return str(path)
 audio,sr=_engine.create(text,voice='af_heart',speed=1.0,lang='en-us')
 from render_listening import clear_speech
 audio=clear_speech(audio,sr)
 np.save(path,audio.astype(np.float32))
 return str(path)

def key(text):return hashlib.sha256(text.encode()).hexdigest()[:20]
def probe(path):return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],text=True))

def entries(pack):
 out=[]
 for g in pack['groups']:
  if g['part']>4:continue
  qs=sorted([q for q in pack['questions'] if q['groupId']==g['id']],key=lambda q:q['number'])
  n=qs[0]['number']
  intro=f'Number {n}.' if g['part']<3 else f'Questions {n} through {qs[-1]["number"]}. Listen to the '+('conversation.' if g['part']==3 else 'talk.')
  out.append((g['id']+':intro',intro))
  if g['part']>=3:
   for q in qs:out.append((q['id'],f'Number {q["number"]}. {q["prompt"]}'))
 return out

def bank(items,path,cache):
 # Independent compact banks; guards lie outside referenced ranges.
 refs={};chunks=[];offset=0;bank_number=1
 def flush():
  if not chunks:return
  x=np.concatenate(chunks+[np.zeros(int(.3*SR),np.float32)])
  dest=path.with_name(path.stem+f'-{bank_number:02}'+path.suffix)
  subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','1','-i','pipe:0','-c:a','libmp3lame','-b:a','48k',str(dest)],input=x.astype('<f4').tobytes(),check=True)
  assert dest.stat().st_size<470000
 for ident,text in items:
  clip=np.load(cache/(key(text)+'.npy'));pad=np.zeros(int(.25*SR),np.float32)
  if offset+len(clip)+len(pad)>71*SR and chunks:
   flush();chunks=[];offset=0;bank_number+=1
  chunks.append(pad);offset+=len(pad)
  filename=path.stem+f'-{bank_number:02}'+path.suffix
  refs[ident]={'src':filename,'start':round(offset/SR,5),'end':round((offset+len(clip))/SR,5),'duration':round(len(clip)/SR,5),'text':text}
  chunks.append(clip);offset+=len(clip)
 flush()
 return refs

def make_plan(pack,site,dirs,refs,target):
 frames=[];last=0
 def audio(ref,role,part,g=None,q=None):
  r={k:v for k,v in ref.items() if k!='text'}
  r.update(kind='audio',role=role,part=part)
  if g:r['groupId']=g
  if q:r['questionId']=q
  frames.append(r)
 def pause(seconds,part,g,q=None):
  r=dict(kind='silence',role='answer',duration=seconds,part=part,groupId=g)
  if q:r['questionId']=q
  frames.append(r)
 for g in pack['groups']:
  part=g['part']
  if part>4:continue
  gid=g['id'];qs=sorted([q for q in pack['questions'] if q['groupId']==gid],key=lambda q:q['number'])
  if part!=last:audio(dirs[str(part)],'direction',part,gid);last=part
  audio(refs[gid+':intro'],'cue',part,gid)
  # Read real MP3 duration rather than stale pack metadata.
  start=g.get('audioStart',0);end=g.get('audioEnd')
  if end is None:end=probe(site/g['audio'])
  duration=end-start
  audio(dict(src=g['audio'],start=start,end=end,duration=duration),'passage',part,gid)
  if part>=3:
   for q in qs:
    audio(refs[q['id']],'question',part,gid,q['id']);pause(8,part,gid,q['id'])
  else:pause(5,part,gid,qs[0]['id'])
 base=sum(f['duration'] for f in frames); pauses=[f for f in frames if f['kind']=='silence']
 if base>target:raise ValueError(f'{pack["testId"]}: content {base:.1f}s exceeds target {target}s')
 extra=(target-base)/len(pauses)
 for f in pauses:f['duration']=round(f['duration']+extra,5)
 pauses[-1]['duration']+=target-sum(f['duration'] for f in frames)
 offset=0
 for f in frames:f['at']=round(offset,5);offset+=f['duration']
 return dict(schemaVersion=1,testId=pack['testId'],duration=target,timing='Original practice pacing; not an ETS recording or official timing specification.',frames=frames)

def practice_group(job):
 g,site,work=job
 global _melo
 import render_listening as rl
 rl.engine=_engine
 path=site/g['audio']; mark=work/(g['id']+'.json')
 script_hash=hashlib.sha256(json.dumps(g['turns'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 if mark.exists() and path.exists():
  saved=json.loads(mark.read_text())
  if saved.get('scriptSha256')==script_hash:return saved
 choices={'female':[('US','af_heart'),('UK','bf_emma'),('US','af_sarah'),('UK','bf_isabella')],
          'male':[('UK','bm_george'),('US','am_michael'),('UK','bm_fable'),('US','am_puck')]}
 speaker_map={};counts={'male':0,'female':0};pcm=[np.zeros(int(.25*SR),np.float32)]
 group_number=int(g['id'].split('g')[-1])
 australian=bool(_melo_args and g['part']==4 and group_number%5==0)
 if australian and _melo is None:
  _melo=rl.MeloBridge(_melo_args[0],_melo_args[1],work)
 seed=group_number%2
 for turn in g['turns']:
  gender=turn['voice'];sid=turn.get('speaker',gender)
  if sid not in speaker_map:
   loc,voice=choices[gender][(counts[gender]+seed)%4];counts[gender]+=1
   speaker_map[sid]={'speaker':sid,'modelVoice':voice,'locale':'en-'+('GB' if loc=='UK' else 'US'),'role':gender}
  if australian:speaker_map[sid]={'speaker':sid,'modelVoice':'EN-AU','locale':'en-AU'}
  spec=speaker_map[sid];voice=spec['modelVoice'];lang='en-gb' if spec['locale']=='en-GB' else 'en-us'
  lines=[(turn['text'],.3)]
  if g['part'] in (1,2) and turn['text'].startswith('A.'):
   split=rl.letter_pattern.split(turn['text'])
   lines=[(f'{letter}. {body.strip()}',.67 if g['part']==1 else .55) for letter,body in zip(split[1::2],split[2::2])]
  for text,pause in lines:
   text=rl.acronym.sub(lambda m:' '.join(m.group()),text)
   if australian:raw,sr,_=_melo.render(text,gender,'AU')
   else:raw,sr=_engine.create(text,voice=voice,speed=1.0,lang=lang)
   pcm.extend([rl.clear_speech(raw,sr),np.zeros(round(pause*SR),np.float32)])
 pcm[-1]=np.zeros(int(.42*SR),np.float32)
 path.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','1','-i','pipe:0','-c:a','libmp3lame','-b:a','48k',str(path)],input=np.concatenate(pcm).astype('<f4').tobytes(),check=True)
 result=dict(id=g['id'],audio=g['audio'],duration=probe(path),speakers=list(speaker_map.values()),scriptSha256=script_hash)
 mark.write_text(json.dumps(result,indent=2)+'\n');return result


def pack_practice(site,work,prefix='t03',max_seconds=72):
 rows=[json.loads(p.read_text()) for p in sorted(work.glob(prefix+'-g*.json'))]
 assert len(rows)==54, f'Expected 54 complete groups, found {len(rows)}'
 buckets=[]
 for row in sorted(rows,key=lambda r:r['duration'],reverse=True):
  size=row['duration']+.3
  target=next((b for b in buckets if b['duration']+size<=max_seconds),None)
  if target is None:target={'duration':0,'rows':[]};buckets.append(target)
  target['rows'].append(row);target['duration']+=size
 result=[]
 for n,bucket in enumerate(buckets,1):
  chunks=[];offset=0;path=site/'audio'/f'{prefix}-bank-{n:02}.mp3'
  for row in bucket['rows']:
   pcm=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(site/row['audio']),'-ar',str(SR),'-ac','1','-f','f32le','pipe:1']),dtype='<f4')
   chunks.append(np.zeros(int(.15*SR),np.float32));offset+=int(.15*SR)
   updated={**row,'audio':str(path.relative_to(site)),'audioStart':offset/SR,'audioEnd':(offset+len(pcm))/SR,'duration':len(pcm)/SR}
   result.append(updated);chunks.append(pcm);offset+=len(pcm)
   chunks.append(np.zeros(int(.15*SR),np.float32));offset+=int(.15*SR)
  subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','1','-i','pipe:0','-c:a','libmp3lame','-b:a','48k',str(path)],input=np.concatenate(chunks).astype('<f4').tobytes(),check=True)
  assert path.stat().st_size<470000,(path,path.stat().st_size)
 out=work/(prefix+'-bank-manifest.json');out.write_text(json.dumps(sorted(result,key=lambda r:r['id']),indent=2)+'\n')
 print('Packed',len(rows),'groups into',len(buckets),'banks; manifest',out,flush=True)


def main():
 p=argparse.ArgumentParser();p.add_argument('--site',type=Path,required=True);p.add_argument('--models',type=Path,required=True);p.add_argument('--scratch',type=Path,required=True);p.add_argument('--packs',nargs='+',default=['test-01','test-02']);p.add_argument('--workers',type=int,default=2);p.add_argument('--threads',type=int,default=1);p.add_argument('--target',type=float,default=2700);p.add_argument('--cues-only',action='store_true');p.add_argument('--practice-json',type=Path);p.add_argument('--melo-python',type=Path);p.add_argument('--melo-provider',type=Path);p.add_argument('--pack-practice',action='store_true');a=p.parse_args()
 a.scratch.mkdir(parents=True,exist_ok=True);dest=a.site/'audio'/'formal';dest.mkdir(parents=True,exist_ok=True)
 if a.pack_practice:
  pack_practice(a.site,a.scratch);return
 if a.practice_json:
  data=json.loads(a.practice_json.read_text());groups=data if isinstance(data,list) else data['groups']
  jobs=[(g,a.site,a.scratch) for g in groups if g['part']<=4]
  melo_args=(a.melo_python,a.melo_provider) if a.melo_python and a.melo_provider else None
  with concurrent.futures.ProcessPoolExecutor(a.workers,initializer=init,initargs=(a.models,a.threads,melo_args)) as pool:
   for result in pool.map(practice_group,jobs):print(json.dumps(result),flush=True)
  return
 packs=[json.loads((a.site/'data'/(name+'.json')).read_text()) for name in a.packs]
 texts=list(DIRECTIONS.values())+[t for pack in packs for _,t in entries(pack)]
 jobs=[(t,a.scratch/(key(t)+'.npy')) for t in dict.fromkeys(texts) if not (a.scratch/(key(t)+'.npy')).exists()]
 with concurrent.futures.ProcessPoolExecutor(a.workers,initializer=init,initargs=(a.models,a.threads)) as pool:
  for n,r in enumerate(pool.map(produce,jobs)):print(f'{n+1}/{len(jobs)} {r}',flush=True)
 dirs=bank([(str(k),v) for k,v in DIRECTIONS.items()],dest/'directions.mp3',a.scratch)
 for ref in dirs.values():ref['src']='audio/formal/'+ref['src']
 for pack in packs:
  refs=bank(entries(pack),dest/(pack['testId']+'-cues.mp3'),a.scratch)
  for ref in refs.values():ref['src']='audio/formal/'+ref['src']
  metadata=dict(directions=dirs,cues=refs)
  (dest/(pack['testId']+'-cues.json')).write_text(json.dumps(metadata,indent=2)+'\n')
  if not a.cues_only:
   plan=make_plan(pack,a.site,dirs,refs,a.target)
   (dest/(pack['testId']+'-plan.json')).write_text(json.dumps(plan,indent=2)+'\n')
   print(pack['testId'],len(plan['frames']),sum(f['duration'] for f in plan['frames']),flush=True)
if __name__=='__main__':main()
