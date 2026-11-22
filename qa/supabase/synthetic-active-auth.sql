-- LOCAL TEST ONLY; hosted Supabase already provides auth.jwt().
create function auth.jwt() returns jsonb
language sql stable
return coalesce(nullif(current_setting('request.jwt.claims',true), '')::jsonb, '{}'::jsonb);
grant execute on function auth.jwt() to authenticated;
