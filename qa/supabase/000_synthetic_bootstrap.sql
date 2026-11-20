-- LOCAL DISPOSABLE DATABASE ONLY. Production uses actual Supabase roles/auth.uid().
create role anon nologin;
create role authenticated nologin;
create role service_role nologin;
create schema auth;
create function auth.uid() returns uuid
language sql stable
return nullif(current_setting('request.jwt.claim.sub', true), '')::uuid;
grant usage on schema auth to authenticated;
grant usage on schema public to anon, authenticated;
grant execute on function auth.uid() to authenticated;
-- Simulate permissive Supabase project defaults, verifying the migration revokes
-- them rather than relying on ordinary PostgreSQL defaults.
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public grant execute on functions to anon, authenticated, service_role;
