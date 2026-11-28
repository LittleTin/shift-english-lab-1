const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const a=require('node:assert/strict');
const source=readFileSync(process.argv[2],'utf8');
const begin=source.indexOf('async function startSync(full=false)');
const end=source.indexOf('\nasync function syncGuestPreview',begin);
a(begin>=0&&end>begin);
const f=source.slice(begin,end);
function workspace(rows,config={}){
 let scope={userId:'owner-a'}, latestDurable=0;
 const trace=[],states=[];
 const c={syncOwner:scope.userId,syncEpoch:0,storageMode:'indexeddb',syncOnline:null,syncOnlineFull:false,syncPendingFull:null,syncFullResume:null,
 navigator:{onLine:true},saveQueue:Promise.resolve(),state:{attempts:[],sessions:[],stats:{},syncSent:{}},syncLastFull:0,syncPageCursor:null,
 now:()=>1_700_000_000_000,syncCore:{getScope:()=>scope,listCompletedSessions:async({scope:expected,cursor,limit})=>{
  a.equal(expected,scope);
  if(cursor)a.equal(cursor.scope,scope);
  const i=cursor?.i??0;trace.push(i);
  const j=Math.min(i+limit,rows);
  return {rows:j>i?[{i,j}]:[],nextCursor:j>i?{i:j,scope}:null};
 }},readWorkspace:async()=>({}),normalizeState:x=>x,records:{localUnion:()=>({}),safeRows:(s,page)=>{
  return {sessions:[],attempts:[],stats:{position:page[0].j},syncSent:{},conflicts:config.conflict&&page[0].i===0?1:0,invalid:0,imported:0};
 }},
 persist:async()=>{if(config.fail===c.state.stats.position)throw Error('simulated local save failure');latestDurable=c.state.stats.position;return true},
 setSyncStatus:s=>states.push(s),accountMessage:e=>e.message,route:'quiz'};
 const run=vm.runInNewContext(f+'\nstartSync',c);
 return {run,c,trace,states,latest:()=>latestDurable,
  replace({owner=c.syncOwner,epoch=c.syncEpoch}={}){c.syncOwner=owner;c.syncEpoch=epoch;scope={userId:owner};}};
}
(async()=>{
 let w=workspace(100001);
 await w.run();
 a.equal(w.latest(),100000);a.equal(w.trace.length,1000);
 a.match(w.states.at(-1),/choose sync now to continue/i);
 await w.run(true);
 a.deepEqual(w.trace.slice(1000),[100000,100001]);
 a.equal(w.latest(),100001);
 a.match(w.states.at(-1),/completed history is synced/i);
 const starting=w.trace.length;
 await w.run(true);
 a.equal(w.trace[starting],0,'an explicit new reconciliation still starts from the beginning');
 console.log('PASS capped full scan resumes on Sync Now and the following full scan restarts at zero');
 w=workspace(100001);
 await w.run();
 await w.run();
 a.deepEqual(w.trace.slice(1000),[100000,100001]);
 console.log('PASS an automatic retry can continue a capped full scan');
 const failures={fail:100001};
 w=workspace(100001,failures);await w.run();await w.run(true);
 a.equal(w.latest(),100000);a.match(w.states.at(-1),/simulated local save failure/);
 failures.fail=null;const n=w.trace.length;await w.run(true);
 a.deepEqual(w.trace.slice(n),[100000,100001]);a.equal(w.latest(),100001);
 console.log('PASS failed page moves no durable continuation');
 w=workspace(100001,{conflict:true});await w.run();await w.run(true);
 a.match(w.states.at(-1),/some records conflict/i);
 console.log('PASS prior chunk conflict is still disclosed');
 for(const profiles of [{owner:'owner-b',epoch:1},{epoch:1},{}]){
  w=workspace(100001);await w.run();w.replace(profiles);await w.run(true);
  a.equal(w.trace[1000],0);
 }
 console.log('PASS owner, workspace generation, or auth-scope replacement restarts without reusing stale cursor');
 w=workspace(99900);await w.run();
 a.match(w.states.at(-1),/completed history is synced/i);
 a.equal(w.trace.length,1000);a.equal(w.c.syncFullResume,null);
 console.log('PASS exact terminal page completes without a continuation');
})().catch(e=>{console.error(e);process.exitCode=1});
