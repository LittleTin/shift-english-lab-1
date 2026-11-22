#!/usr/bin/env python3
"""Disposable SHIFT QA only. No provider, disk data, or non-loopback binding."""
import argparse
import json
import mimetypes
import re
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

KEY = "sb_publishable_shift_fixture_only"
ACCOUNTS = {f"{name}@shift-fixture.invalid": (f"{digit*8}-{digit*4}-4{digit*3}-8{digit*3}-{digit*12}", pin)
            for name,digit,pin in [("alex","1","AlexInitialPass-V1"),("blair","2","BlairInitialPass-V1")]}
TABLE = "/rest/v1/shift_completed_sessions"
RPC = "/rest/v1/rpc/shift_save_completed_session"
AUTH = "/auth/v1/"
FAULT = "/__shift_qa/fault"
COLUMNS = ("id","user_id","completed_at","created_at","payload")
CURSOR = re.compile(r"\(created_at\.gt\.([^,]+),and\(created_at\.eq\.([^,]+),id\.gt\.([0-9a-f-]+)\)\)")
CHUNK = 1_048_576

class HttpError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code

def stamp(v):
    if not isinstance(v, str):
        raise ValueError("timestamp")
    d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("timezone required")
    return d.astimezone(timezone.utc)

def iso(d):
    return d.isoformat(timespec="microseconds").replace("+00:00","Z")

def payload_equal(a,b):
    # JSONB treats numeric spellings as equal but booleans are not numbers.
    if type(a) in (int,float) and type(b) in (int,float):
        return a == b
    if type(a) != type(b):
        return False
    if isinstance(a,list):
        return len(a)==len(b) and all(payload_equal(x,y) for x,y in zip(a,b))
    if isinstance(a,dict):
        return a.keys()==b.keys() and all(payload_equal(a[k],b[k]) for k in a)
    return a == b

class Fixture:
    def __init__(self, ttl=120, clock=time.time):
        self.ttl,self.clock=ttl,clock
        self.lock=threading.RLock()
        self.passwords={email: pair[1] for email,pair in ACCOUNTS.items()}
        self.access={}
        self.refresh={}
        self.rows={}
        self.faults={}

    def issue(self, email):
        uid,_=ACCOUNTS[email]
        access="shift-qa-access-"+secrets.token_hex(20)
        refresh="shift-qa-refresh-"+secrets.token_hex(20)
        expiry=int(self.clock())+self.ttl
        self.access[access]=(email,expiry,refresh)
        self.refresh[refresh]=(email,access)
        return dict(access_token=access,refresh_token=refresh,expires_at=expiry,
                    expires_in=self.ttl,token_type="bearer",
                    user=dict(id=uid,email=email,aud="authenticated",role="authenticated"))

    def revoke(self, access):
        old=self.access.pop(access,None)
        if old:
            self.refresh.pop(old[2],None)

    def owner(self, bearer, allow_expired=False):
        s=self.access.get(bearer)
        if not s or (not allow_expired and self.clock()>=s[1]):
            raise HttpError(401,"auth_required")
        return ACCOUNTS[s[0]][0]

    def api(self, method, path, q, body, headers):
        with self.lock:
            return self._api(method,path,q,body,headers)

    def _api(self, method, path, q, body, headers):
        if path==FAULT:
            if method!="POST" or headers.get("x-shift-fixture-control")!="1":
                raise HttpError(404,"not_found")
            dest,status=body.get("path"),body.get("status")
            if dest not in (TABLE,RPC,AUTH+"token",AUTH+"user",AUTH+"logout") or status not in (401,429,503):
                raise HttpError(400,"invalid_fault")
            self.faults[dest]=status   # one-shot, no credential or attempt contents reported
            return 200,{"queued":True}
        if headers.get("apikey")!=KEY:
            raise HttpError(401,"fixture_key_required")
        if path in self.faults:
            raise HttpError(self.faults.pop(path),"injected_fixture_fault")
        bearer=headers.get("authorization","").removeprefix("Bearer ")
        if method=="POST" and path==AUTH+"token" and q.get("grant_type")==["password"]:
            email=body.get("email")
            password=body.get("password")
            if not isinstance(email,str) or not isinstance(password,str) or self.passwords.get(email)!=password:
                raise HttpError(400,"invalid_credentials")
            return 200,self.issue(email)
        if method=="PUT" and path==AUTH+"user":
            self.owner(bearer)
            email=self.access[bearer][0]
            if body.get("current_password")!=self.passwords[email]:
                raise HttpError(400,"invalid_credentials")
            fresh=body.get("password")
            if not isinstance(fresh,str) or len(fresh)<12 or fresh==self.passwords[email]:
                raise HttpError(422,"weak_password")
            self.passwords[email]=fresh
            return 200,dict(id=ACCOUNTS[email][0],email=email,aud="authenticated",role="authenticated")
        if method=="POST" and path==AUTH+"token":
            entry=self.refresh.get(body.get("refresh_token"))
            if not entry or q.get("grant_type")!=["refresh_token"]:
                raise HttpError(400,"invalid_grant")
            self.revoke(entry[1])
            return 200,self.issue(entry[0])
        if method=="POST" and path==AUTH+"logout":
            self.owner(bearer,allow_expired=True)
            self.revoke(bearer)
            return 204,None
        if path not in (TABLE,RPC):
            raise HttpError(404,"not_found")
        owner=self.owner(bearer)
        if path==RPC and method=="POST":
            rid=str(uuid.UUID(body["p_id"]))
            ended=iso(stamp(body["p_completed_at"]))
            payload=body["p_payload"]
            if not (isinstance(payload,dict) and type(payload.get("version")) is int and payload["version"]==1
                    and isinstance(payload.get("session"),dict) and isinstance(payload.get("attempts"),list)
                    and len(payload["attempts"])<=500 and all(isinstance(x,dict) for x in payload["attempts"])
                    and len(json.dumps(payload,ensure_ascii=False).encode())<=CHUNK):
                raise HttpError(400,"invalid_payload")
            existing=self.rows.get((owner,rid))
            if existing:
                same=existing["completed_at"]==ended and payload_equal(existing["payload"],payload)
                return 200,"already_exists" if same else "conflict"
            created=iso(datetime.fromtimestamp(self.clock(),timezone.utc))
            self.rows[(owner,rid)]=dict(id=rid,user_id=owner,completed_at=ended,created_at=created,payload=payload)
            return 200,"inserted"
        if path!=TABLE or method!="GET":
            raise HttpError(405,"method_not_allowed")
        if set(q)-{"select","user_id","order","limit","or","created_at","id"} or any(len(v)!=1 for v in q.values()):
            raise HttpError(400,"unsupported_filter")
        f={k:v[0] for k,v in q.items()}
        if "user_id" in f and not f["user_id"].startswith("eq."):
            raise HttpError(400,"unsupported_owner_filter")
        if "user_id" in f and f["user_id"]!="eq."+owner:
            return 200,[]
        order=f.get("order","created_at.asc,id.asc")
        if order not in ("created_at.asc,id.asc","created_at.desc,id.desc"):
            raise HttpError(400,"unsupported_order")
        limit=int(f.get("limit","100"))
        if not 1<=limit<=500:
            raise HttpError(400,"limit")
        columns=f.get("select","*")
        columns=COLUMNS if columns=="*" else columns.split(",")
        if not set(columns)<=set(COLUMNS):
            raise HttpError(400,"select")
        rows=[row for (uid,_),row in self.rows.items() if uid==owner]
        pair=lambda row:(stamp(row["created_at"]),row["id"])
        if "or" in f:
            m=CURSOR.fullmatch(f["or"])
            if not m or m[1]!=m[2] or order!="created_at.asc,id.asc":
                raise HttpError(400,"unsupported_cursor")
            position=stamp(m[1]),str(uuid.UUID(m[3]))
            rows=[row for row in rows if pair(row)>position]
        if "created_at" in f:
            op,_,v=f["created_at"].partition(".")
            if op not in ("gt","eq"):
                raise HttpError(400,"unsupported_timestamp_filter")
            d=stamp(v)
            rows=[row for row in rows if (stamp(row["created_at"])>d if op=="gt" else stamp(row["created_at"])==d)]
        if "id" in f:
            op,_,v=f["id"].partition(".")
            if op not in ("gt","eq"):
                raise HttpError(400,"unsupported_id_filter")
            rid=str(uuid.UUID(v))
            rows=[row for row in rows if (row["id"]>rid if op=="gt" else row["id"]==rid)]
        rows.sort(key=pair,reverse=order.endswith(".desc"))
        return 200,[{k:row[k] for k in columns} for row in rows[:limit]]

GET_ACTIVE = '/rest/v1/shift_active_checkpoint'
WRITE_ACTIVE = '/rest/v1/rpc/shift_write_active_checkpoint'
ACTIVE_COLUMNS = ('revision', 'mutation_id', 'checkpoint', 'updated_at')
ARGS = {'p_expected_revision', 'p_mutation_id', 'p_checkpoint'}
FIELDS = {'version','id','title','mode','questionIds','answers','submitted','startedAt','testIds','index',
          'contentVersion','deadline','examVersion','audioEdition','examPhase','listeningStartedAt','sectionDeadline',
          'listeningRemaining','readingStartsOnReturn','audioUsed','practiceMedia'}
REQUIRED = {'version','id','title','mode','questionIds','answers','submitted','startedAt','testIds','index'}

class ActiveFixture(Fixture):
    """Mimic route and conflict behavior only; the disposable SQL tests enforce RLS/shape."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.active = {}

    def row(self, rev, mut, checkpoint):
        d = iso(datetime.fromtimestamp(self.clock(), timezone.utc))
        return dict(revision=rev,mutation_id=mut,checkpoint=checkpoint,updated_at=d)

    def _api(self, method, path, q, body, headers):
        if path == FAULT and body.get('path') in (GET_ACTIVE, WRITE_ACTIVE):
            if method != 'POST' or headers.get('x-shift-fixture-control') != '1':
                raise HttpError(404,'not_found')
            if body.get('status') not in (401,429,503):
                raise HttpError(400,'invalid_fault')
            self.faults[body['path']]=body['status']
            return 200,{"queued":True}
        bearer=headers.get("authorization","").removeprefix("Bearer ")
        if path not in (GET_ACTIVE, WRITE_ACTIVE):
            status, value=super()._api(method,path,q,body,headers)
            if method=='POST' and path==RPC and value=='inserted':
                owner=self.owner(bearer)
                saved=self.active.get(owner)
                checkpoint=(saved or {}).get('checkpoint')
                if checkpoint and body['p_id'].lower()==checkpoint['id']:
                    self.active[owner]=self.row(saved['revision']+1,str(uuid.uuid4()),None)
            return status,value

        if headers.get("apikey")!=KEY:
            raise HttpError(401,"fixture_key_required")
        if path in self.faults:
            raise HttpError(self.faults.pop(path),"injected_fixture_fault")
        owner=self.owner(bearer)
        saved=self.active.get(owner)
        if path == GET_ACTIVE and method == 'GET':
            if set(q)-{'select','limit'} or any(len(v)!=1 for v in q.values()):
                raise HttpError(400,'unsupported_filter')
            projection=q.get('select',['*'])[0]
            requested=ACTIVE_COLUMNS if projection=='*' else projection.split(',')
            if not set(requested)<=set(ACTIVE_COLUMNS) or str(q.get('limit',['1'])[0]) not in ('1','2','10','100'):
                raise HttpError(400,'unsupported_filter')
            return 200,[{k:saved[k] for k in requested}] if saved else []

        if path != WRITE_ACTIVE or method != 'POST':
            raise HttpError(405,'method_not_allowed')
        if q or set(body)!=ARGS:
            raise HttpError(400,'invalid_checkpoint')
        expect=body['p_expected_revision']
        if type(expect) is not int or not 0<=expect<9007199254740991:
            raise HttpError(400,'invalid_checkpoint')
        mut=str(uuid.UUID(body['p_mutation_id']))
        ck=body['p_checkpoint']
        if ck is not None:
            if not (type(ck) is dict and REQUIRED<=set(ck)<=FIELDS and type(ck['version']) is int and ck['version']==1
                and len(json.dumps(ck,ensure_ascii=False).encode())<=CHUNK
                and ck['mode'] in ('practice','exam') and type(ck['questionIds']) is list
                and type(ck['answers']) is dict and 0<len(ck['questionIds'])<=5000
                and type(ck['index']) is int and 0<=ck['index']<len(ck['questionIds'])
                and type(ck['id']) is str and str(uuid.UUID(ck['id']))==ck['id']):
                raise HttpError(400,'invalid_checkpoint')
            if 'practiceMedia' in ck:
                media=ck['practiceMedia']
                if not (ck['mode']=='practice' and type(media) is dict and set(media)=={'groupId','offset','rate','paused'}
                        and type(media['groupId']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,95}',media['groupId'])
                        and media['groupId'] not in ('constructor','prototype','__proto__')
                        and type(media['offset']) in (int,float) and 0<=media['offset']<=86400
                        and type(media['rate']) in (int,float) and media['rate'] in (0.75,1,1.25)
                        and type(media['paused']) is bool):
                    raise HttpError(400,'invalid_checkpoint')
        if saved and saved['mutation_id']==mut:
            return 200,'already_saved' if saved['revision']==expect+1 and payload_equal(saved['checkpoint'],ck) else 'conflict'
        if ck and (owner,ck['id']) in self.rows:
            return 200,'already_completed'
        if (saved['revision'] if saved else 0)!=expect:
            return 200,'conflict'
        self.active[owner]=self.row(expect+1,mut,ck)
        return 200,'saved'


def handler_for(root,state):
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*_):
            pass

        def allowed_origin(self):
            o=self.headers.get("Origin")
            return not o or o in (f"http://127.0.0.1:{self.server.server_port}",f"http://localhost:{self.server.server_port}")

        def body(self):
            size=int(self.headers.get("Content-Length","0"))
            if size<0 or size>CHUNK+16384:
                raise HttpError(413,"request_too_large")
            if not size:
                return {}
            if self.headers.get_content_type()!="application/json":
                raise HttpError(415,"json_required")
            def bad_const(_): raise ValueError("invalid JSON")
            data=json.loads(self.rfile.read(size),parse_constant=bad_const)
            if not isinstance(data,dict):
                raise HttpError(400,"object_required")
            return data

        def json_reply(self,status,data=None):
            raw=b"" if data is None else json.dumps(data,ensure_ascii=False,separators=(",",":")).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(raw)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers()
            if self.command!="HEAD" and raw:
                self.wfile.write(raw)

        def dispatch(self):
            try:
                u=urlsplit(self.path)
                if u.scheme or u.netloc or not self.allowed_origin():
                    raise HttpError(403,"private_same_origin_only")
                if u.path.startswith((AUTH,"/rest/v1/","/__shift_qa/")):
                    if self.command not in ("GET","POST","PUT"):
                        raise HttpError(405,"method_not_allowed")
                    q=parse_qs(u.query,keep_blank_values=True,max_num_fields=12)
                    body=self.body() if self.command in ("POST","PUT") else {}
                    status,data=state.api(self.command,u.path,q,body,{k.lower():v for k,v in self.headers.items()})
                    return self.json_reply(status,data)
                if self.command not in ("GET","HEAD"):
                    raise HttpError(405,"method_not_allowed")
                rel=unquote(u.path,errors="strict")
                if rel=="/":
                    rel="/index.html"
                parts=rel.lstrip("/").split("/")
                if any(not x or x.startswith(".") or "\\" in x or "\x00" in x for x in parts):
                    raise HttpError(404,"not_found")
                file=root.joinpath(*parts)
                if not file.is_file() or file.resolve()!=file:
                    raise HttpError(404,"not_found")
                size=file.stat().st_size
                lo,hi=0,size-1
                request_range=self.headers.get("Range")
                extra={}
                status=200
                if request_range:
                    m=re.fullmatch(r"bytes=(\d*)-(\d*)",request_range)
                    if m and any(m.groups()) and size>0:
                        if m[1]:
                            lo=int(m[1]); hi=min(int(m[2]),hi) if m[2] else hi
                        else:
                            lo=max(0,size-int(m[2]))
                    if not m or not any(m.groups()) or lo>hi or lo>=size:
                        self.send_response(416); self.send_header("Content-Range",f"bytes */{size}")
                        self.send_header("Content-Length","0"); self.end_headers(); return
                    status=206; extra["Content-Range"]=f"bytes {lo}-{hi}/{size}"
                self.send_response(status)
                self.send_header("Content-Type",{".ogg":"audio/ogg",".mjs":"text/javascript"}.get(file.suffix) or mimetypes.guess_type(file.name)[0] or "application/octet-stream")
                self.send_header("Content-Length",str(max(0,hi-lo+1)))
                self.send_header("Accept-Ranges","bytes")
                self.send_header("Cache-Control","no-store")
                for k,v in extra.items():
                    self.send_header(k,v)
                self.end_headers()
                if self.command!="HEAD":
                    with file.open("rb") as stream:
                        stream.seek(lo); remain=max(0,hi-lo+1)
                        while remain:
                            chunk=stream.read(min(remain,65536))
                            if not chunk: break
                            self.wfile.write(chunk);remain-=len(chunk)
            except HttpError as e:
                self.json_reply(e.status,dict(code=e.code,message=e.code))
            except (TypeError,ValueError,KeyError,OverflowError):
                self.json_reply(400,dict(code="invalid_fixture_request",message="invalid_fixture_request"))
            except (BrokenPipeError,ConnectionResetError):
                pass

        do_GET=do_POST=do_PUT=do_HEAD=do_OPTIONS=do_DELETE=do_PATCH=dispatch
    return Handler

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("candidate",type=Path)
    ap.add_argument("--port",type=int,default=8765)
    ap.add_argument("--ttl",type=int,default=120)
    a=ap.parse_args()
    root=a.candidate.resolve(strict=True)
    if not root.is_dir() or not (root/"index.html").is_file() or not 1<=a.ttl<=3600:
        ap.error("candidate must have index.html and TTL must be 1–3600")
    with ThreadingHTTPServer(("127.0.0.1",a.port),handler_for(root,ActiveFixture(a.ttl))) as server:
        print(f"SHIFT synthetic only: http://127.0.0.1:{server.server_port}/",flush=True)
        server.serve_forever()

if __name__=="__main__":
    main()
