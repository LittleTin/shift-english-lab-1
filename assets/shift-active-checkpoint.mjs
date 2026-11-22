/** Owner-scoped active progress protocol. No UI, credentials, or storage here. */
const own=(x,k)=>Object.hasOwn(x,k);
export const CHECKPOINT_FIELDS=Object.freeze(['id','title','mode','questionIds','answers','submitted','startedAt','testIds','contentVersion','index','deadline','examVersion','audioEdition','examPhase','listeningStartedAt','sectionDeadline','listeningRemaining','readingStartsOnReturn','audioUsed','practiceMedia']);
const uuid=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i;
const set=new Set(CHECKPOINT_FIELDS);
const ordered=x=>Array.isArray(x)?x.map(ordered):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,ordered(x[k])])):x;
export const sameCheckpoint=(a,b)=>JSON.stringify(ordered(a))===JSON.stringify(ordered(b));
export function captureCheckpoint(active){
 if(!active)return null;
 if(active.reservedPackConflict||!uuid.test(active.id))throw new Error('checkpoint_unsupported');
 const result={version:1};
 for(const k of CHECKPOINT_FIELDS)if(own(active,k))result[k]=active[k];
 // "started" cannot be autostarted on another device. Keep the exact seek cursor.
 result.audioUsed=Object.fromEntries(Object.entries(result.audioUsed||{}).map(([k,v])=>[k,{...v,status:v.status==='started'?'interrupted':v.status}]));
 const j=JSON.stringify(result);
 if(new TextEncoder().encode(j).byteLength>450000)throw new Error('checkpoint_unsupported');
 return JSON.parse(j);
}
export function parseCheckpoint(raw,normalize) {
 if(raw===null)return null;
 if(!raw||typeof raw!=='object'||Array.isArray(raw)||raw.version!==1||
  !uuid.test(raw.id)||Object.keys(raw).some(k=>k!=='version'&&!set.has(k)))throw new Error('invalid_checkpoint');
 const clean=captureCheckpoint(normalize({formatVersion:1,attempts:[],sessions:[],active:raw}).active);
 if(!sameCheckpoint(raw,clean))throw new Error('invalid_checkpoint');
 return clean;
}
export function checkpointDecision({base,remote,local,inTest=false}){
 if(sameCheckpoint(local,remote.checkpoint))return 'ack';
 if(!base){
  if(local===null&&!inTest)return 'take';
  if(remote.revision===0)return 'push';
  return 'conflict';
 }
 if(remote.revision<base.revision)return 'stale';
 if(remote.revision===base.revision){
  if(!sameCheckpoint(base.checkpoint,remote.checkpoint))return 'stale';
  return 'push';
 }
 if(!inTest&&sameCheckpoint(local,base.checkpoint))return 'take';
 return 'conflict';
}
