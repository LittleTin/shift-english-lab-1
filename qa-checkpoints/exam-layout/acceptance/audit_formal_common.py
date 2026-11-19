from pathlib import Path
import json,subprocess,hashlib,concurrent.futures,re,decimal
D=decimal.Decimal
roots={n:Path('shift-qa' if n==1 else 'shift-next') for n in (1,2,3)}
dst=Path('shift-formal-common-audit');dst.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parts={1:(1,6),2:(7,31),3:(32,70),4:(71,100)}
expected=[('intro',1),('direction',1),('example',1),('direction',2),('direction',3),('direction',4),('closing',4)]
clips={};per={}
for n,r in roots.items():
 p=r/'data'/f'test-{n:02d}.json'
 a=json.loads(p.read_text())
 planned=a['listeningPlan']['frames'];qs={x['id']:x for x in a['questions'] if x['part']<=4}
 assert sorted(q['number'] for q in qs.values())==list(range(1,101))
 assert len(planned)==284
 observed=[(i,x) for i,x in enumerate(planned) if x['role'] in {'intro','example','direction','closing'}]
 assert [(x['role'],x['part']) for i,x in observed]==expected
 head=[];used=set()
 since=D(0)
 for i,x in enumerate(planned):
  assert abs(D(str(x['at']))-since)<=D('0.0003')
  assert D(str(x['duration']))>0
  since=D(str(x['at']))+D(str(x['duration']))
  if x['role']=='answer':
   assert x['kind']=='silence' and x['questionId'] in qs and x['questionId'] not in used
   assert parts[x['part']][0]<=qs[x['questionId']]['number']<=parts[x['part']][1]
   used.add(x['questionId'])
 assert len(used)==100 and abs(since-D(2700))<D('0.0003')
 for i,x in observed:
  assert x['kind']=='audio' and 'questionId' not in x
  item=f"{x['role']}-{x['part']}"
  src,start,end=(x[k] for k in ('src','start','end'))
  h=sha(r/src)
  info=dict(role=x['role'],part=x['part'],source=src,sha256=h,start=start,end=end)
  assert not item in clips or clips[item][0]==info
  clips[item]=info,r
  if x['role']=='direction':
   first=next(v for v in planned if v['role']=='cue' and v['part']==x['part'])
   assert planned.index(first)>i
  head.append(dict(item=item,frame=i,at=x['at'],duration=x['duration']))
 per[f'test-{n:02d}']=dict(packSha256=sha(p),commonFrames=head,formalFrames=len(planned),scoredAnswerWindows=len(used),readingStartSec=2700)
image='assets/scenes/formal-example.svg'
image_hash={sha(r/image) for r in roots.values()}
assert len(image_hash)==1
required={
 'intro-1':['listening test','45 minutes','100 questions','4 parts','plays once'],
 'direction-1':['photographs','four descriptions','best matches','not shown'],
 'example-1':['a lamp is next to a mug','a mug is under a chair','a lamp is hanging from the ceiling','a person is closing a door','correct choice is a','does not count','part 1 starts now'],
 'direction-2':['question and response','three possible replies','best reply','nor the replies are printed'],
 'direction-3':['conversations','three questions','information in the graphic'],
 'direction-4':['talks','short talk','three questions','information in the graphic'],
 'closing-4':['end of the listening test','begin the reading test','75 minutes'],
}
def run(x):
 name,(e,root)=x
 out=dst/name;wav=out.with_suffix('.wav')
 subprocess.run(['ffmpeg','-loglevel','error','-y','-ss',str(e['start']),'-i',str(root/e['source']),'-t',str(e['end']-e['start']),'-vn','-ac','1','-ar','16000',str(wav)],check=True)
 subprocess.run(['test01-audio/whisper/main','-m','test01-audio/ggml-base.en.bin','-t','2','-l','en','-f',str(wav),'-oj','-of',str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 t=' '.join(x['text'].strip() for x in json.loads(out.with_suffix('.json').read_text())['transcription'])
 norm=t.lower().replace('forty-five','45').replace('forty five','45').replace('one hundred','100').replace('four parts','4 parts').replace('seventy-five','75').replace('seventy five','75')
 return name,dict(e,observed=t,missingAssertions=[v for v in required[name] if v not in norm])
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as w: checked=dict(w.map(run,clips.items()))
audit=dict(status='physical-audio-and-authored-timeline-check-not-browser-acceptance',exams=per,clips=checked,exampleImage=dict(path=image,sha256=image_hash.pop(),observed='Lamp and mug on a desk; none of chair, ceiling mounting or door action is shown. A is uniquely correct.'))
(dst/'report.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
for k,v in checked.items():print(k,v['observed'],v['missingAssertions'])
assert not any(r['missingAssertions'] for r in checked.values())
