'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const f=process.argv[2],src=fs.readFileSync(f,'utf8');
const snippet=src.slice(src.indexOf('const LISTENING_TAB_KEY'),src.indexOf("window.addEventListener?.('pagehide',saveListeningTabPoint);"));
function ctx(){
 const db={id:'x',startedAt:100,contentVersion:'1.4.2',audioEdition:'toeic-1',index:0,questionIds:['q'],audioUsed:{g:{status:'started',frame:0,offset:2}},answers:{q:'B'},notes:{q:'keep'}};
 const core={
 state:{active:db},formalRunning:true,route:'quiz',listening:()=>true,currentAudioGroup:'g',
 captureFormal:()=>{db.audioUsed.g.offset=3.75},sessionGroup:()=>({id:'g'}),sessionQuestion:()=>({groupId:'g'}),
 groupFrames:()=>[{kind:'audio',role:'passage',src:'a.wav',start:0,end:10,duration:10}],resumePosition:u=>u,
 sessionStorage:{map:new Map,setItem(k,v){this.map.set(k,v)},getItem(k){return this.map.get(k)||null},removeItem(k){this.map.delete(k)}}
 };
 const c=vm.createContext(core);vm.runInContext(snippet+'\nthis.api={saveListeningTabPoint,restoreListeningTabPoint};',c);
 return {db,c,api:core.api, key:'shift-formal-listening-refresh-v1'};
}
test('newer tab-local exact frame recovers offset and does not change answers or notes',()=>{
 const {db,c,api,key}=ctx();api.saveListeningTabPoint();db.audioUsed.g.offset=2;
 assert.equal(api.restoreListeningTabPoint(db),true);assert.equal(db.audioUsed.g.offset,3.75);assert.equal(db.audioUsed.g.status,'interrupted');
 assert.equal(db.answers.q,'B');assert.equal(db.notes.q,'keep');assert.equal(c.sessionStorage.getItem(key),null);
});
test('stale point, different active session or revision and changed source are rejected',()=>{
 for(const change of [d=>d.audioUsed.g.offset=5,d=>d.id='other',d=>d.contentVersion='1.4.3',d=>d.audioUsed.g.status='ended',(_d,c)=>c.groupFrames=()=>[{kind:'audio',role:'passage',src:'other.wav',start:0,end:10,duration:10}]]){
  const {db,c,api}=ctx();api.saveListeningTabPoint();change(db,c);assert.equal(api.restoreListeningTabPoint(db),false);
 }
});
test('storage unavailable preserves durable fallback',()=>{
 const {db,c,api}=ctx();c.sessionStorage={getItem(){throw new Error('blocked')},setItem(){throw new Error('blocked')}};
 assert.doesNotThrow(()=>api.saveListeningTabPoint());assert.equal(api.restoreListeningTabPoint(db),false);
});
