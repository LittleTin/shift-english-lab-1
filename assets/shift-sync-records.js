(function(root){
'use strict';
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const copy=v=>JSON.parse(JSON.stringify(v));
const sessionOrder=(a,b)=>a.finishedAt-b.finishedAt||a.id.localeCompare(b.id);
const attemptOrder=(a,b)=>a.at-b.at||a.id.localeCompare(b.id);
function key(base,uid){if(!uid)return base;if(!UUID.test(uid))throw Error('Invalid account ID');return base+'::'+uid.toLowerCase()}
function record(s,byId,canonical){
 if(!UUID.test(canonical)||!s||!Array.isArray(s.questionIds)||s.questionIds.length>500) return null;
 const attempts=s.questionIds.map(qid=>byId.get(s.id+':'+qid));
 if(attempts.some(a=>!a))return null;
 const session=copy(s);
 session.id=canonical;
 const canonicalAttempts=attempts.map(a=>({...copy(a),id:canonical+':'+a.questionId}));
 if(canonicalAttempts.filter(a=>a.correct).length!==s.correct||canonicalAttempts.filter(a=>a.selected!==null).length!==s.answered||
 canonicalAttempts.some(a=>(s.answers[a.questionId]||null)!==a.selected))return null;
 const payload={version:1,session,attempts:canonicalAttempts};
 // Leave space for PostgreSQL JSONB's extra separators and formatting.
 if(new TextEncoder().encode(JSON.stringify(payload)).byteLength>850000)return null;
 return {id:canonical,completedAt:new Date(s.finishedAt).toISOString(),payload};
}
function safeRows(target,rows,normalize,uid){
 const sessions=new Map(target.sessions.map(s=>[s.id,s]));
 const attempts=new Map(target.attempts.map(a=>[a.id,a]));
 const sent={...(target.syncSent||{})};
 let imported=0; let conflicts=0; let invalid=0;
 for(const row of rows){
  const p=row.payload; const id=row.id;
  if(row.user_id!==uid)throw Error('Unexpected account in cloud response');
  let valid,candidate;
  try{
   if(!UUID.test(id)||p?.version!==1||p.session?.id!==id||!Array.isArray(p.attempts)||p.attempts.length>500)throw Error();
   valid=normalize({formatVersion:1,sessions:[p.session],attempts:p.attempts});
   candidate=record(valid.sessions[0],new Map(valid.attempts.map(a=>[a.id,a])),id);
   if(!candidate||candidate.payload.attempts.length!==p.attempts.length||Date.parse(row.completed_at)!==valid.sessions[0].finishedAt)throw Error()
  }catch{invalid++;continue}
  if(sessions.has(id)){
   const local=record(sessions.get(id),attempts,id);
   if(!local||!same(local.payload,candidate.payload)){conflicts++;continue}
  }else{
   if(valid.attempts.some(a=>attempts.has(a.id))) { conflicts++; continue }
   sessions.set(id,valid.sessions[0]);for(const a of valid.attempts)attempts.set(a.id,a);
   imported++;
  }
  sent[id]=true;
 }
 const combined=normalize({...target,sessions:[...sessions.values()].sort(sessionOrder),attempts:[...attempts.values()].sort(attemptOrder)});
 // Only commit history fields. In-progress tests, preferences, etc. stay in the current local object.
 return {sessions:combined.sessions,attempts:combined.attempts,stats:combined.stats,syncSent:sent,imported,conflicts,invalid};
}
function same(a,b){
 const sort=x=>Array.isArray(x)?x.map(sort):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,sort(x[k])])):x;
 return JSON.stringify(sort(a))===JSON.stringify(sort(b));
}
function localUnion(live,durable,normalize){
 const sessions=new Map(live.sessions.map(s=>[s.id,s]));
 const attempts=new Map(live.attempts.map(a=>[a.id,a]));
 const sent={...live.syncSent};
 const persistedAttempts=new Map(durable.attempts.map(a=>[a.id,a]));
 let imported=0;
 for(const s of durable.sessions){
  if(!sessions.has(s.id)){
   sessions.set(s.id,s);imported++;
   for(const qid of s.questionIds){
    const k=s.id+':'+qid;
    if(!attempts.has(k)&&persistedAttempts.has(k))attempts.set(k,persistedAttempts.get(k))
   }
   if(durable.syncSent?.[s.id])sent[s.id]=true
  }else if(durable.syncSent?.[s.id]&&!sent[s.id]){
   const a=record(s,persistedAttempts,s.id),b=record(sessions.get(s.id),attempts,s.id);
   if(a&&b&&same(a.payload,b.payload))sent[s.id]=true
  }
 }
 if(!imported)return {syncSent:sent};
 const merged=normalize({...live,sessions:[...sessions.values()].sort(sessionOrder),attempts:[...attempts.values()].sort(attemptOrder)});
 return {sessions:merged.sessions,attempts:merged.attempts,stats:merged.stats,syncSent:sent}
}
root.SHIFT_SYNC_RECORDS=Object.freeze({UUID,key,record,safeRows,same,localUnion});
})(globalThis);
