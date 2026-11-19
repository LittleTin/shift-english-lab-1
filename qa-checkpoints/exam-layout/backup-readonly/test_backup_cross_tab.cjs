'use strict';
const assert=require('node:assert/strict');
const {test}=require('node:test');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const src=fs.readFileSync(process.argv[2]||path.join(__dirname,'../assets/app.js'),'utf8');
const hook="boot().catch(e=>";
assert.equal(src.split(hook).length,2);
const code=src.slice(0,src.indexOf(hook))+`
globalThis.hooks={attach(mode,d,s){storageMode=mode;db=d;state=s},persist,exportBackup,setState(s){state=s},
 getState(){return state},lastBackupTime:typeof lastBackupTime==='function'?lastBackupTime:null};
})();`;
const key='shift-english-lab-v1',meta='shift-english-last-export-v1';
const copy=x=>JSON.parse(JSON.stringify(x));
function fixture(){
 const initial={formatVersion:1,noteDraftEpoch:'initial',attempts:[],stats:{},stars:{},notes:{},sessions:[],settings:{fontScale:1},importedPacks:[],lastBackup:null,
  active:{id:'exam-1',mode:'exam',index:0,answers:{},audioUsed:{g1:{status:'interrupted',frame:0,offset:0}}}};
 const local=new Map([[key,JSON.stringify(initial)]]), writes=[], reads=[];
 let record=copy(initial),readFault=false,localFault=false;
 const db={transaction(store,mode){
  assert.equal(store,'kv');
  const tx={objectStore:()=>({
   get(k){assert.equal(k,'state');reads.push(mode||'readonly');const req={};queueMicrotask(()=>{if(readFault){req.onerror();return}req.result=record===undefined?undefined:copy(record);req.onsuccess()});return req},
   put(s,k){assert.equal(mode,'readwrite');assert.equal(k,'state');queueMicrotask(()=>{record=copy(s);writes.push('state-idb');tx.oncomplete()})}
  })};
  return tx;
 }};
 const localStorage={
  getItem(k){if(localFault&&k===key)throw Error('read blocked');return local.get(k)??null},
  setItem(k,v){writes.push(k);local.set(k,v)}
 };
 const node={addEventListener(){},classList:{add(){},remove(){}}};
 const dom={getElementById:()=>node,addEventListener(){},body:{append(){}},createElement:()=>({click(){},remove(){}})};
 function tab(mode){
  const downloads=[];
  const con={window:{},document:dom,console,localStorage,Blob:class {constructor(chunks){this.payload=JSON.parse(chunks[0])}},
   URL:{createObjectURL(b){downloads.push(b.payload);return 'blob:fixture'},revokeObjectURL(){}},setTimeout(){},clearTimeout(){},setInterval(){}};
  vm.createContext(con);vm.runInContext(code,con);
  con.hooks.attach(mode,db,copy(initial));return {...con.hooks,downloads};
 }
 const advance=tab=>{const s=tab.getState();Object.assign(s.active,{index:3,answers:{q98:'D'},audioUsed:{g1:{status:'interrupted',frame:9,offset:4.75}}});s.notes.q98='preserve me';};
 return {tab,advance,initial,read:mode=>mode==='indexeddb'?record:JSON.parse(local.get(key)),local,writes,reads,
  failRead(mode){if(mode==='indexeddb')readFault=true;else localFault=true}, clear(mode){if(mode==='indexeddb')record=undefined;else local.delete(key)}};
}
for(const mode of ['indexeddb','localstorage']){
 test(mode+': stale B exports latest A state without writing learning records',async()=>{
  const f=fixture(),a=f.tab(mode),b=f.tab(mode);
  f.advance(a);await a.persist();const before=copy(f.read(mode)),count=f.writes.length;
  await b.exportBackup();
  assert.deepEqual(f.read(mode),before);
  assert.deepEqual(f.writes.slice(count),[meta]);
  const backup=b.downloads[0];assert.equal(backup.format,'shift-learning-backup');assert.equal(backup.version,1);
  assert.deepEqual(backup.state.active,before.active);
  assert.equal(backup.state.notes.q98,'preserve me');
  assert.equal(Date.parse(backup.exportedAt),backup.state.lastBackup);
  assert.equal(b.getState().active.index,0,'export does not replace the running tab state');
  assert.equal(f.tab(mode).lastBackupTime(),backup.state.lastBackup);
  if(mode==='indexeddb')assert.deepEqual(f.reads,['readonly']);
 });
 test(mode+': drains previously queued local save before reading',async()=>{
  const f=fixture(),a=f.tab(mode);f.advance(a);
  const pending=a.persist();
  await a.exportBackup();await pending;
  assert.equal(a.downloads[0].state.active.audioUsed.g1.offset,4.75);
  assert.equal(f.writes.filter(x=>x!==meta).length,1);
 });
 test(mode+': a failed durable read never silently exports stale local progress',async()=>{
  const f=fixture(),a=f.tab(mode);f.failRead(mode);
  await assert.rejects(a.exportBackup());assert.deepEqual(a.downloads,[]);assert.deepEqual(f.writes,[]);
 });
}
test('memory backend: unsaved edits still export and no learning state is written',async()=>{
 const f=fixture(),a=f.tab('memory');f.advance(a);await a.exportBackup();
 assert.equal(a.downloads[0].state.active.index,3);assert.deepEqual(f.writes,[meta]);
 assert.equal(f.read('localstorage').active.index,0);
});
test('unwritten durable store still exports in-memory default',async()=>{
 const f=fixture(),a=f.tab('indexeddb');f.clear('indexeddb');
 await a.exportBackup();assert.equal(a.downloads[0].state.active.index,0);
 assert.deepEqual(f.writes,[meta]);
});
