-- Run in fresh disposable DB after 000_synthetic_bootstrap.sql + migration.
-- Fail-closed assertions with real non-owner roles; successful script rolls data back.
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
do $test$
declare
  i constant uuid := 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  t constant timestamptz := '2026-01-01T12:00:00.123456Z';
  p constant jsonb := '{"version":1,"session":{"id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"},"attempts":[{"questionId":"synthetic-001"}]}';
begin
  if public.shift_save_completed_session(i,t,p) is distinct from 'inserted'
  then raise exception 'A insert failed'; end if;
  if public.shift_save_completed_session(i,t,'{"attempts":[{"questionId":"synthetic-001"}],"session":{"id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"},"version":1}') is distinct from 'already_exists'
  then raise exception 'A key-order-insensitive retry failed'; end if;
  if public.shift_save_completed_session(i,t+'1 microsecond',p) is distinct from 'conflict'
     or public.shift_save_completed_session(i,t,jsonb_set(p,'{attempts}','[]')) is distinct from 'conflict'
  then raise exception 'A conflict failed'; end if;
  if (select count(*) from public.shift_completed_sessions) <> 1
     or not exists(select 1 from public.shift_completed_sessions where id=i and completed_at=t and payload=p and user_id=auth.uid() and created_at >= transaction_timestamp())
  then raise exception 'A row changed'; end if;
  begin
    insert into public.shift_completed_sessions(id,user_id,completed_at,payload)
      values(i,'22222222-2222-4222-8222-222222222222',t,p);
    raise exception 'A could forge owner'; exception when insufficient_privilege then null;
  end;
  begin
    insert into public.shift_completed_sessions(id,created_at,completed_at,payload)
      values(i,t,t,p);
    raise exception 'A could forge creation clock'; exception when insufficient_privilege then null;
  end;
  begin
    update public.shift_completed_sessions set payload='{}';
    raise exception 'A could update'; exception when insufficient_privilege then null;
  end;
  begin
    delete from public.shift_completed_sessions;
    raise exception 'A could delete'; exception when insufficient_privilege then null;
  end;
  begin
    truncate public.shift_completed_sessions;
    raise exception 'A could truncate'; exception when insufficient_privilege then null;
  end;
end;
$test$;

select set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
do $test$
declare
  i constant uuid := 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  t constant timestamptz := '2026-01-01T12:00:00Z';
  p constant jsonb := '{"version":1,"session":{},"attempts":[{"questionId":"synthetic-002"}]}';
  bad jsonb;
begin
  if exists(select 1 from public.shift_completed_sessions where id=i)
  then raise exception 'B can read A'; end if;
  if public.shift_save_completed_session(i,t,p) is distinct from 'inserted'
  then raise exception 'Same id across users is not independent'; end if;
  if (select count(*) from public.shift_completed_sessions) <> 1
     or not exists(select 1 from public.shift_completed_sessions where id=i and payload=p and user_id=auth.uid())
  then raise exception 'B sees wrong row'; end if;
  -- Valid canonical complete test may contain 200 attempts.
  insert into public.shift_completed_sessions(id,completed_at,payload)
    values ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',t,
      jsonb_set(p,'{attempts}',(select jsonb_agg(jsonb_build_object('n',n)) from generate_series(1,200) n))),
    ('cccccccc-cccc-4ccc-8ccc-cccccccccccc',t,p);
  if (select array_agg(id order by created_at desc,id desc) from public.shift_completed_sessions where id<>i)
     <> array['cccccccc-cccc-4ccc-8ccc-cccccccccccc'::uuid,'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'::uuid]
  then raise exception 'Tie ordering failed'; end if;
  foreach bad in array array[
    '{"version":1,"session":{}}'::jsonb,
    '{"version":1,"session":{},"attempts":[[]]}'::jsonb,
    '{"version":1,"session":{"id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"},"attempts":[]}'::jsonb,
    '{"version":2,"session":{},"attempts":[]}'::jsonb,
    jsonb_set(p,'{session}',jsonb_build_object('n',repeat('x',1048576))),
    jsonb_set(p,'{attempts}',(select jsonb_agg('{}'::jsonb) from generate_series(1,501)))
  ] loop
    begin
      perform public.shift_save_completed_session('dddddddd-dddd-4ddd-8ddd-dddddddddddd',t,bad);
      raise exception 'Invalid payload accepted: %', left(bad::text,140); exception when check_violation then null;
    end;
  end loop;
  if exists(select 1 from public.shift_completed_sessions where id='dddddddd-dddd-4ddd-8ddd-dddddddddddd')
  then raise exception 'Invalid insert was not atomic'; end if;
end;
$test$;
select set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
do $test$
begin
  if (select count(*) from public.shift_completed_sessions) <> 1
     or not exists(select 1 from public.shift_completed_sessions where payload #>> '{attempts,0,questionId}' = 'synthetic-001')
  then raise exception 'A can see B or B overwrote A'; end if;
end;
$test$;

select set_config('request.jwt.claim.sub','',true);
do $test$
begin
  if exists(select 1 from public.shift_completed_sessions) then raise exception 'No-sub read leaked'; end if;
  begin
    perform public.shift_save_completed_session('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',now(),'{}');
    raise exception 'No-sub save succeeded'; exception when insufficient_privilege then null;
  end;
end;
$test$;

set local role anon;
do $test$
begin
  begin
    perform id from public.shift_completed_sessions;
    raise exception 'Anon read succeeded'; exception when insufficient_privilege then null;
  end;
  begin
    perform public.shift_save_completed_session('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',now(),'{}');
    raise exception 'Anon RPC succeeded'; exception when insufficient_privilege then null;
  end;
end;
$test$;
select 'PASS: synthetic two-user isolation, idempotence, bounds, atomicity and least privilege' as result;
rollback;
