import unittest,tempfile,json,threading,os
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from unittest.mock import patch
from frontierdock.core import initialize,fingerprint
from frontierdock.providers import derive,ProviderError,public_url,get_secret
from frontierdock.pdf import extract,status
from scripts.release import inventory

class IntegrationTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.w=initialize(self.root/'workspace',True)
 def tearDown(self):self.tmp.cleanup()
 def test_actual_compatible_http_request_and_enrichment(self):
  received=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(s):
    body=json.loads(s.rfile.read(int(s.headers['Content-Length'])));received.append(body)
    result={'model_keywords':['fictional','research'],'abstract_translation':'这个虚构摘要演示研究发现流程。它并非真实出版物，不应被引用。','translated_title':'关于研究信号的虚构研究'}
    raw=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(result,ensure_ascii=False)}}]}).encode();s.send_response(200);s.send_header('Content-Length',str(len(raw)));s.end_headers();s.wfile.write(raw)
  server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with patch.dict(os.environ,{'FRONTIERDOCK_LLM_KEY':'test-only-credential'}):value=derive(self.w.get('demo:0'),{'base_url':f'http://127.0.0.1:{server.server_port}/v1','allow_local':True,'model':'local-test'})
   self.w.enrich([value]);self.assertTrue(self.w.get('demo:0')['abstract_translation']);self.assertEqual(received[0]['model'],'local-test')
   self.assertIn(self.w.get('demo:0')['abstract'],received[0]['messages'][1]['content'])
  finally:server.shutdown();server.server_close();thread.join()
 def test_cloud_upload_requires_specific_opt_in(self):
  source=self.root/'dummy.pdf';source.write_bytes(b'%PDF-1.4\n% synthetic fixture only\n');self.w.config['pdf']['mode']='cloud'
  with patch('frontierdock.pdf.json_request',side_effect=AssertionError('no cloud request allowed')):
   with self.assertRaisesRegex(ValueError,'explicit_allow_cloud'):extract(self.w,source)
 def test_pdf_disabled_does_not_install_tools(self):
  with self.assertRaisesRegex(ValueError,'pdf_disabled'):extract(self.w,self.root/'none.pdf')
 def test_mineru_request_contract_and_upload(self):
  self.w.config['pdf']['mode']='cloud';source=self.root/'dummy.pdf';source.write_bytes(b'%PDF-1.4\n% synthetic fixture\n')
  with patch('frontierdock.pdf.get_secret',return_value='test-only'),patch('frontierdock.pdf.json_request',return_value={'code':0,'data':{'batch_id':'test-batch','file_urls':['https://example.org/upload']}})as submit,patch('frontierdock.pdf.request',return_value=b'')as upload:
   result=extract(self.w,source,True)
  self.assertEqual(result['status'],'submitted');self.assertEqual(upload.call_args.kwargs['method'],'PUT');self.assertEqual(submit.call_args.args[1]['model_version'],'vlm')
  task=json.loads(next((self.w.root/'extractions').glob('*/task.json')).read_text());self.assertNotIn('file_urls',task)
 def test_private_network_url_rejected(self):
  with self.assertRaises(ProviderError):public_url('http://127.0.0.1/test')
  with self.assertRaises(ProviderError):public_url('https://user:password@example.org')
 def test_insecure_secret_file_rejected(self):
  p=self.root/'temporary.key';p.write_text('test-only');p.chmod(0o644)
  with patch.dict(os.environ,{'FRONTIERDOCK_LLM_KEY':''}),patch('frontierdock.providers.secret_path',return_value=p):
   with self.assertRaisesRegex(ProviderError,'permissions'):get_secret('llm')
 def test_release_never_includes_runtime_or_history(self):
  root=self.root/'source';root.mkdir();(root/'README.md').write_text('Public project')
  for name in ['workspace','private-data','.git']:
   (root/name).mkdir();(root/name/'catalog.sqlite').write_text('private')
  files,errors=inventory(root);self.assertEqual([p.name for p in files],['README.md']);self.assertEqual(errors,[])
 def test_release_catches_credentials_and_machine_paths(self):
  root=self.root/'source';root.mkdir();(root/'README.md').write_text('sk-'+'a'*32+'\n'+'/Us'+'ers/example/private')
  _,errors=inventory(root);self.assertEqual({x['reason']for x in errors},{'possible_secret','private_machine_path'})

if __name__=='__main__':unittest.main()
