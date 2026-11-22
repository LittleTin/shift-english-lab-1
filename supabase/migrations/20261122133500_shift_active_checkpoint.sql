-- Additive SHIFT unfinished checkpoint migration.
-- The underlying table lives outside the PostgREST-exposed schemas. Expose
-- only a read-only, security-invoker view and a compare-and-swap RPC.
begin;

create schema shift_private;
revoke all on schema shift_private from public, anon, authenticated, service_role;
grant usage on schema shift_private to authenticated;

-- A Supabase anonymous sign-in can carry the authenticated role. Exclude it
-- independently of the project's current anonymous sign-in setting.
create function shift_private.checkpoint_caller()
returns uuid language sql stable security invoker set search_path = ''
return case when auth.jwt() -> 'is_anonymous' = 'true'::jsonb then null::uuid else auth.uid() end;
revoke all on function shift_private.checkpoint_caller() from public, anon, authenticated, service_role;
grant execute on function shift_private.checkpoint_caller() to authenticated;

create function shift_private.checkpoint_safe_id(s text)
returns boolean language sql immutable strict security invoker set search_path = ''
return s ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$'
   and s not in ('constructor','prototype','__proto__');

create function shift_private.checkpoint_number(js jsonb, floor_num numeric, ceiling_num numeric, whole boolean default false)
returns boolean language sql immutable security invoker set search_path = ''
return case when jsonb_typeof(js) = 'number'
  then (js #>> '{}')::numeric between floor_num and ceiling_num
       and (not whole or trunc((js #>> '{}')::numeric) = (js #>> '{}')::numeric)
  else false end;

create function shift_private.checkpoint_valid(js jsonb)
returns boolean
language plpgsql immutable security invoker set search_path = ''
as $fn$
declare
  question_ids text[];
  question_count integer;
  field text;
  v jsonb;
  entry record;
begin
  if js is null then return true; end if;
  if jsonb_typeof(js) <> 'object' or octet_length(js::text) > 1048576 then
    return false;
  end if;
  if not (js ?& array['version','id','title','mode','questionIds','answers','submitted','startedAt','testIds','index'])
     or js - array['version','id','title','mode','questionIds','answers','submitted','startedAt','testIds','index',
       'contentVersion','deadline','examVersion','audioEdition','examPhase','listeningStartedAt','sectionDeadline',
       'listeningRemaining','readingStartsOnReturn','audioUsed','practiceMedia'] <> '{}'::jsonb
     or js -> 'version' <> '1'::jsonb
     or jsonb_typeof(js -> 'id') <> 'string'
     or js ->> 'id' !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
     or coalesce(js ->> 'mode','') not in ('practice','exam')
     or jsonb_typeof(js -> 'mode') <> 'string'
     or jsonb_typeof(js -> 'title') <> 'string'
     or char_length(js ->> 'title') > 250
     or not shift_private.checkpoint_number(js -> 'startedAt', 0, 8639999999999999)
     or jsonb_typeof(js -> 'questionIds') <> 'array'
     or jsonb_typeof(js -> 'testIds') <> 'array'
     or jsonb_typeof(js -> 'answers') <> 'object'
     or jsonb_typeof(js -> 'submitted') <> 'object'
  then return false; end if;

  question_count := jsonb_array_length(js -> 'questionIds');
  if question_count not between 1 and 5000
     or jsonb_array_length(js -> 'testIds') not between 1 and least(question_count, 5000)
     or not shift_private.checkpoint_number(js -> 'index',0,question_count-1,true)
  then return false; end if;
  select array_agg(x #>> '{}') into question_ids
    from jsonb_array_elements(js -> 'questionIds') as args(x)
   where jsonb_typeof(x) = 'string' and shift_private.checkpoint_safe_id(x #>> '{}');
  if coalesce(cardinality(question_ids),0) <> question_count
     or (select count(distinct x) from unnest(question_ids) as ids(x)) <> question_count
     or exists (select from jsonb_array_elements(js -> 'testIds') as args(x)
                 where jsonb_typeof(x) <> 'string' or not shift_private.checkpoint_safe_id(x #>> '{}'))
     or (select count(distinct x) from jsonb_array_elements(js -> 'testIds') as args(x))
       <> jsonb_array_length(js -> 'testIds')
     or exists (select from jsonb_each(js -> 'answers') as a(k,v)
                 where not (a.k = any(question_ids)) or a.v not in ('"A"'::jsonb,'"B"'::jsonb,'"C"'::jsonb,'"D"'::jsonb))
     or exists (select from jsonb_each(js -> 'submitted') as a(k,v)
                 where not (a.k = any(question_ids)) or a.v <> 'true'::jsonb)
  then return false; end if;

  if js ? 'contentVersion' and (jsonb_typeof(js -> 'contentVersion') <> 'string'
       or not shift_private.checkpoint_safe_id(js ->> 'contentVersion')) then return false; end if;
  if js ? 'examVersion' and (js -> 'examVersion') not in ('1'::jsonb,'2'::jsonb) then return false; end if;
  if js ? 'audioEdition' and (js -> 'audioEdition') not in ('"azure-1"'::jsonb,'"toeic-1"'::jsonb) then return false; end if;
  if js ? 'examPhase' and (js -> 'examPhase') not in ('"reading"'::jsonb,'"listening"'::jsonb) then return false; end if;
  if js ? 'readingStartsOnReturn' and jsonb_typeof(js -> 'readingStartsOnReturn') <> 'boolean' then return false; end if;
  if js ? 'listeningRemaining' and not shift_private.checkpoint_number(js -> 'listeningRemaining',0,86400) then return false; end if;
  foreach field in array array['deadline','listeningStartedAt','sectionDeadline'] loop
    v := js -> field;
    if v is not null and v <> 'null'::jsonb and not shift_private.checkpoint_number(v,0,8639999999999999)
    then return false; end if;
  end loop;
  if js ->> 'mode' = 'exam' and not shift_private.checkpoint_number(js -> 'deadline',0,8639999999999999)
  then return false; end if;

  if js ? 'practiceMedia' then
    v := js -> 'practiceMedia';
    if js ->> 'mode' <> 'practice' or jsonb_typeof(v) <> 'object'
       or not (v ?& array['groupId','offset','rate','paused'])
       or v - array['groupId','offset','rate','paused'] <> '{}'::jsonb
       or jsonb_typeof(v -> 'groupId') <> 'string'
       or not shift_private.checkpoint_safe_id(v ->> 'groupId')
       or not shift_private.checkpoint_number(v -> 'offset',0,86400)
       or (v -> 'rate') not in ('0.75'::jsonb, '1'::jsonb, '1.25'::jsonb)
       or jsonb_typeof(v -> 'paused') <> 'boolean'
    then return false; end if;
  end if;

  if js ? 'audioUsed' then
    if jsonb_typeof(js -> 'audioUsed') <> 'object' then return false; end if;
    if (select count(*) from jsonb_each(js -> 'audioUsed')) > question_count then return false; end if;
    for entry in select * from jsonb_each(js -> 'audioUsed') loop
      v := entry.value;
      if not shift_private.checkpoint_safe_id(entry.key) or jsonb_typeof(v) <> 'object'
         or v - array['status','unlockAt','frame','offset'] <> '{}'::jsonb
         or not (v ?& array['status','unlockAt'])
         or (v -> 'status') not in ('"started"'::jsonb,'"ended"'::jsonb,'"interrupted"'::jsonb)
         or not shift_private.checkpoint_number(v -> 'unlockAt',0,8639999999999999)
         or (v ? 'frame') <> (v ? 'offset')
         or (v ? 'frame' and (not shift_private.checkpoint_number(v -> 'frame',0,100000,true)
                         or not shift_private.checkpoint_number(v -> 'offset',0,86400)))
      then return false; end if;
    end loop;
  end if;
  return true;
end;
$fn$;

revoke all on function shift_private.checkpoint_safe_id(text),
  shift_private.checkpoint_number(jsonb,numeric,numeric,boolean),
  shift_private.checkpoint_valid(jsonb) from public, anon, authenticated, service_role;
grant execute on function shift_private.checkpoint_safe_id(text),
  shift_private.checkpoint_number(jsonb,numeric,numeric,boolean),
  shift_private.checkpoint_valid(jsonb) to authenticated;

create table shift_private.active_checkpoint_rows (
  user_id uuid primary key default auth.uid(),
  revision bigint not null check (revision between 1 and 9007199254740991),
  mutation_id uuid not null,
  checkpoint jsonb,
  updated_at timestamptz not null default clock_timestamp(),
  constraint shift_active_checkpoint_shape check (shift_private.checkpoint_valid(checkpoint))
);
alter table shift_private.active_checkpoint_rows enable row level security;
alter table shift_private.active_checkpoint_rows force row level security;
revoke all on shift_private.active_checkpoint_rows from public, anon, authenticated, service_role;
grant select on shift_private.active_checkpoint_rows to authenticated;
grant insert(revision,mutation_id,checkpoint), update(revision,mutation_id,checkpoint,updated_at)
  on shift_private.active_checkpoint_rows to authenticated;
create policy shift_active_checkpoint_select_own on shift_private.active_checkpoint_rows for select to authenticated
  using (user_id = (select shift_private.checkpoint_caller()));
create policy shift_active_checkpoint_insert_own on shift_private.active_checkpoint_rows for insert to authenticated
  with check (user_id = (select shift_private.checkpoint_caller()));
create policy shift_active_checkpoint_update_own on shift_private.active_checkpoint_rows for update to authenticated
  using (user_id = (select shift_private.checkpoint_caller())) with check (user_id = (select shift_private.checkpoint_caller()));

create view public.shift_active_checkpoint with (security_invoker=true) as
  select revision, mutation_id, checkpoint, updated_at from shift_private.active_checkpoint_rows;
revoke all on public.shift_active_checkpoint from public, anon, authenticated, service_role;
grant select on public.shift_active_checkpoint to authenticated;

create function public.shift_write_active_checkpoint(
  p_expected_revision bigint,
  p_mutation_id uuid,
  p_checkpoint jsonb
) returns text
language plpgsql volatile security invoker set search_path = ''
as $fn$
declare
  caller_id uuid := shift_private.checkpoint_caller();
  saved_revision bigint;
  saved_mutation uuid;
  saved_checkpoint jsonb;
begin
  if caller_id is null then
    raise exception using errcode='42501', message='Authentication required';
  end if;
  if p_expected_revision is null or p_expected_revision < 0 or p_expected_revision > 9007199254740990
     or p_mutation_id is null or not shift_private.checkpoint_valid(p_checkpoint)
  then raise exception using errcode='22023', message='Invalid unfinished checkpoint'; end if;

  -- Serialize first writes, compare-and-swap, and completed-session cleanup.
  -- Volatile statements observe the prior holder's commit at READ COMMITTED.
  perform pg_advisory_xact_lock(hashtextextended(caller_id::text,2915838275810049));
  select r.revision,r.mutation_id,r.checkpoint into saved_revision,saved_mutation,saved_checkpoint
    from shift_private.active_checkpoint_rows as r where r.user_id=caller_id;
  if saved_mutation = p_mutation_id then
    if saved_revision = p_expected_revision+1 and saved_checkpoint is not distinct from p_checkpoint
    then return 'already_saved'; end if;
    return 'conflict';
  end if;
  if p_checkpoint is not null and exists (
    select from public.shift_completed_sessions as s
      where s.user_id=caller_id and s.id=(p_checkpoint ->> 'id')::uuid
  ) then return 'already_completed'; end if;
  if coalesce(saved_revision,0) <> p_expected_revision then return 'conflict'; end if;
  if saved_revision is null then
    insert into shift_private.active_checkpoint_rows(revision,mutation_id,checkpoint)
    values (1,p_mutation_id,p_checkpoint);
  else
    update shift_private.active_checkpoint_rows as r
       set revision=saved_revision+1, mutation_id=p_mutation_id,
           checkpoint=p_checkpoint, updated_at=clock_timestamp()
     where r.user_id=caller_id and r.revision=saved_revision;
    if not found then return 'conflict'; end if;
  end if;
  return 'saved';
end;
$fn$;
revoke all on function public.shift_write_active_checkpoint(bigint,uuid,jsonb)
  from public, anon, authenticated, service_role;
grant execute on function public.shift_write_active_checkpoint(bigint,uuid,jsonb) to authenticated;

create function shift_private.clear_checkpoint_after_completion()
returns trigger
language plpgsql volatile security invoker set search_path = ''
as $fn$
declare caller_id uuid := shift_private.checkpoint_caller();
begin
  -- Unprivileged writers of completed records only have owner's INSERT. An
  -- administrative backfill has no end-user JWT and is outside this sync path.
  if caller_id is null or caller_id <> new.user_id then return new; end if;
  perform pg_advisory_xact_lock(hashtextextended(caller_id::text,2915838275810049));
  update shift_private.active_checkpoint_rows as r
     set revision=r.revision+1, mutation_id=gen_random_uuid(), checkpoint=null,
         updated_at=clock_timestamp()
   where r.user_id=caller_id and r.checkpoint ->> 'id' = new.id::text;
  return new;
end;
$fn$;
revoke all on function shift_private.clear_checkpoint_after_completion()
  from public, anon, authenticated, service_role;
create trigger shift_clear_active_after_completion
  after insert on public.shift_completed_sessions for each row
  execute function shift_private.clear_checkpoint_after_completion();

comment on view public.shift_active_checkpoint is
  'Read-only per-authenticated-account unfinished progress, including a versioned SQL NULL tombstone. No row is revision zero.';
comment on function public.shift_write_active_checkpoint(bigint,uuid,jsonb) is
  'JWT-owned compare-and-swap. Returns saved, already_saved, conflict or already_completed. Send SQL NULL to tombstone; reuse mutation ID only to retry the identical write.';
commit;
