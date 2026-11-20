-- SHIFT session sync v1. Run once as the Supabase migration owner.
-- Contract: one immutable completed snapshot and its attempts per (user_id, id).
begin;

create table public.shift_completed_sessions (
    id uuid not null,
    user_id uuid not null default auth.uid(),
    completed_at timestamptz not null,
    payload jsonb not null,
    created_at timestamptz not null default statement_timestamp(),
    primary key (user_id, id),
    constraint shift_completed_at_finite check (isfinite(completed_at)),
    constraint shift_completed_payload_shape check (
        case when jsonb_typeof(payload) = 'object'
                   and payload -> 'version' = '1'::jsonb
                   and jsonb_typeof(payload -> 'session') = 'object'
                   and jsonb_typeof(payload -> 'attempts') = 'array'
        then octet_length(payload::text) <= 1048576
             and jsonb_array_length(payload -> 'attempts') <= 500
             and not jsonb_path_exists(payload, 'strict $.attempts[*] ? (@.type() != "object")')
             and (not ((payload -> 'session') ? 'id')
                  or (payload -> 'session' -> 'id') = to_jsonb(id::text))
        else false end
    )
);

-- Within one authenticated account, paginate in stable descending order; never
-- sort by a mutable/client timestamp or round the server timestamp in a cursor.
create index shift_completed_sessions_owner_created_id_idx
    on public.shift_completed_sessions (user_id, created_at desc, id desc);

alter table public.shift_completed_sessions enable row level security;

-- Undo permissive platform defaults before granting least privilege. The row
-- owner and server timestamp cannot be supplied by an application client.
revoke all privileges on table public.shift_completed_sessions
    from public, anon, authenticated, service_role;
grant select on table public.shift_completed_sessions to authenticated;
grant insert (id, completed_at, payload) on public.shift_completed_sessions to authenticated;

create policy shift_completed_sessions_select_own
    on public.shift_completed_sessions for select to authenticated
    using (user_id = (select auth.uid()));
create policy shift_completed_sessions_insert_own
    on public.shift_completed_sessions for insert to authenticated
    with check (user_id = (select auth.uid()));
-- Intentionally no UPDATE/DELETE policies or privileges.

create function public.shift_save_completed_session(
    p_id uuid,
    p_completed_at timestamptz,
    p_payload jsonb
) returns text
language plpgsql
volatile
security invoker
set search_path = ''
as $fn$
declare
    caller_id uuid := auth.uid();
    saved_completed_at timestamptz;
    saved_payload jsonb;
begin
    if caller_id is null then
        raise exception using errcode = '42501', message = 'Authentication required';
    end if;

    -- Do not update, even on a retry. The unique index handles competing writers.
    insert into public.shift_completed_sessions (id, completed_at, payload)
    values (p_id, p_completed_at, p_payload)
    on conflict (user_id, id) do nothing;
    if found then
        return 'inserted';
    end if;

    -- A separate statement in a VOLATILE function gets a fresh READ COMMITTED
    -- snapshot after ON CONFLICT waits for a concurrent insert to commit.
    select s.completed_at, s.payload into saved_completed_at, saved_payload
      from public.shift_completed_sessions as s
     where s.user_id = caller_id and s.id = p_id;
    if not found then
        -- Do not declare a false conflict if an administrative operation or
        -- nondefault transaction isolation prevented reading the committed row.
        raise exception using errcode = '40001', message = 'Retry the completed-session save';
    end if;
    if saved_completed_at is not distinct from p_completed_at
       and saved_payload is not distinct from p_payload then
        return 'already_exists';
    end if;
    return 'conflict';
end;
$fn$;

revoke all privileges on function public.shift_save_completed_session(uuid, timestamptz, jsonb)
    from public, anon, authenticated, service_role;
grant execute on function public.shift_save_completed_session(uuid, timestamptz, jsonb)
    to authenticated;

comment on table public.shift_completed_sessions is
    'Immutable per-account completed SHIFT session snapshots. Authoritative account and completion metadata are relational columns.';
comment on function public.shift_save_completed_session(uuid, timestamptz, jsonb) is
    'Authenticated idempotent insert. Returns inserted, already_exists on JSONB-equal payload/time, or conflict. Never overwrites.';

commit;
