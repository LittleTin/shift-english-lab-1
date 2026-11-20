import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import {createShiftSync,combineCompletedSessionId} from '../../assets/shift-sync.mjs';
globalThis.crypto ??= webcrypto;
const url='https://example123.supabase.co';
const key='sb_publishable_AbcdEFGHijklmnop';
const A='00000000-0000-4000-8000-000000000001', B='00000000-0000-4000-8000-000000000002';
const at='2026-11-20T00:00:00Z', email='example@example.test';
const payload={version:1,session:{id:'local'},attempts:[{id:'attempt'}]};
const row = (id=A, created=at,user_id=A) => ({id,user_id,completed_at:at,created_at:created,payload});
const auth=(t='1',id=A,exp=1200)=>({access_token:'access'+t,refresh_token:'refresh'+t,expires_at:exp,user:{id}});
function fixture(opts={}) {
 const calls=[], replies=[];
 return {calls,replies,sync:createShiftSync({url,publishableKey:key,now:()=>1_000_000,...opts,fetchImpl:async (u,o)=>{
  calls.push({u:new URL(u),raw:o,body:o.body===undefined?undefined:JSON.parse(o.body)});
  assert(replies.length,'unexpected request');const r=replies.shift();
  const v=typeof r==='function'?await r():r;
  const [status,body]=Array.isArray(v)?v:[200,v];
  return {ok:status>=200&&status<300,status,json:async()=>body};
 }})};
}
async function login(f) {
 f.replies.push({},auth());
 await f.sync.signInWithOtp(email);
 return await f.sync.verifyOtp(email,'001234');
}
const code = c => e => e.code===c && e.message===c && !e.cause;
test('strict origin and client-only keys', () => {
 const jwt = role => 'eyJhbGciOiJIUzI1NiJ9.'+Buffer.from(JSON.stringify({role})).toString('base64url')+'.synthetic';
 for (const proposed of ['http://example123.supabase.co','https://example123.supabase.co.attacker.test','https://user@example123.supabase.co','https://example123.supabase.co/auth/v1','http://localhost:54321','https://example123.supabase.co/#bogus']) {
  assert.throws(()=>createShiftSync({url:proposed,publishableKey:key}),code('invalid_config'));
 }
 for(const k of ['sb_secret_012345678901234567',jwt('service_role'),jwt('authenticated')]) assert.throws(()=>createShiftSync({url,publishableKey:k}),code('invalid_config'));
 createShiftSync({url,publishableKey:jwt('anon')});
 createShiftSync({url:'http://[::1]:54321',publishableKey:key,allowLocal:true});
});
test('six digit sign-in, access header, RPC and immutable payload body',async()=>{
 const f=fixture(); await assert.rejects(f.sync.verifyOtp(email,'012345'),code('otp_not_requested'));
 f.replies.push({},auth());
 await f.sync.signInWithOtp(' Example@Example.Test ');
 await assert.rejects(f.sync.verifyOtp(email,'12345'),code('invalid_code'));
 const s=await f.sync.verifyOtp(email,'001234');
 assert.deepEqual(s,{userId:A,generation:1}); assert.equal(f.sync.getScope(),s);
 assert.deepEqual(f.calls[0].body,{email,create_user:true,data:{}});
 assert.equal(f.calls[0].u.pathname,'/auth/v1/otp');
 assert.deepEqual(f.calls[1].body,{email,token:'001234',type:'email'});
 assert(!f.calls[0].raw.headers.authorization);
 for(const status of ['inserted','already_exists','conflict']){
  f.replies.push(status);
  assert.equal(await f.sync.saveCompletedSession({id:B,completedAt:at,payload},s),status);
  assert.deepEqual(f.calls.at(-1).body,{p_id:B,p_completed_at:at,p_payload:payload});
  assert.equal(f.calls.at(-1).u.pathname,'/rest/v1/rpc/shift_save_completed_session');
  assert.equal(f.calls.at(-1).raw.headers.authorization,'Bearer access1');
  assert.equal(f.calls.at(-1).raw.redirect,'error');
 }
 f.replies.push('bad response that must not leak');
 await assert.rejects(f.sync.saveCompletedSession({id:B,completedAt:at,payload},s),code('invalid_response'));
 await assert.rejects(f.sync.saveCompletedSession({id:B,completedAt:at,payload},{...s}),code('stale_scope'));
});
test('deterministic keyset keeps microseconds, tie-break id, server-capped page does not lose rows',async()=>{
 const f=fixture(), scope=await login(f);
 const t='2026-11-20T00:00:00.000001+00:00';
 f.replies.push([200,[row(A,t),row(B,t)]],[200,[row(A,'2026-11-20T00:00:00.000002Z')]],[200,[]]);
 const a=await f.sync.listCompletedSessions({scope,limit:10});
 const b=await f.sync.listCompletedSessions({scope,cursor:a.nextCursor});
 const c=await f.sync.listCompletedSessions({scope,cursor:b.nextCursor});
 assert.equal(c.nextCursor,null);
 const p=f.calls[3].u.searchParams;
 assert.equal(p.get('or'),'(created_at.gt.'+t+',and(created_at.eq.'+t+',id.gt.'+B+'))');
 assert.equal(p.get('order'),'created_at.asc,id.asc');
 assert.equal(p.get('user_id'),'eq.'+A);
 f.replies.push([200,[row(A,t,B)]]);
 await assert.rejects(f.sync.listCompletedSessions({scope}),code('invalid_response'));
 f.replies.push([200,[row(B,t),row(A,t)]]);
 await assert.rejects(f.sync.listCompletedSessions({scope}),code('invalid_response'));
 await assert.rejects(f.sync.listCompletedSessions({scope,cursor:{createdAt:t+',x',id:A}}),code('invalid_page'));
});
test('coalesced refresh, 401 retry with fresh access and no remote raw errors', async()=>{
 const f=fixture(),s=await login(f);
 f.replies.push(auth('2'));
 assert.deepEqual(await Promise.all([f.sync.refresh(),f.sync.refresh()]),[s,s]);
 assert.equal(f.calls.filter(c=>c.u.pathname==='/auth/v1/token').length,1);
 assert.equal(f.calls[2].u.searchParams.get('grant_type'),'refresh_token');
 assert.deepEqual(f.calls[2].body,{refresh_token:'refresh1'});
 f.replies.push([401,{message:'sensitive'}],auth('3'),'inserted');
 assert.equal(await f.sync.saveCompletedSession({id:A,completedAt:at,payload},s),'inserted');
 assert.equal(f.calls.at(-1).raw.headers.authorization,'Bearer access3');
 f.replies.push(()=>{throw Error('token from malicious exception')});
 await assert.rejects(f.sync.listCompletedSessions({scope:s}),code('network'));
});
test('late verify and data cannot revive a cleared scope', async()=>{
 const f=fixture();
 f.replies.push({},()=>new Promise(r=>setTimeout(()=>r(auth()),5)));
 await f.sync.signInWithOtp(email);
 const staleLogin=f.sync.verifyOtp(email,'012345'); f.sync.clear();
 await assert.rejects(staleLogin,code('stale_scope')); assert.equal(f.sync.getScope(),null);
 const s=await login(f);
 f.replies.push(()=>new Promise(r=>setTimeout(()=>r([200,[row()]]),5)),[204,null]);
 const data=f.sync.listCompletedSessions({scope:s}); const logout=f.sync.logout();
 assert.equal(f.sync.getScope(),null); await logout; await assert.rejects(data,code('stale_scope'));
 assert.equal(f.calls.at(-1).u.searchParams.get('scope'),'local');
});
test('restore revalidates ownership before exposure; invalid refresh clears scope', async()=>{
 const f=fixture(),s=await login(f), saved=f.sync.exportAuthState();f.sync.clear();
 await assert.rejects(f.sync.restore({...saved,projectOrigin:'https://other.supabase.co'}),code('invalid_auth_state'));
 f.replies.push({id:B});await assert.rejects(f.sync.restore(saved),code('auth_required'));
 assert.equal(f.sync.getScope(),null);
 f.replies.push({id:A});const scope=await f.sync.restore(saved);
 assert.notEqual(scope,s);assert.equal(f.calls.at(-1).u.pathname,'/auth/v1/user');
 f.replies.push([400,{'error_description':'sensitive'}]);
 await assert.rejects(f.sync.refresh(),code('auth_required'));assert.equal(f.sync.getScope(),null);
 f.replies.push(auth('5'));await f.sync.restore({...saved,expiresAt:999});
 assert.equal(f.sync.exportAuthState().refreshToken,'refresh5');
});
test('stable combined ID, distinct components, UUIDv8 variant',async()=>{
 const id=await combineCompletedSessionId('exam','source');
 assert.match(id,/^[0-9a-f]{8}-[0-9a-f]{4}-8[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
 assert.equal(id,await combineCompletedSessionId('exam','source'));
 assert.notEqual(await combineCompletedSessionId('ex','amsource'),await combineCompletedSessionId('exam','source'));
});
