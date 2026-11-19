#!/usr/bin/env python3
"""Loopback-only HTTP server for synthetic SHIFT fixtures, with media byte ranges."""
from argparse import ArgumentParser
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlsplit, unquote


def make_server(root, port=0):
    receipt_bytes=(root/'fixture.json').read_bytes()
    receipt=json.loads(receipt_bytes)
    if receipt.get('fixtureOnly') is not True or receipt.get('doNotDeploy') is not True:
        raise ValueError('Refusing to serve a non-fixture tree.')
    files=receipt['files']
    site=(root/'site').resolve()
    identity=sha256(receipt_bytes).hexdigest()
    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self): self.reply(False)
        def do_GET(self): self.reply(True)
        def reply(self, body):
            try:
                url=urlsplit(self.path)
                p=unquote(url.path,errors='strict')
                if url.scheme or url.netloc or not p.startswith('/'):raise ValueError()
                if p=='/__shift_fixture':
                    data=json.dumps({'case':'SHIFT_SYNTHETIC_LOCAL_ONLY','identity':identity}).encode()
                    self.send_response(200)
                    self.send_header('X-Shift-Fixture',identity)
                    self.send_header('Cache-Control','no-store')
                    self.send_header('Content-Type','application/json; charset=utf-8')
                    self.send_header('Content-Length',str(len(data)))
                    self.end_headers()
                    if body:self.wfile.write(data)
                    return
                ref='index.html' if p=='/' else p[1:]
                if '\\' in ref or '\0' in ref or any(part in ('','.','..') for part in ref.split('/')):
                    self.send_error(400);return
            except (ValueError,UnicodeError):
                self.send_error(400);return
            if ref not in files:
                self.send_error(404);return
            file=site/ref
            # Reject symlink substitutions or escaped runtime paths.
            if not file.is_file() or file.resolve()!=file or not file.is_relative_to(site):
                self.send_error(404);return
            size=file.stat().st_size
            if size!=files[ref]['size']:
                self.send_error(409,'Fixture mutated; regenerate it');return
            start,end=0,size-1
            requested=self.headers.get('Range')
            if requested:
                match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
                if match and any(match.groups()) and size:
                    a,b=match.groups()
                    if a:
                        start=int(a);end=min(int(b),size-1) if b else size-1
                    else:
                        start=max(0,size-int(b));end=size-1
                if not match or not any(match.groups()) or start>end or start<0 or start>=size:
                    self.send_response(416)
                    self.send_header('Content-Range',f'bytes */{size}')
                    self.send_header('Content-Length','0')
                    self.end_headers()
                    return
            self.send_response(206 if requested else 200)
            kind='audio/wav' if file.suffix=='.wav' else mimetypes.guess_type(ref)[0] or 'application/octet-stream'
            self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(max(0,end-start+1)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Shift-Fixture',identity)
            self.send_header('Accept-Ranges','bytes')
            if requested: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.end_headers()
            if body:
                with file.open('rb') as f:
                    f.seek(start);remaining=end-start+1
                    while remaining>0:
                        b=f.read(min(1024*256,remaining))
                        if not b:break
                        self.wfile.write(b);remaining-=len(b)
        def log_message(self, fmt, *args):
            if self.server.verbose:super().log_message(fmt,*args)
    s=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    s.verbose=False
    return s


if __name__=='__main__':
    p=ArgumentParser(description=__doc__)
    p.add_argument('fixture',type=Path)
    p.add_argument('--port',type=int,default=8769)
    p.add_argument('--verbose',action='store_true')
    a=p.parse_args()
    with make_server(a.fixture,a.port) as server:
        server.verbose=a.verbose
        print('Synthetic local-only fixture: http://127.0.0.1:'+str(server.server_port)+'/',flush=True)
        server.serve_forever()
