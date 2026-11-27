const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const app=fs.readFileSync(process.argv[2],'utf8');
function exact(from,to){
 const a=app.indexOf(from),b=app.indexOf(to,a+from.length);
 assert(a>=0&&b>a);
 return app.slice(a,b);
}
const bulk=exact('async function loadAll(){','function customTest(');
const expiry=exact('function advanceExpiredFormalPhase(){',"document.getElementById('modal').addEventListener('cancel'");
async function test(label,options,expected,err) {
 const s={id:'synthetic',testIds:['test-01','test-01'],questionIds:['q1','q101'],answers:{q101:'A'},reservedPackConflict:options.reserved};
 const state={active:s};
 const pending={listening:false,until:5000,transitioning:false};
 const trace=[];
 let work;
 const context=vm.createContext({state,formalExpiryNotices:new Map([[s,pending]]),guestSubmitPending:false,busy:false,now:()=>options.notYet?4999:5000,
  allTests:()=>[{id:'test-01'},{id:'test-03'}],
  loadTest:async id=>{trace.push(id);if(options.fail===id)throw Error('controlled load failed: '+id);if(options.swap&&id==='test-01')state.active={id:'another'}},
  pinnedFor:()=>options.pinned||null,
  prepareResume:async x=>{assert.equal(s,x);trace.push('verify-versions');if(options.badVersion)throw Error('original version missing');if(options.swapOnVerify)state.active={id:'another'};},
  closeFormalExpiryNotice:()=>trace.push('close'),
  finishSession:async force=>{assert(force);assert.equal(s.answers.q101,'A');trace.push('score');state.active=null;},
  withBusy:fn=>{work=fn()},});
 vm.runInContext(bulk+'\n'+expiry+'\nadvanceExpiredFormalPhase()',context);
 if(err){await assert.rejects(work,err);assert.equal(pending.transitioning,false);assert.equal(state.active,s);}
 else await work;
 assert.deepEqual(trace,expected);
 console.log('PASS '+label);
}
(async()=>{
 await test('unavailable unrelated pack cannot block expiry',{fail:'test-03'},['close','test-01','verify-versions','score']);
 await test('original pinned question versions retained',{pinned:true},['close','test-01','score']);
 await test('required pack failure does not score',{fail:'test-01'},['close','test-01'],/controlled load failed: test-01/);
 await test('unverifiable original versions prevent scoring',{badVersion:true},['close','test-01','verify-versions'],/original version missing/);
 await test('reserved ID conflict does not score',{reserved:true},['close'],/original pack is not available/);
 await test('session swap during pack loading never writes result',{swap:true},['close','test-01']);
 await test('session swap during validation never writes result',{swapOnVerify:true},['close','test-01','verify-versions']);
 await test('notice timing unchanged',{notYet:true},[]);
})().catch(e=>{console.error(e);process.exitCode=1});
