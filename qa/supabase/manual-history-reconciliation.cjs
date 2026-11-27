'use strict';
// Usage: node manual-history-reconciliation.cjs path/to/assets/app.js
// Uses only a synthetic in-memory transport and test rows; no service credentials.
const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const src=fs.readFileSync(process.argv[2],'utf8');
const beg=src.indexOf('async function startSync(full=false)');
const end=src.indexOf('\nasync function syncGuestPreview',beg);
assert(beg>=0&&end>beg,'Could not locate startSync in app.js');
const fn=src.slice(beg,end);
const watchdog=setTimeout(()=>{console.error('Timed out waiting for synthetic sync');process.exit(1);},5000);
const fullTrace=[0,2];
function fixture({full=false,fail=false}={}){
 const rows=[{id:1},{id:2}],trace=[], statuses=[];let enter,release,block=true;const entered=new Promise(r=>enter=r),gate=new Promise(r=>release=r);
 const x={syncOwner:'a',syncEpoch:4,storageMode:'indexeddb',navigator:{onLine:true},syncOnline:null,syncOnlineFull:false,syncPendingFull:null,syncLastFull:full?0:900_000,syncPageCursor:rows.at(-1),
  saveQueue:Promise.resolve(),now:()=>1_000_000,state:{sessions:[],attempts:[],stats:{},syncSent:{}},records:{localUnion:()=>({}),safeRows:current=>({...current,conflicts:0,invalid:0,imported:0})},
  syncCore:{getScope:()=>({userId:x.syncOwner}),listCompletedSessions:async({cursor,limit})=>{
   trace.push(cursor?.id??0);if(block){block=false;enter();await gate;if(fail)throw Error('network failed')}
   const rs=rows.slice(cursor?.id??0,(cursor?.id??0)+limit);return {rows:rs,nextCursor:rs.at(-1)??null};
  }},readWorkspace:async()=>({}),normalizeState:x=>x,persist:async()=>true,setSyncStatus:s=>statuses.push(s),accountMessage:e=>e.message};
 const run=vm.runInNewContext(fn+'\nstartSync',x);
 return {x,trace,statuses,entered,release,run};
}
(async()=>{
 const covered=[];
 for(const [name,options,clicks,beforeFinish,expectedTrace,expectedStatus] of [
 ['overlapping manual clicks coalesce',{},4,()=>{},[2,...fullTrace],'Completed history is synced.'],
 ['manual joins background full',{full:true},3,()=>{},fullTrace,'Completed history is synced.'],
 ['works after incremental request fails',{fail:true},1,()=>{},[2,...fullTrace],'Completed history is synced.'],
 ['queue cancelled on different account',{},2,x=>{x.syncOwner='b';x.syncEpoch++;x.syncOnline=x.syncPendingFull=null;x.syncOnlineFull=false},[2],'Syncing completed history…'],
 ['queue cancelled on same account new epoch',{},2,x=>{x.syncEpoch++;x.syncOnline=x.syncPendingFull=null;x.syncOnlineFull=false},[2],'Syncing completed history…'],
 ['queue cancels on logout',{},2,x=>{x.syncOwner=null;x.syncEpoch++;x.syncOnline=x.syncPendingFull=null;x.syncOnlineFull=false},[2],'Syncing completed history…'],
 ['offline reuses existing status and sends nothing further',{},2,x=>{x.navigator.onLine=false},[2],'Offline. Completed records will sync after reconnecting.'],
 ['ordinary incremental unchanged',{},0,()=>{},[2],'Completed history is synced.'],
 ]){
  const f=fixture(options);const pending=[f.run()];await f.entered;
  for(let i=0;i<clicks;i++)pending.push(f.run(true));
  beforeFinish(f.x);
  f.release();await Promise.all(pending);
  assert.deepEqual(f.trace,expectedTrace,name);
  assert.equal(f.statuses.at(-1),expectedStatus,name);
  assert.equal(f.x.syncPendingFull,null,name);
  assert.equal(f.x.syncOnline,null,name);
  covered.push({name,trace:f.trace});
 }
 console.log(JSON.stringify({fixture:'synthetic Node isolated exact function',covered},null,2));
})().catch(error=>{console.error(error);process.exitCode=1}).finally(()=>clearTimeout(watchdog));
