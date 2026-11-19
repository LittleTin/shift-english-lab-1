"""Offline timing guard for already-authored local media; never synthesizes or deploys."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
import wave

SCALE=100000
EXAM=2700*SCALE
ROLES={'passage','question'}

def ticks(x):
    if isinstance(x,bool):raise ValueError('Invalid seconds')
    z=Decimal(str(x))
    if not z.is_finite() or z<0:raise ValueError('Invalid seconds')
    return int((z*SCALE).to_integral_value(rounding=ROUND_HALF_UP))

def sec(x):return x/SCALE

def guarded_asset(root,row):
    relative=row['path']
    if not isinstance(relative,str) or not relative.startswith('audio/') or '\\' in relative or any(x in ('','.','..') for x in relative.split('/')):
        raise ValueError('Unsafe audio path')
    file=root
    for segment in relative.split('/'):
        file=file/segment
        if file.is_symlink():raise ValueError('Symlink audio paths are not supported')
    if sha256(file.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Audio bytes drifted')
    return file

def inspect_new(root,row):
    file=guarded_asset(root,row)
    with wave.open(str(file),'rb') as w:
        count=w.getnframes(); rate=w.getframerate()
        if count<1 or w.getnchannels()!=1 or w.getsampwidth()!=2 or w.getcomptype()!='NONE':
            raise ValueError('New local file must be non-empty verified mono 16-bit PCM WAV')
        if (count,rate)!=(row['frames'],row['sampleRate']):raise ValueError('Measured sample metadata drift')
    return dict(src=row['path'],start=0,end=sec(ticks(Decimal(count)/Decimal(rate))),duration=sec(ticks(Decimal(count)/Decimal(rate))))

def audit(frames):
    cursor=0; seen=set()
    for f in frames:
        if abs(ticks(f['at'])-cursor)>2:raise ValueError('Noncontiguous formal schedule')
        d=ticks(f['duration'])
        if d<1:raise ValueError('Empty frame')
        cursor=ticks(f['at'])+d
        if f['role']=='answer':
            q=f['questionId']
            if q in seen or f['kind']!='silence':raise ValueError('Duplicated or non-silent answer slot')
            seen.add(q)
    if cursor!=EXAM or len(seen)!=100:raise ValueError('Not 100 answer slots and a 2700-second exam')
    return seen

def draft(pack, root, unit):
    """Return a clone and proof. For already-approved F0 recordings only, after exact recheck.
    Never trusts this draft as approval, current text agreement, or audible verification.
    """
    p=deepcopy(pack)
    if p['testId']!=unit['testId']:raise ValueError('Wrong test')
    g=[v for v in p['groups'] if v['id']==unit['groupId']]
    if len(g)!=1:raise ValueError('No unique target group')
    g=g[0]
    frames=p['listeningPlan']['frames']; group=g['id']
    before=[deepcopy(x) for x in frames]
    seen=audit(frames)
    indices=[i for i,f in enumerate(frames) if f.get('groupId')==group]
    if not indices or indices!=list(range(indices[0],indices[-1]+1)):raise ValueError('Noncontiguous targeted group')
    first,last=indices[0],indices[-1]
    left=ticks(frames[first]['at'])
    right=ticks(frames[last+1]['at']) if last+1<len(frames) else EXAM
    changes=unit['changes']; matched=set(); at_formal=[]
    for patch in changes:
        mode=patch['mode']; role=patch['role']; qid=patch.get('questionId')
        k=(mode,role,qid)
        if k in matched:raise ValueError('Duplicate replacement')
        matched.add(k)
        if patch['new']['path']==patch['old']['path']:raise ValueError('Do not replace shared/old audio in place')
        guarded_asset(root,patch['old'])
        new=inspect_new(root,patch['new'])
        old=patch['old']
        if mode=='practice' and role=='passage' and qid is None:
            if (g['audio'],ticks(g['audioStart']),ticks(g['audioEnd']))!=(old['path'],ticks(old['start']),ticks(old['end'])):
                raise ValueError('Practice range drift')
            if 'duration' in g and abs(ticks(g['duration'])-(ticks(g['audioEnd'])-ticks(g['audioStart'])))>2:
                raise ValueError('Practice duration drift')
            g.update(audio=new['src'],audioStart=new['start'],audioEnd=new['end'],duration=new['duration'])
        elif mode=='formal' and role in ROLES and (role=='question')==bool(qid):
            hits=[i for i in indices if frames[i]['role']==role and frames[i].get('questionId')==qid]
            if len(hits)!=1:raise ValueError('No unique formal audio target')
            i=hits[0];f=frames[i]
            if f['kind']!='audio' or (f['src'],ticks(f['start']),ticks(f['end']))!=(old['path'],ticks(old['start']),ticks(old['end'])):
                raise ValueError('Formal range drift')
            f.update(new);at_formal.append(i)
        else:raise ValueError('Only practice/formal passages and actual formal question frames may change')
    if not changes:raise ValueError('No replacements')
    answer=[i for i in indices if frames[i]['role']=='answer']
    if at_formal:
        floor=ticks(unit['minAnswerSec'])
        if not answer or floor<1 or any(ticks(before[i]['duration']) < floor for i in answer):
            raise ValueError('Answer floor exceeds existing slots or is invalid')
        diff=right-left-sum(ticks(frames[i]['duration']) for i in indices)
        q,rest=divmod(abs(diff),len(answer))
        for j,i in enumerate(answer):
            sign=1 if diff>=0 else -1
            next_d=ticks(frames[i]['duration'])+sign*(q+(j<rest))
            if next_d<floor:raise ValueError('Cannot fit group without reducing allowed response time; no speech truncation')
            frames[i]['duration']=sec(next_d)
        z=left
        for i in indices:
            frames[i]['at']=sec(z);z+=ticks(frames[i]['duration'])
        if z!=right:raise ValueError('Group end drift')
    if frames[:first]!=before[:first] or frames[last+1:]!=before[last+1:]:
        raise ValueError('Other groups changed')
    if audit(frames)!=seen:raise ValueError('Timing or scored identity changed')
    return p,dict(status='timing-candidate-not-sound-or-browser-acceptance',testId=p['testId'],groupId=group,firstSec=sec(left),endSec=sec(right),changedFormalIndices=at_formal,answerSeconds=[frames[i]['duration'] for i in answer],formalSeconds=2700)
