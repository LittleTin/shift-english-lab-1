const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const src=fs.readFileSync(process.argv[2],'utf8');
const i=src.indexOf('function applyAccountWrite('),j=src.indexOf('// Imported packs are immutable',i);
assert(i>=0&&j>i);
const recordsCode=fs.readFileSync(process.argv[3],'utf8');
const ctx=vm.createContext({blankWorkspace:()=>({formatVersion:1,attempts:[],sessions:[],stats:{}}),normalizeState:x=>x,
 guestEqual:(a,b)=>JSON.stringify(a)===JSON.stringify(b),uid:()=> 'fake-next',TextEncoder});
vm.runInContext(recordsCode,ctx);
vm.runInContext('let records=SHIFT_SYNC_RECORDS;'+src.slice(i,j),ctx);
const apply=vm.runInContext('applyAccountWrite',ctx);
const thisId='93f80dc1-25b9-4abb-b99b-dc7f916e2719',otherId='35c2ddee-3805-4e2c-8bde-8004cf79a09d',qid='t01-q101-r3';
function session(id){return {id,questionIds:[qid],answers:{[qid]:'A'},finishedAt:1000,correct:1,answered:1}}
function attempt(id){return {id:id+':'+qid,questionId:qid,correct:true,selected:'A',at:1000}}
const survey={formatVersion:1,active:{id:'active'},attempts:[attempt(thisId)],sessions:[session(thisId)],stats:{},syncSent:{[thisId]:true}};
const run=(store,next)=>apply(store,null,next,null,true,false);
assert.equal(run(survey,structuredClone(survey)).value,undefined);
assert.equal(run({...survey,syncSent:{}},survey).value.syncSent[thisId],true);
const next={...survey,active:{id:'other'},sessions:[...survey.sessions,session(otherId)],attempts:[...survey.attempts,attempt(otherId)],syncSent:{...survey.syncSent,[otherId]:true}};
const imported=run(survey,next).value;
assert.equal(imported.sessions.length,2);assert.equal(imported.attempts.length,2);assert.equal(imported.active.id,'active');
assert.equal(run(survey,{...survey,syncSent:{}}).value,undefined,'retains existing durability receipt');
assert.equal(run(null,{...survey,active:null}).value.sessions.length,1);
const withConflict={...survey,attempts:[{...attempt(thisId),selected:'C',correct:false}],sessions:[{...session(thisId),answers:{[qid]:'C'},correct:0}]};
assert.equal(run(withConflict,survey).value,undefined);
const noHistory={...survey,syncSent:undefined};
assert.equal(typeof run(noHistory,noHistory).value.syncSent,'object');
const original={...survey,settings:{},stars:{},notes:{},importedPacks:[],accountActiveRevision:'r0'};
const nextActive={...original,active:{id:'different'}};
assert.equal(apply(original,original,nextActive,'bad',false,false).blocked,true);
assert.equal(apply(original,original,nextActive,'r0',false,false).value.active.id,'different');
console.log('PASS 9 history-only idempotence, fresh data, receipt, conflict, initialization and active revision cases');
