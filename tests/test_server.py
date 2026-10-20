import unittest,tempfile,threading,json,http.client
from pathlib import Path
from frontierdock.core import initialize
from frontierdock.server import AppServer

class ServerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.w=initialize(Path(self.temp.name)/'data',True)
  self.server=AppServer(('127.0.0.1',0),self.w);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.port=self.server.server_port
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
 def req(self,path='/',body=None,headers=None,method=None):
  conn=http.client.HTTPConnection('127.0.0.1',self.port);conn.request(method or('POST'if body else'GET'),path,body,headers or{});r=conn.getresponse();data=r.read();status=r.status;conn.close();return status,data
 def test_static_ui_and_runtime(self):
  status,body=self.req();self.assertEqual(status,200);self.assertIn(b'FrontierDock',body)
  self.assertEqual(self.req('/runtime.js')[0],200)
 def test_workspace_never_static(self):
  for path in ['/config.json','/catalog.sqlite','/.frontierdock-workspace','/../frontierdock/core.py','/%2e%2e/frontierdock/core.py','/.git/config']:
   self.assertEqual(self.req(path)[0],404,path)
 def test_host_check(self):self.assertEqual(self.req(headers={'Host':'attacker.example'})[0],403)
 def test_api_reads(self):
  for path in ['journals','catalog','issues?journal=none','analytics','update-status','reading','record?id=demo:0']:
   status,body=self.req('/api/v1/'+path);self.assertEqual(status,200,path);json.loads(body)
 def test_write_requires_header_and_origin(self):
  b=json.dumps({'record_id':'demo:0','state':'to_read','revision':0});h={'Content-Type':'application/json'}
  self.assertEqual(self.req('/api/v1/reading',b,h)[0],403);h['X-FrontierDock']='1';h['Origin']='https://attacker.example';self.assertEqual(self.req('/api/v1/reading',b,h)[0],403)
 def test_write_persists_and_invalidates_catalog_cache(self):
  self.req('/api/v1/catalog');h={'Content-Type':'application/json','X-FrontierDock':'1','Origin':f'http://127.0.0.1:{self.port}'};b=json.dumps({'record_id':'demo:0','state':'to_read','revision':0})
  self.assertEqual(self.req('/api/v1/reading',b,h)[0],200);self.assertEqual(self.req('/api/v1/reading',b,h)[0],409)
  _,body=self.req('/api/v1/catalog?q=research%20signals');row=next(x for x in json.loads(body)['items']if x['record_id']=='demo:0');self.assertEqual(row['reading']['status'],'to_read')
 def test_invalid_body_and_unknown_endpoint(self):
  h={'Content-Type':'application/json','X-FrontierDock':'1'};self.assertEqual(self.req('/api/v1/reading','[]',h)[0],400);self.assertEqual(self.req('/api/v1/unknown')[0],404)

if __name__=='__main__':unittest.main()
