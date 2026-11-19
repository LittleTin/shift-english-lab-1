#!/usr/bin/env python3
"""Independent local HTTP fixture checks for every exact Opus object; not host proof."""
import argparse,hashlib,json,re,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from http.client import HTTPConnection
a=argparse.ArgumentParser();a.add_argument('--proof',type=Path,required=True);z=a.parse_args()
p=z.proof;site=p/'site';r=json.loads((p/'asset-report.json').read_text());assets={x['path']:x for x in r['assets'].values()}
class H(BaseHTTPRequestHandler):
 def do_HEAD(self):self.send_data(False)
 def do_GET(self):self.send_data(True)
 def log_message(self,*args):pass
 def send_data(self,body):
  rel=self.path.lstrip('/'); 
  if rel not in assets:self.send_error(404);return
  f=site/rel;n=f.stat().st_size;lo=0;hi=n-1; rr=self.headers.get('Range')
  if rr:
   m=re.fullmatch(r'bytes=(\d*)-(\d*)',rr)
   if not m or not any(m.groups()):self.send_error(416);return
   a,b=m.groups()
   if a:lo=int(a);hi=min(hi,int(b)) if b else hi
   else:lo=max(0,n-int(b))
   if not 0<=lo<=hi<n:
    self.send_response(416);self.send_header('Content-Range',f'bytes */{n}');self.send_header('Content-Length','0');self.end_headers();return
  self.send_response(206 if rr else 200);self.send_header('Content-Type','audio/ogg');self.send_header('Content-Length',str(hi-lo+1));self.send_header('Accept-Ranges','bytes')
  if rr:self.send_header('Content-Range',f'bytes {lo}-{hi}/{n}')
  self.end_headers()
  if body:
   with f.open('rb') as fp:fp.seek(lo);self.wfile.write(fp.read(hi-lo+1))
with ThreadingHTTPServer(('127.0.0.1',0),H) as srv:
 t=threading.Thread(target=srv.serve_forever,daemon=True);t.start()
 def req(method,rel,r=None):
  c=HTTPConnection('127.0.0.1',srv.server_port,timeout=5);c.request(method,'/'+rel,headers={'Range':r} if r else {}); resp=c.getresponse();b=resp.read();v=(resp.status,dict(resp.getheaders()),b);c.close();return v
 for rel,row in sorted(assets.items()):
  b=(site/rel).read_bytes();n=len(b);assert hashlib.sha256(b).hexdigest()==row['encodedSha256']
  st,h,x=req('HEAD',rel);assert st==200 and h['Content-Type']=='audio/ogg' and h['Content-Length']==str(n) and h['Accept-Ranges']=='bytes' and x==b''
  for a1,b1 in [(0,3),(n//2,n//2+7),(n-8,n-1)]:
   st,h,x=req('GET',rel,f'bytes={a1}-{b1}');assert st==206 and h['Content-Range']==f'bytes {a1}-{b1}/{n}' and h['Content-Type']=='audio/ogg' and x==b[a1:b1+1]
  st,h,x=req('GET',rel,f'bytes={n}-');assert st==416 and h['Content-Range']==f'bytes */{n}' and x==b''
 srv.shutdown()
proof=dict(status='byte-range-local-fixture-not-live-deployment',opusAssets=len(assets),head200=len(assets),ranges206=3*len(assets),pastEof416=len(assets),mime='audio/ogg')
(p/'http-range-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
