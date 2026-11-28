const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const src=readFileSync(process.argv[2],'utf8');
const a=src.indexOf('async function startSync(full=false)'),b=src.indexOf('\nasync function syncGuestPreview',a);
assert(a>=0&&b>a);
const scope={userId:'same-account-fixture'}, first={id:2,createdAt:2000},delayed={id:1,createdAt:1000};
let visible=[first], clock=1_000_000;
const trace=[];
const context={
 syncOwner:scope.userId,syncEpoch:0,storageMode:'indexeddb',syncOnline:null,syncOnlineFull:false,
 syncPendingFull:null,syncFullResume:null,syncLastFull:0,syncPageCursor:null,navigator:{onLine:true},saveQueue:Promise.resolve(),
 state:{attempts:[],sessions:[],stats:{seen:[]},syncSent:{}},now:()=>clock,readWorkspace:async()=>({}),normalizeState:x=>x,
 route:'quiz',records:{localUnion:()=>({}),safeRows:(s,page)=>({sessions:[],attempts:[],stats:{seen:[...new Set([...s.stats.seen,...page.map(x=>x.id)])].sort()},syncSent:{},conflicts:0,invalid:0,imported:0})},
 persist:async()=>true,setSyncStatus(){},accountMessage:e=>{throw e},
 syncCore:{getScope:()=>scope,listCompletedSessions:async({cursor})=>{
  const rows=visible.filter(r=>r.createdAt>(cursor?.createdAt??0));trace.push({from:cursor?.id??null,rows:rows.map(r=>r.id)});
  return {rows,nextCursor:rows.at(-1)??null};
 }}
};
const run=vm.runInNewContext(src.slice(a,b)+'\nstartSync',context);
(async()=>{
 await run();assert.equal(context.state.stats.seen.join(','),'2');
 visible=[delayed,first];trace.length=0;clock+=60_000;
 await run();assert.equal(context.state.stats.seen.join(','),'2');assert.deepEqual(trace,[{from:2,rows:[]}]);
 const increment=trace.slice();trace.length=0;clock+=15*60_000;
 await run();assert.equal(context.state.stats.seen.join(','),'1,2');assert.deepEqual(trace,[{from:null,rows:[1,2]},{from:2,rows:[]}]);
 console.log(JSON.stringify({scope:'Exact deployed UI sync loop with synthetic visibility and a test storage seam',increment,scheduledReconciliation:trace,preserved:context.state.stats.seen}));
})().catch(e=>{console.error(e);process.exitCode=1});
