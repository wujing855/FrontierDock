"""仅提供本机 UI 与受限阅读状态 API；工作区和密钥不属于静态目录。"""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlsplit,parse_qsl,unquote
from pathlib import Path
import json,mimetypes,threading
from .core import Workspace
from . import views

WEB=Path(__file__).resolve().parent.parent/'web'
class AppServer(ThreadingHTTPServer):
 daemon_threads=True
 def __init__(self,address,workspace):
  self.workspace=workspace;self.cache={};self.lock=threading.Lock()
  super().__init__(address,Handler)
 def view(self,key,build):
  w=self.workspace;version=(w.db.stat().st_mtime_ns,(w.root/'config.json').stat().st_mtime_ns,(w.root/'state.json').stat().st_mtime_ns if(w.root/'state.json').exists()else 0)
  with self.lock:
   if self.cache.get('_version')!=version:self.cache={'_version':version};self.workspace=Workspace(w.root)
   if key not in self.cache:
    if len(self.cache)>150:self.cache={'_version':version}
    self.cache[key]=build(self.workspace)
   return self.cache[key]

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,status,data,ctype='application/json; charset=utf-8'):
  body=data if isinstance(data,bytes)else json.dumps(data,ensure_ascii=False).encode()
  self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'")
  self.end_headers();self.wfile.write(body)
 def host_ok(self):
  return self.headers.get('Host')in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
 def do_GET(self):
  if not self.host_ok():return self.reply(403,{'error':'host_rejected'})
  path=urlsplit(self.path).path;q=dict(parse_qsl(urlsplit(self.path).query));w=self.server.workspace
  try:
   if path=='/runtime.js':
    runtime={'canonical':True,'demo':bool(w.config.get('demo')),'file_import':True,'timezone':w.config['project']['timezone']}
    return self.reply(200,('globalThis.FRONTIERDOCK_RUNTIME='+json.dumps(runtime)+';').encode(),'text/javascript; charset=utf-8')
   if path.startswith('/api/v1/'):
    endpoint=path[8:];key=self.path
    if endpoint=='journals':data=self.server.view(key,views.journals)
    elif endpoint=='catalog':data=self.server.view(key,lambda w:views.catalog(w,q))
    elif endpoint=='issues':data=self.server.view(key,lambda w:views.issues(w,q.get('journal','')))
    elif endpoint=='analytics':data=self.server.view(key,lambda w:views.analytics(w,q))
    elif endpoint=='reading':data=self.server.view(key,lambda w:views.reading(w,q))
    elif endpoint=='update-status':data=self.server.view(key,views.status)
    elif endpoint=='candidates':data=[]
    elif endpoint=='record':
     m=w.get(q.get('id',''))
     if not m:return self.reply(404,{'error':'record_not_found'})
     data={'metadata':m,'reading':w.reading_state(m['record_id'])}
    else:return self.reply(404,{'error':'endpoint_not_found'})
    return self.reply(200,data)
   target=(WEB/unquote(path).lstrip('/')).resolve()if path!='/'else WEB/'index.html'
   if not target.is_relative_to(WEB)or not target.is_file()or any(x.startswith('.')for x in target.relative_to(WEB).parts):return self.reply(404,{'error':'not_found'})
   return self.reply(200,target.read_bytes(),mimetypes.guess_type(target.name)[0]or'application/octet-stream')
  except (ValueError,KeyError,TypeError):self.reply(400,{'error':'invalid_request'})
  except Exception:self.reply(500,{'error':'local_storage_error; ask your Agent to run doctor'})
 def do_POST(self):
  origin=self.headers.get('Origin');allowed={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
  if not self.host_ok()or(origin and origin not in allowed)or self.headers.get('X-FrontierDock')!='1':return self.reply(403,{'error':'local_write_rejected'})
  try:
   if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('json_required')
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=4096:raise ValueError('request_too_large')
   v=json.loads(self.rfile.read(size));endpoint=urlsplit(self.path).path;w=self.server.workspace
   if endpoint=='/api/v1/reading':data=w.set_reading(v['record_id'],v['state'],v['revision'])
   elif endpoint=='/api/v1/visibility':data=w.set_reading(v['record_id'],None,v['revision'],v['removed'])
   else:return self.reply(404,{'error':'endpoint_not_found'})
   self.reply(200,data)
  except RuntimeError:self.reply(409,{'error':'revision_conflict; refresh before retrying'})
  except (ValueError,KeyError,TypeError):self.reply(400,{'error':'invalid_write'})
  except Exception:self.reply(500,{'error':'local_storage_error'})

def serve(workspace,port=8876):
 server=AppServer(('127.0.0.1',port),workspace)
 print(f'FrontierDock: http://127.0.0.1:{server.server_port}  (Ctrl+C to stop)',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
