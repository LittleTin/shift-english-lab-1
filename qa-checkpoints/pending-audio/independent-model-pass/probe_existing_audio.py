"""Independent, zero-upload secondary ASR probe. Cannot approve a quiz item on its own."""
import argparse, hashlib,json, os,pathlib,subprocess,collections
P=argparse.ArgumentParser(description=__doc__)
P.add_argument('--repo',type=pathlib.Path,default=pathlib.Path('shift-qa'))
P.add_argument('--ref',required=True)
P.add_argument('--asset-root',type=pathlib.Path,required=True)
P.add_argument('--model-dir',type=pathlib.Path,required=True)
P.add_argument('--out',type=pathlib.Path,required=True)
P.add_argument('--test',choices=['test-01','test-02','test-03'],required=True)
P.add_argument('numbers',nargs='+',type=int)
a=P.parse_args()
m=a.model_dir.resolve()
# Exact untouched CMUSphinx source model  f20ff1b7a5db64c5e892a798479e20df86e79a35.
pinned={
  'cmudict-en-us.dict':'20b5c293e1f311fb375fe067e500ec5636f4fc7af5594967263696def9b23bfe',
  'en-us.lm.bin':'db21d0642286677699e6dbc859d2e5395570222361999387ce60f6e1d01995d6',
  'en-us/feat.params':'c982c5f75e2a30c34d2c9ef1f6b129a5a00e67e3e927565076b58664cc2404c9',
  'en-us/mdef':'2360f9a86889c1cfee8bd618a0269387911e5fb2920a594f506b18b8c79683b0',
  'en-us/means':'832019e32cac12eb318964f96f469034acb12d0348eeddc3831831a100cb4dd4',
  'en-us/noisedict':'7295b07df2c204c4f87c6782b6be1a3859d7006d4e3864181c955d6dab105a33',
  'en-us/sendump':'8c9564c0d5bef69ca9d9bf1014abe162f071644cf02cf1fa8a483c3dc165a7a8',
  'en-us/transition_matrices':'c1f7f28ea43177be734be1f88bd7f1b9a853d0e660f8599c67c6eaeca8bb539a',
  'en-us/variances':'b00d696f85e96834fc10f8e5f06428d8c4db6bffdbe5845b6f69bf6efbc48fa5',
}
for name,expected in pinned.items():
  local=m/name
  if local.is_symlink() or hashlib.sha256(local.read_bytes()).hexdigest()!=expected:
    raise ValueError('Model bytes diverge from pinned source: '+name)
git=lambda *p:subprocess.check_output(['git','-C',str(a.repo),*p])
pin=git('rev-parse','--verify','--end-of-options',a.ref+'^{commit}').decode().strip()
assert pin==a.ref and not a.out.exists() and set(a.numbers)<=set(range(1,101))
base='qa-checkpoints/pending-audio/inventory-0605'
get=lambda path:json.loads(git('show',f'{pin}:{path}'))
test=a.test;pack=get('data/'+test+'.json');ps={q['number']:q for q in pack['questions']};gs={g['id']:g for g in pack['groups']}
reg=get(base+'/index.json')
older={}
for path in reg['slices'][test]:
 for rec in get(base+'/'+path)['groups']:
  for n in rec['questions']:
   older.setdefault(n,[]).append((path,rec))
files=set(git('ls-tree','-r','--name-only',pin,f'qa-checkpoints/verified-items/{test}').decode().splitlines())
observed={}; entries=[]
for n in a.numbers:
 q=ps[n];g=gs[q['groupId']]
 rows=[];ctx=[]
 approved=f'qa-checkpoints/verified-items/{test}/Q{n:03}.json'
 if approved in files:
  ev=get(approved)
  assert ev['status']=='verified-item-not-published'
  for r in ev['audio']:
   role=r.get('mode')
   if role not in ('passage','practice','formal','formalStem','stem','question'):continue
   rows.append((role,r['path'],r.get('start',r.get('from')),r.get('end',r.get('to')),r.get('assetSha256',r.get('sha256'))))
  status='approved-audio-control'
 else:
  status='held-audio-under-independent-test'
  for fname,x in older.get(n,[]):
   ctx.append([fname,x.get('focus'),x.get('scopedMode')])
   for role in ('practicePassage','formalPassage','formalStem'):
    rs=x.get(role)
    if isinstance(rs,dict):rs=[rs]
    for r in rs or []:
     if r.get('questionId') not in (None,q['id']) and role=='formalStem':continue
     rows.append((role,r['file'],r['start'],r['end'],r['sha256']))
  assert rows,f'No scoped immutable intervals for held {test}/{n}'
 for role,path,lo,hi,sha in rows:
  k=(path,lo,hi)
  source=(a.asset_root/path).resolve()
  assert source.is_relative_to(a.asset_root.resolve()) and source.is_file() and 0<=lo<hi
  if k not in observed:
   sig=hashlib.sha256(source.read_bytes()).hexdigest();assert sig==sha,(path,sig,sha)
   filter=(f'atrim=start={lo}:end={hi},asetpts=PTS-STARTPTS,aresample=16000,apad=pad_dur=1.4,'
      f'asr=hmm={m}/en-us:dict={m}/cmudict-en-us.dict:lm={m}/en-us.lm.bin,ametadata=mode=print:file=-')
   cmd=['ffmpeg','-nostdin','-hide_banner','-v','error','-i',str(source),'-af',filter,'-f','null','-']
   v=subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=50)
   observed[k]=dict(source=path,start=lo,end=hi,sha256=sig,
     unpromptedUtterances=[line.split('=',1)[1] for line in v.stdout.splitlines() if line.startswith('lavfi.asr.text=')])
 entries.append(dict(number=n,questionId=q['id'],groupId=g['id'],status=status,priorQuestionedTokens=ctx,
  windows=[dict(role=r[0],**observed[tuple(r[1:4])]) for r in list(dict.fromkeys(rows))]))
a.out.write_text(json.dumps(dict(test=test,pinnedStage=pin,recognizer='system FFmpeg libpocketsphinx with unmodified upstream CMUSphinx data',modelSourceCommit='f20ff1b7a5db64c5e892a798479e20df86e79a35',independentAudioOnlyNotAnApproval=True,
 entries=entries),ensure_ascii=False,indent=2)+'\n')
print(a.out)
