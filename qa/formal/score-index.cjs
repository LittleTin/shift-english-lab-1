const fs=require('node:fs'), vm=require('node:vm'),a=require('node:assert/strict');
const base=fs.readFileSync(process.argv[2],'utf8'), candidate=fs.readFileSync(process.argv[3],'utf8');
const {performance}=require('node:perf_hooks');
const take=(s,s1,s2)=>{const f=s.indexOf(s1),z=s.indexOf(s2,f+s1.length);a(f>=0&&z>f);return s.slice(f,z)};
async function simulate(source,n,fail=false){
 const qs=Array.from({length:200},(_,i)=>({id:'q'+i,part:i<100?2:6,testId:'test-01',revision:1,topic:'daily',answer:'C'}));
 const sq=new Map(qs.map(q=>[q.id,q])), s={id:'fresh',title:'synthetic',mode:'exam',startedAt:2,answers:{q1:'A',q99:'C'},submitted:{},questionIds:qs.map(q=>q.id)};
 let idReads=0;
 const attempts=Array.from({length:n},(_,i)=>{const id='previous'+i+':q4';return {get id(){idReads++;return id},questionId:'q4',correct:true}});
 if(n)attempts.splice(0,0,{id:'fresh:q1',questionId:'q1',selected:'A',correct:false});
 const opts={state:{attempts,sessions:[],stats:n?{q1:{attempts:1,wrong:1,streak:0}}:{},active:s},diagnostic:false,guestSubmitPending:false,guestBackupApplying:false,guestRejectedAutoSubmit:null,accountActiveConflict:false,syncOwner:null,sessionQuestion:id=>sq.get(id),
  notify:msg=>{throw Error(msg)},stopAudio(){},now:()=>17,route:'quiz',lastResult:null,resumeEnv:null,
  sessionOutcomes:(s,t)=>{const out=new Map();for(const x of t.attempts)if(x.id===s.id+':'+x.questionId)out.set(x.questionId,x.correct);return out;},
  persist:async (_strict,_history,_mode,target)=>{a(target.active===null);return !fail},
  render(){},window:{scrollTo(){}}};
 const x=vm.createContext(opts);
 const program=take(source,'function recordAnswer(','\nfunction ')+'\n'+take(source,'async function finishSession(force=false){','\nfunction questionGrid()')+'\nfinishSession(true)';
 const start=performance.now();
 await vm.runInContext(program,x);
 const ms=performance.now()-start, reads=idReads;
 if(fail){a.equal(opts.state.active,s);a.equal(opts.state.sessions.length,0);}else{
  a.equal(opts.state.active,null);a.equal(opts.state.sessions[0].answered,2);
  a.equal(opts.state.sessions[0].correct,1);a.equal(opts.state.stats.q1.attempts,1);
  a.equal(opts.state.attempts.length,n+200);a.equal(opts.state.attempts.filter(t=>t.id==='fresh:q1').length,1);
 }
 return {ms,reads,state:JSON.stringify(opts.state)};
}
(async()=>{
 for(const n of [0,2000,20000,100000]){
  const x=await simulate(base,n),y=await simulate(candidate,n);
  a.equal(y.state,x.state);if(n) {a(x.reads>=n*199);a.equal(y.reads,n*2)}
  console.log(JSON.stringify({previousAttempts:n,baselineIdReads:x.reads,candidateIdReads:y.reads,baselineMs:x.ms,candidateMs:y.ms,identical:true}));
 }
 const [failA,failB]=await Promise.all([simulate(base,2000,true),simulate(candidate,2000,true)]);
 a.equal(failA.state,failB.state);console.log('PASS rejected local save leaves original active session and history unchanged');
})().catch(e=>{console.error(e);process.exitCode=1});
