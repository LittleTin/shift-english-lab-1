"""Shared, additive continuous formal audio contract used by authoring and locks."""
from decimal import Decimal,ROUND_HALF_UP
import math
RATE=48000
TOTAL=2700*RATE
def at48(t):
 return int((Decimal(str(t))*RATE).to_integral_value(rounding=ROUND_HALF_UP))
def require(x,msg):
 if not x:raise ValueError(msg)
def geometry(plan,test):
 if 'groupAudio' not in plan:return {}
 m=plan['groupAudio'];fs=plan['frames']; require(type(m)==dict and m and fs,'invalid or empty formal group-audio map')
 require(plan['duration']==2700 and at48(fs[0]['at'])==0,'formal map missing exact exam start/length')
 groups={}
 for i,f in enumerate(fs):
  g=f['groupId']; a=at48(f['at']);b=at48(fs[i+1]['at']) if i+1<len(fs) else TOTAL
  require(b>a and abs(b-a-at48(f['duration']))<=3, 'logical formal frame does not map to positive 48k samples')
  if g not in groups:groups[g]=[]
  elif groups[g][-1]['index']!=i-1:raise ValueError(f'formal group not contiguous: {g}')
  groups[g].append(dict(index=i,start=a,end=b,kind=f['kind'],role=f['role']))
 require(set(groups)==set(m),'formal group audio map must have exactly one entry per formal group')
 result={}
 for g,spans in groups.items():
  ent=m[g];path=f'audio/formal-groups/{test}/{g}.ogg'
  require(type(ent)==dict and set(ent)=={'src','duration'} and ent['src']==path,f'wrong formal URL/fields for {g}')
  start=spans[0]['start'];end=spans[-1]['end'];size=end-start
  require(type(ent['duration']) in (int,float) and math.isfinite(ent['duration']) and abs(ent['duration']-size/RATE)<1e-9,f'wrong sample-exact group duration: {g}')
  result[g]=dict(src=path,seconds=ent['duration'],size=size,start=start,end=end,frames=[dict(**x) | {'start':x['start']-start,'end':x['end']-start} for x in spans])
 require(sum(x['size'] for x in result.values())==TOTAL,'continuous Opus schedule does not total exactly 2700s at 48k')
 return result
def role(row,g):
 return dict(url=row['src'],role='formal-group-audio',group=g,start=0,end=row['seconds'],startSample48k=0,endSample48k=row['size'])
def owner(test,g,path):
 return f'{test}/groups/{g}/media/{path}'
