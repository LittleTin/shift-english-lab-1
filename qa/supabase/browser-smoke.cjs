const {chromium}=require('playwright');
const {strict:assert}=require('node:assert');
const host=process.env.SHIFT_QA_ORIGIN||'http://127.0.0.1:18765';
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(host))throw Error('Loopback fixture only');
const A=['alex@shift-fixture.invalid','AlexInitialPass-V1'],B=['blair@shift-fixture.invalid','BlairInitialPass-V1'];
const NEW='BlairReplacementPass-V2';
const out=[];
const ok=s=>{out.push(s); console.log('PASS '+s)};
const action=(p,name)=>p.locator('[data-action="'+name+'"]:visible').first();
const syncText=p=>p.locator('#shift-sync-status');
async function data(p){await action(p,'nav-data').click();await p.locator('#account-sync').waitFor()}
async function submit(p,s,inputs){
 const f=p.locator(s);for(const [k,v] of Object.entries(inputs))await f.locator('[name='+k+']').fill(v);
 await f.locator('button[type=submit]').click();
}
async function signIn(p,[email,password]){
 await submit(p,'#shift-sync-login-form',{email,password});
 await action(p,'sync-logout').waitFor();
}
async function rejectLogin(p,[email,password]){
 const result=p.waitForResponse(r=>{const u=new URL(r.url());return u.origin===host&&u.pathname==='/auth/v1/token'&&u.searchParams.get('grant_type')==='password'});
 await submit(p,'#shift-sync-login-form',{email,password});
 assert.equal((await result).status(),400);
 await p.locator('#shift-sync-login-form').waitFor();assert.equal(await action(p,'sync-logout').count(),0);
}
async function changeBlairPassword(p){
 await action(p,'sync-change-password').click();
 async function put(current,status){
  const result=p.waitForResponse(r=>new URL(r.url()).origin===host&&new URL(r.url()).pathname==='/auth/v1/user'&&r.request().method()==='PUT');
  await submit(p,'#shift-sync-password-form',{currentPassword:current,newPassword:NEW,confirmPassword:NEW});
  assert.equal((await result).status(),status);
 }
 await put('DefinitelyWrongPass-V0',400);
 await p.locator('#shift-sync-password-form').waitFor();
 await put(B[1],200);
}
async function signedOut(p){await action(p,'sync-logout').click();await p.locator('#shift-sync-login-form').waitFor()}
async function snapshot(p){
 return p.evaluate(async()=>{
  const db=await new Promise((yes,no)=>{const r=indexedDB.open('shift-english-lab-v1');r.onsuccess=()=>yes(r.result);r.onerror=no});
  const all=await new Promise((yes,no)=>{const r=db.transaction('kv').objectStore('kv').getAllKeys();r.onsuccess=()=>yes(r.result);r.onerror=no});
  const data=new Map();for(const k of all){const v=await new Promise((yes,no)=>{const r=db.transaction('kv').objectStore('kv').get(k);r.onsuccess=()=>yes(r.result);r.onerror=no});data.set(k,v)}
  const keys=[...data.keys()].filter(k=>k.startsWith('state'));
  return Object.fromEntries(keys.map(k=>[k,{sessions:data.get(k).sessions.map(x=>({id:x.id,total:x.total,correct:x.correct})),attempts:data.get(k).attempts.length,wrong:Object.values(data.get(k).stats).filter(x=>x.needsReview).length,sent:Object.keys(data.get(k).syncSent||{}).length}]))
 });
}
function aBucket(s,n){return Object.entries(s).filter(([k,v])=>k!=='state'&&v.sessions.length===n).at(0)?.[1]}
async function wait(p,predicate){for(let i=0;i<100;i++){const s=await snapshot(p);if(predicate(s))return s;await p.waitForTimeout(50)}throw Error(JSON.stringify(await snapshot(p)))}
async function complete(p){
 await action(p,'nav-home').click();
 await action(p,'quick-reading').click();
 await action(p,'finish-session').click();
 await p.getByRole('button',{name:'Confirm Submission'}).click();
 await p.getByRole('heading',{name:'Session complete. See what you learned.'}).waitFor();
}
(async()=>{
 const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
 try{
  const ca=await b.newContext({viewport:{width:1280,height:830}}),cb=await b.newContext({viewport:{width:390,height:844},isMobile:true,deviceScaleFactor:2});
  const egress=[];
  for(const c of [ca,cb])await c.route('**/*', route=>{const url=route.request().url();const u=new URL(url);
   if(u.origin===host&&u.pathname==='/assets/shift-sync-config.js')return route.fulfill({contentType:'application/javascript',body:"window.SHIFT_SYNC_CONFIG={url:location.origin,publishableKey:'sb_publishable_shift_fixture_only',allowLocal:true};"});
   if(u.origin===host)return route.continue();egress.push(url.split('?')[0]);return route.abort();});
  const a=await ca.newPage(),d=await cb.newPage();
  const errors=[];for(const p of [a,d])p.on('pageerror',x=>errors.push(x.message));
  await Promise.all([a.goto(host),d.goto(host)]);
  await complete(a);
  let s=await wait(a,x=>x.state?.sessions.length===1);
  assert.equal(s.state.sessions[0].correct,0);assert.ok(s.state.attempts>0);ok('guest practice, scoring, IndexedDB and wrong list preserved');
  await data(a);await rejectLogin(a,[A[0],'DefinitelyWrongPass-V0']);await signIn(a,A);await a.waitForFunction(()=>document.querySelector('#shift-sync-status')?.textContent==='Completed history is synced.');
  s=await snapshot(a);assert.equal(s.state.sessions.length,1);assert.equal(aBucket(s,1),undefined);ok('sign-in leaves existing guest answers local by default');
  await action(a,'sync-import-guest').click();await a.getByRole('button',{name:'Copy & Sync'}).click();
  s=await wait(a,x=>aBucket(x,1)?.sent===1);
  assert.equal(aBucket(s,1).wrong,s.state.wrong);ok('explicit guest history copy persists once, score and wrong IDs preserved');
  await data(d);await signIn(d,A);
  s=await wait(d,x=>aBucket(x,1)?.sent===1);assert.equal(s.state.sessions.length,0);
  await action(d,'nav-review').click();await d.waitForFunction(()=>document.querySelectorAll('.record-card').length>0);
  ok('same account on a fresh mobile-size browser context sees wrong review');
  await data(d);await signedOut(d);await signIn(d,B);
  await d.waitForFunction(()=>document.querySelector('#shift-sync-status')?.textContent==='Completed history is synced.');
  s=await snapshot(d);assert.equal(s.state.sessions.length,0);assert.equal(Object.keys(s).filter(x=>x!=='state').length,1);
  await action(d,'nav-review').click();await d.waitForFunction(()=>document.body.innerText.includes('Review & Remember'));
  assert.equal(await d.locator('.record-card').count(),0);ok('sign-out and account switch do not expose the previous account’s wrong answers');
  await data(d);await changeBlairPassword(d);
  if(await action(d,'sync-logout').count())await signedOut(d);
  await d.locator('#shift-sync-login-form').waitFor();
  await rejectLogin(d,B);await signIn(d,[B[0],NEW]);
  await d.waitForFunction(()=>document.querySelector('#shift-sync-status')?.textContent==='Completed history is synced.');
  await action(d,'nav-review').click();assert.equal(await d.locator('.record-card').count(),0);
  ok('wrong current password fails, old login is denied, new login opens only the correct account');
  await data(d);await signedOut(d);await signIn(d,A);
  await d.reload();await data(d);await d.locator('#shift-sync-login-form').waitFor();await signIn(d,A);
  s=await wait(d,x=>aBucket(x,1)?.sent===1);assert.equal(aBucket(s,1).sessions[0].correct,0);ok('token revalidation and same-account reload preserve history');
  const fault=await ca.request.post(host+'/__shift_qa/fault',{headers:{'X-Shift-Fixture-Control':'1'},data:{path:'/rest/v1/rpc/shift_save_completed_session',status:503}});
  assert.ok(fault.ok());await complete(a);await data(a);
  await a.waitForFunction(()=>document.querySelector('#shift-sync-status')?.textContent.includes('Unable to connect.'));
  s=await snapshot(a);assert.equal(aBucket(s,2).sent,1);
  await action(a,'sync-now').click();await wait(a,x=>aBucket(x,2)?.sent===2);
  await action(d,'sync-now').click();s=await wait(d,x=>aBucket(x,2)?.sent===2);assert.equal(aBucket(s,2).attempts,2*aBucket(s,2).sessions[0].total);
  ok('failed cloud write stays local; retry syncs exactly once and pulls on other device');
  assert.deepEqual(errors,[]);assert.deepEqual(egress,[]);ok('no JavaScript errors or external requests in both sessions');
 }finally{await b.close()}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
