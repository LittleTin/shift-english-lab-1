/** Pure browser transport; no storage, timers, external dependencies, or logging. */
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/;
const UTC = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(?:Z|\+00:00)$/;
const obj = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const str = x => typeof x === 'string';
const validTime = x => str(x) && ISO.test(x) && Number.isFinite(Date.parse(x));
const statuses = new Set(['inserted', 'already_exists', 'conflict']);
const token = x => str(x) && x.length > 0 && x.length <= 16000 && /^[\x21-\x7e]+$/.test(x);
function passwordOf(x) {
  if (!str(x) || x.length < 1 || x.length > 1024) fail('invalid_password');
  return x;
}
function emailOf(x) {
  if (!str(x) || x.trim().length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(x.trim())) fail('invalid_email');
  return x.trim().toLowerCase();
}
export class ShiftSyncError extends Error {
  constructor(code) {
    super(code);
    this.name = 'ShiftSyncError';
    this.code = code;
  }
}
function fail(code) { throw new ShiftSyncError(code); }
function uuid(x, code = 'invalid_session') {
  if (!str(x) || !UUID.test(x)) fail(code);
  return x.toLowerCase();
}
function originOf(raw, local) {
  let u;
  try { u = new URL(raw); } catch { fail('invalid_config'); }
  const loopback = local === true && ['localhost', '127.0.0.1', '[::1]'].includes(u.hostname)
    && ['http:', 'https:'].includes(u.protocol);
  const hosted = u.protocol === 'https:' && /^[a-z0-9]+\.supabase\.co$/.test(u.hostname) && !u.port;
  if (!(hosted || loopback) || u.username || u.password || u.pathname !== '/' || u.search || u.hash) fail('invalid_config');
  return u.origin;
}
function publicKey(raw) {
  if (str(raw) && /^sb_publishable_[A-Za-z0-9_-]{12,}$/.test(raw)) return raw;
  if (str(raw) && /^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(raw) && raw.length < 8000) {
    try {
      const part = raw.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      if (JSON.parse(atob(part)).role === 'anon') return raw;
    } catch {} // Do not surface key bytes.
  }
  fail('invalid_config');
}
function stamp(s) {
  const m = str(s) && UTC.exec(s);
  if (!m || !validTime(s)) fail('invalid_response');
  return m[1] + '.' + (m[2] ?? '').padEnd(6, '0');
}
function validPayload(x) {
  return obj(x) && x.version === 1 && obj(x.session) && Array.isArray(x.attempts) && x.attempts.every(obj);
}
export async function combineCompletedSessionId(namespace, sourceId) {
  if (![namespace, sourceId].every(s => str(s) && s.length > 0 && s.length <= 1024)) fail('invalid_id_source');
  let bytes;
  try {
    bytes = new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(
      JSON.stringify(['SHIFT completed session UUID v1', namespace, sourceId]))));
  } catch { fail('crypto_unavailable'); }
  bytes[6] = (bytes[6] & 15) | 128; // RFC 9562 UUIDv8, application-defined SHA-256 mapping.
  bytes[8] = (bytes[8] & 63) | 128;
  const h = Array.from(bytes.slice(0, 16), v => v.toString(16).padStart(2, '0')).join('');
  return [h.slice(0, 8), h.slice(8, 12), h.slice(12, 16), h.slice(16, 20), h.slice(20)].join('-');
}
export function createShiftSync({url, publishableKey, fetchImpl = globalThis.fetch, allowLocal = false,
                                 now = Date.now} = {}) {
  const origin = originOf(url, allowLocal), apikey = publicKey(publishableKey);
  if (typeof fetchImpl !== 'function' || typeof now !== 'function') fail('invalid_config');
  const cursorScopes = new WeakMap();
  let generation = 0, authEpoch = 0, current = null, scope = null, refreshing = null;
  function clear() {
    generation++;
    authEpoch++;
    current = scope = refreshing = null;
  }
  function requireScope(expected) {
    if (!scope || expected !== scope) fail('stale_scope');
    return current;
  }
  function checkEpoch(expected) { if (authEpoch !== expected) fail('stale_scope'); }
  function install(s) {
    current = s;
    scope = Object.freeze({userId: s.userId, generation});
    return scope;
  }
  function authResponse(data) {
    if (!obj(data) || !token(data.access_token) || !token(data.refresh_token) ||
        (data.token_type !== undefined && String(data.token_type).toLowerCase() !== 'bearer')) fail('invalid_response');
    const userId = uuid(data.user?.id, 'invalid_response');
    const expiresAt = data.expires_at === undefined && Number.isFinite(data.expires_in)
      ? Math.floor(now() / 1000) + data.expires_in : data.expires_at;
    if (!Number.isSafeInteger(expiresAt) || expiresAt <= 0) fail('invalid_response');
    return {userId, expiresAt, accessToken: data.access_token, refreshToken: data.refresh_token};
  }
  async function request(path, {method='GET', body, accessToken, empty=false, context} = {}) {
    const headers = {apikey, accept:'application/json'};
    // Legacy gateway expects anon JWT as bearer for Auth entry points; modern project keys
    // are sent as apikey only until a real signed-in access token is available.
    if (accessToken || apikey.startsWith('eyJ')) headers.authorization = 'Bearer ' + (accessToken || apikey);
    let serialized;
    if (body !== undefined) {
      headers['content-type'] = 'application/json';
      try { serialized = JSON.stringify(body); } catch { fail('invalid_session'); }
    }
    let res;
    const controller = new AbortController();
    const timeout = setTimeout(()=>controller.abort(), 15000);
    try {
      res = await fetchImpl(origin + path, {method, headers, body:serialized,
        credentials:'omit', redirect:'error', cache:'no-store', referrerPolicy:'no-referrer', signal:controller.signal});
    } catch { fail('network'); } finally { clearTimeout(timeout); }
    if (!res.ok) {
      // No wire/body/identifier/token escapes; never parse an external error into UI.
      if (res.status === 429) fail('rate_limited');
      if (res.status >= 500) fail('service_unavailable');
      if (context === 'password_login' && [400,401,403,422].includes(res.status)) fail('invalid_credentials');
      if (context === 'password_change' && [400,403,422].includes(res.status)) fail('password_change_failed');
      if (context === 'refresh' && [400,401,403,422].includes(res.status)) fail('auth_required');
      if (res.status === 401) fail('auth_required');
      if (res.status === 403) fail('forbidden');
      fail('request_failed');
    }
    if (empty) return null;
    try { return await res.json(); } catch { fail('invalid_response'); }
  }
  async function signInWithPassword(email, password) {
    email = emailOf(email);
    password = passwordOf(password);
    if (scope) fail('already_signed_in');
    const ticket = ++authEpoch;
    try {
      const data = await request('/auth/v1/token?grant_type=password', {
        method:'POST',body:{email,password},context:'password_login'});
      checkEpoch(ticket);
      const s = authResponse(data);
      generation++;
      return install(s);
    } catch (e) { checkEpoch(ticket); throw e; }
  }
  async function changePassword(currentPassword, newPassword, expected) {
    const s = requireScope(expected);
    const body = {current_password:passwordOf(currentPassword),password:passwordOf(newPassword)};
    const user = await authenticated('/auth/v1/user',{method:'PUT',body,context:'password_change'},expected);
    requireScope(expected);
    if (!obj(user) || uuid(user.id,'invalid_response') !== s.userId) fail('invalid_response');
    return true;
  }
  async function refresh(expected = scope) {
    const old = requireScope(expected);
    if (refreshing) return refreshing;
    const task = (async () => {
      let next;
      try {
        next = authResponse(await request('/auth/v1/token?grant_type=refresh_token',{
          method:'POST',body:{refresh_token:old.refreshToken},context:'refresh'}));
      } catch (e) {
        requireScope(expected);
        if (e.code === 'auth_required') clear();
        throw e;
      }
      requireScope(expected);
      if (next.userId !== old.userId) { clear(); fail('auth_required'); }
      current = next;
      return expected;
    })();
    refreshing = task;
    try { return await task; } finally { if (refreshing === task) refreshing = null; }
  }
  async function restore(saved) {
    if (scope) fail('already_signed_in');
    if (!obj(saved) || saved.projectOrigin !== origin || !token(saved.accessToken) || !token(saved.refreshToken) ||
        !Number.isSafeInteger(saved.expiresAt) || saved.expiresAt <= 0) fail('invalid_auth_state');
    const userId = uuid(saved.userId, 'invalid_auth_state');
    const ticket = ++authEpoch;
    try {
      let s;
      if (saved.expiresAt <= now() / 1000 + 30) {
        s = authResponse(await request('/auth/v1/token?grant_type=refresh_token',{
          method:'POST',body:{refresh_token:saved.refreshToken},context:'refresh'}));
        if (s.userId !== userId) fail('auth_required');
      } else {
        const data = await request('/auth/v1/user',{accessToken:saved.accessToken});
        if (uuid(data?.id,'invalid_response') !== userId) fail('auth_required');
        s = {userId, expiresAt:saved.expiresAt, accessToken:saved.accessToken, refreshToken:saved.refreshToken};
      }
      checkEpoch(ticket);
      generation++;
      return install(s);
    } catch (e) { checkEpoch(ticket); throw e; }
  }
  function exportAuthState() { return current ? {...current,projectOrigin:origin} : null; }
  async function logout() {
    const old = current;
    clear();
    const ticket = authEpoch;
    if (!old) return;
    try {
      await request('/auth/v1/logout?scope=local',{method:'POST',accessToken:old.accessToken,empty:true});
      checkEpoch(ticket);
    } catch (e) { checkEpoch(ticket); throw e; }
  }
  async function authenticated(path, opts, expected) {
    let s = requireScope(expected);
    if (s.expiresAt <= now()/1000 + 30) await refresh(expected);
    s = requireScope(expected);
    for (let pass=0; pass<2; pass++) {
      try {
        const value = await request(path,{...opts,accessToken:s.accessToken});
        requireScope(expected);
        return value;
      } catch (e) {
        const next = requireScope(expected);
        if (e.code !== 'auth_required' || pass) throw e;
        if (next === s) await refresh(expected);
        s = requireScope(expected);
      }
    }
  }
  async function saveCompletedSession({id,completedAt,payload} = {}, expected) {
    requireScope(expected);
    const p_id = uuid(id);
    if (!validTime(completedAt) || !validPayload(payload)) fail('invalid_session');
    // Snapshot immediately: callers may mutate the original while an access refresh runs.
    let p_payload;
    try { p_payload = JSON.parse(JSON.stringify(payload)); } catch { fail('invalid_session'); }
    if (!validPayload(p_payload)) fail('invalid_session');
    const status = await authenticated('/rest/v1/rpc/shift_save_completed_session',{
      method:'POST',body:{p_id,p_completed_at:completedAt,p_payload}},expected);
    requireScope(expected);
    if (!statuses.has(status)) fail('invalid_response');
    return status;
  }
  async function listCompletedSessions({scope:expected,cursor=null,limit=100} = {}) {
    const s = requireScope(expected);
    if (!Number.isInteger(limit) || limit<1 || limit>500) fail('invalid_page');
    const params = new URLSearchParams({select:'id,user_id,completed_at,created_at,payload',
      user_id:'eq.'+s.userId,order:'created_at.asc,id.asc',limit:String(limit)});
    let prior = '';
    if (cursor !== null) {
      try {
        if (!obj(cursor) || cursorScopes.get(cursor) !== expected) fail('invalid_page');
        const id = uuid(cursor.id,'invalid_page');
        prior = stamp(cursor.createdAt) + id;
        params.set('or','(created_at.gt.'+cursor.createdAt+',and(created_at.eq.'+cursor.createdAt+',id.gt.'+id+'))');
      } catch { fail('invalid_page'); }
    }
    const rows = await authenticated('/rest/v1/shift_completed_sessions?'+params,{},expected);
    requireScope(expected);
    if (!Array.isArray(rows) || rows.length>limit) fail('invalid_response');
    for (const r of rows) {
      if (!obj(r) || r.user_id !== s.userId || !validTime(r.completed_at) || !validPayload(r.payload)) fail('invalid_response');
      const order = stamp(r.created_at) + uuid(r.id,'invalid_response');
      if (order <= prior) fail('invalid_response');
      prior = order;
    }
    const last = rows.at(-1);
    const nextCursor = last ? Object.freeze({createdAt:last.created_at,id:last.id}) : null;
    if (nextCursor) cursorScopes.set(nextCursor,expected);
    return {rows,nextCursor};
  }
  return Object.freeze({signInWithPassword,changePassword,refresh,logout,getScope:()=>scope,clear,restore,
    exportAuthState,saveCompletedSession,listCompletedSessions});
}
