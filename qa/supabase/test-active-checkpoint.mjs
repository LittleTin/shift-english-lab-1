import { readFile } from 'node:fs/promises';
import { strict as assert } from 'node:assert';
import { createRequire } from 'node:module';
const req = createRequire(import.meta.url);
const { PGlite } = req(process.env.SHIFT_PGLITE_PATH || '@electric-sql/pglite');
const base = new URL('../../', import.meta.url);
const db = new PGlite();
const a='00000000-0000-4000-8000-000000000001',b='00000000-0000-4000-8000-000000000002';
const run='10000000-0000-4000-8000-000000000001', other='10000000-0000-4000-8000-000000000002';
const task=(n)=>'20000000-0000-4000-8000-'+String(n).padStart(12,'0');
const shape={version:1,id:run,title:'One empty practice',mode:'practice',questionIds:['t06-q101','t06-q102'],answers:{},submitted:{},startedAt:1795350000000,testIds:['test-06'],index:0,contentVersion:'1.5.0',deadline:null,examVersion:1,audioEdition:'toeic-1',examPhase:'listening',listeningStartedAt:null,sectionDeadline:null,audioUsed:{}};
const set=async (role,user='',claims={})=>{
  await db.exec('RESET ROLE');
  await db.query("select set_config('request.jwt.claim.sub',$1,false)",[user]);
  await db.query("select set_config('request.jwt.claims',$1,false)",[JSON.stringify(claims)]);
  if(role)await db.exec('SET ROLE '+role);
};
const rows=async()=>(await db.query('SELECT * FROM public.shift_active_checkpoint')).rows;
const rpc=async (rev,m,p)=>(await db.query('SELECT public.shift_write_active_checkpoint($1::bigint,$2::uuid,$3::jsonb) AS state',[rev,m,p===null?null:JSON.stringify(p)])).rows[0].state;
const rerror=(p,code)=>assert.rejects(p,e=>e.code===code);
const read=(path,scope=base)=>readFile(new URL(path,scope),'utf8');
const ok=(text)=>console.log('PASS '+text);
try{
  for(const [scope,path] of [
    [base,'qa/supabase/000_synthetic_bootstrap.sql'],[base,'supabase/migrations/20261120000000_shift_completed_sessions.sql'],
    [import.meta.url,'synthetic-active-auth.sql'],[base,'supabase/migrations/20261122133500_shift_active_checkpoint.sql'],[base,'qa/supabase/002_synthetic_rls_test.sql']
  ]) await db.exec(await read(path,scope));
  await set('anon');
  await rerror(rows(),'42501');
  await rerror(rpc(0,task(1),shape),'42501');
  await set('service_role',a);
  await rerror(rows(),'42501');
  await rerror(rpc(0,task(1),shape),'42501');
  await set('authenticated');
  assert.deepEqual(await rows(),[]);
  await rerror(rpc(0,task(1),shape),'42501');
  await set('authenticated',a,{is_anonymous:true});
  assert.deepEqual(await rows(),[]);
  await rerror(rpc(0,task(1),shape),'42501');
  await rerror(db.query('INSERT INTO shift_private.active_checkpoint_rows(revision,mutation_id) VALUES (1,$1)',[task(1)]),'42501');
  ok('No anonymous or service-role ACLs; authenticated without a valid non-anonymous JWT cannot write');
  await set('authenticated',a);
  assert.deepEqual(await rows(),[]);
  assert.equal(await rpc(0,task(1),shape),'saved');
  let [r]=await rows();
  assert.equal(Number(r.revision),1);
  assert.equal(r.mutation_id,task(1));
  assert.deepEqual(r.checkpoint,shape);
  assert.ok(r.updated_at);
  assert.equal(await rpc(0,task(1),shape),'already_saved');
  assert.equal(await rpc(0,task(1),{...shape,title:'different'}),'conflict');
  assert.deepEqual((await rows())[0],r);
  // Even otherwise updatable security-invoker view has only SELECT permission.
  await rerror(db.query("UPDATE public.shift_active_checkpoint SET revision=9"),'42501');
  await rerror(db.query("DELETE FROM shift_private.active_checkpoint_rows"),'42501');
  ok('Zero-answer session saved immediately with revision one; retry is byte-equivalent/idempotent; no direct public write');
  // A and B may test the same session id; ownership comes only from JWT.
  await set('authenticated',b);
  assert.deepEqual(await rows(),[]);
  assert.equal((await db.query('SELECT user_id FROM shift_private.active_checkpoint_rows WHERE user_id=$1',[a])).rows.length,0);
  assert.equal((await db.query('UPDATE shift_private.active_checkpoint_rows SET revision=9 WHERE user_id=$1 RETURNING revision',[a])).rows.length,0);
  await rerror(db.query('INSERT INTO shift_private.active_checkpoint_rows (user_id,revision,mutation_id) VALUES ($1,1,$2)',[a,task(2)]),'42501');
  await rerror(db.query('UPDATE shift_private.active_checkpoint_rows SET user_id=$1',[a]),'42501');
  assert.equal(await rpc(0,task(2),{...shape,title:'Different owner same run id'}),'saved');
  ok('A and B have independent rows even with same checkpoint ID; ownership cannot be injected or changed');
  await set('authenticated',a);
  assert.equal((await rows())[0].checkpoint.title,shape.title);
  const media={groupId:'t06-g021',offset:42.75,rate:1.25,paused:false};
  const left={...shape,index:1,answers:{'t06-q101':'D'},practiceMedia:media};
  const stale={...shape,answers:{'t06-q101':'A'}};
  assert.equal(await rpc(1,task(3),left),'saved');
  assert.equal(await rpc(1,task(4),stale),'conflict');
  assert.equal(await rpc(2,task(3),left),'conflict'); // don't reuse token for new expected revision
  assert.deepEqual((await rows())[0].checkpoint,left);
  assert.equal(await rpc(2,task(4),stale),'saved');
  assert.deepEqual((await rows())[0].checkpoint,stale);
  const exam={...shape,mode:'exam',index:1,examVersion:2,listeningStartedAt:1795350000010,deadline:1795351200000,listeningRemaining:3000.5,audioUsed:{'t06-g001':{status:'interrupted',unlockAt:1795350000020,frame:5,offset:8.42}}};
  assert.equal(await rpc(3,task(5),exam),'saved');
  assert.deepEqual((await rows())[0].checkpoint,exam);
  ok('Two editors on the same base revision: one wins, stale needs a fresh base; timed/audio position stored');
  const long={...shape,questionIds:Array.from({length:4900},(_,i)=>'tq'+String(i).padEnd(93,'x'))};
  long.answers=Object.fromEntries(long.questionIds.map(k=>[k,'A']));
  long.submitted=Object.fromEntries(long.questionIds.map(k=>[k,true]));
  for(const bad of [
    { ...shape,password:'nope' }, { ...shape,notes:{'t06-q101':'nope'} }, { ...shape,refresh_token:'nope' },
    { ...shape,practiceMedia:{...media,src:'https://example.invalid/not-allowed'} },
    { ...shape,practiceMedia:{...media,autoplay:true} },
    { ...shape,practiceMedia:{...media,paused:'false'} },
    { ...shape,practiceMedia:{...media,groupId:'constructor'} },
    { ...shape,practiceMedia:{...media,offset:-1} },
    { ...shape,practiceMedia:{...media,offset:86401} },
    { ...shape,practiceMedia:{...media,rate:1.1} },
    { ...shape,practiceMedia:{groupId:media.groupId,offset:0,rate:1} },
    { ...shape,practiceMedia:null }, { ...exam,practiceMedia:media },
    { ...shape,answers:{bad:'A'} }, { ...shape,answers:{'t06-q101':'E'} },{ ...shape,answers:[1] },
    { ...shape,questionIds:['constructor'] },{ ...shape,questionIds:['x','x'] },{ ...shape,testIds:['test-06','test-06'] },
    { ...shape,testIds:[] },{ ...shape,index:2 },{ ...shape,index:0.1 },{ ...shape,index:'0' },
    { ...shape,mode:'exam' },{ ...shape,deadline:'1795350000000' },{ ...shape,contentVersion:null },
    { ...shape,id:'session-guest' },{ ...shape,submitted:{'t06-q101':false} },
    { ...exam,audioUsed:{'t06-g001':{status:'interrupted',unlockAt:1795350000020,frame:5,password:'nope'}} },
    { ...exam,audioUsed:{'t06-g001':{status:'interrupted',unlockAt:1795350000020,frame:5}} },
    { ...exam,audioUsed:{'t06-g001':{status:'broken',unlockAt:1795350000020}} },
    { ...exam,audioUsed:null },{ ...shape,title:'x'.repeat(251) },long
  ]) await rerror(rpc(4,task(6),bad),'22023');
  await rerror(rpc(-1,task(6),shape),'22023');
  await rerror(rpc(null,task(6),shape),'22023');
  await rerror(rpc(4,null,shape),'22023');
  await rerror(rpc(4,task(6),{}),'22023');
  assert.deepEqual((await rows())[0].checkpoint,exam);
  ok('Strict payload shape, nested allowlists and 1 MiB ceiling reject invalid progress and non-progress fields');
  const history={version:1,session:{id:run},attempts:[]};
  const saved=async(p=history)=>(await db.query('SELECT public.shift_save_completed_session($1::uuid,$2::timestamptz,$3::jsonb) AS result',[p.session.id,'2026-11-22T13:30:00Z',JSON.stringify(p)])).rows[0].result;
  assert.equal(await saved(),'inserted');
  r=(await rows())[0];assert.equal(r.checkpoint,null);assert.equal(Number(r.revision),5);
  assert.notEqual(r.mutation_id,task(5));
  assert.equal(await saved(),'already_exists');
  assert.deepEqual((await rows())[0],r);
  assert.equal(await rpc(4,task(5),exam),'already_completed');
  assert.equal(await rpc(5,task(7),exam),'already_completed');
  assert.equal(await rpc(5,task(7),{...shape,id:other}),'saved');
  assert.equal(await rpc(5,task(8),null),'conflict');
  assert.equal(await rpc(6,task(8),null),'saved');
  assert.equal(await rpc(6,task(8),null),'already_saved');
  assert.equal(await rpc(0,task(9),{...shape,id:other}),'conflict');
  assert.equal((await rows())[0].checkpoint,null);
  await set('authenticated',b);
  assert.equal((await rows())[0].checkpoint.title,'Different owner same run id');
  assert.equal(await rpc(1,task(9),{...exam,title:'B still active'}),'saved');
  // Old client may insert through its original permitted direct history columns.
  await db.query('INSERT INTO public.shift_completed_sessions (id,completed_at,payload) VALUES ($1,$2,$3)',[run,'2026-11-22T13:31:00Z',JSON.stringify(history)]);
  r=(await rows())[0];assert.equal(r.checkpoint,null);assert.equal(Number(r.revision),3);
  ok('Existing history RPC/insert atomically tombstone only matching account/session; stale pushes cannot resurrect it; revisioned clear is idempotent');
  await set(null);
  const conf=(await db.query("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='shift_private.active_checkpoint_rows'::regclass")).rows[0];
  assert.deepEqual(conf,{relrowsecurity:true,relforcerowsecurity:true});
  const view=(await db.query("SELECT reloptions FROM pg_class WHERE oid='public.shift_active_checkpoint'::regclass")).rows[0];
  assert.ok(view.reloptions.includes('security_invoker=true'));
  const f=(await db.query("SELECT prosecdef FROM pg_proc WHERE oid='public.shift_write_active_checkpoint(bigint,uuid,jsonb)'::regprocedure")).rows[0];
  assert.equal(f.prosecdef,false);
  ok('Catalog verifies forced table RLS + security-invoker view and RPC. No prod connection was used.');
}catch(e){console.error(e.message, e.detail ||'',e.where||'');process.exitCode=1}
finally{await db.close()}
