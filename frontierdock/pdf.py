"""可选提取入口；不提供全文批注，不自动安装 MinerU。"""
from pathlib import Path
from urllib.parse import urlsplit,quote
import hashlib,subprocess,json,zipfile,io
from .providers import get_secret,json_request,request,ProviderError
from .core import atomic_json

def extract(w,input_file,allow_cloud=False):
 source=Path(input_file).expanduser().resolve();mode=w.config['pdf']['mode']
 if mode=='disabled':raise ValueError('pdf_disabled; ask Agent to configure local or cloud extraction')
 if not source.is_file()or source.suffix.lower()!='.pdf' or not source.read_bytes()[:1024].lstrip().startswith(b'%PDF'):raise ValueError('valid_pdf_required')
 if source.stat().st_size>20_000_000:raise ValueError('app_pdf_limit_20MB; split the file with your Agent')
 ident=hashlib.sha256(source.read_bytes()).hexdigest()[:24];folder=w.root/'extractions'/ident;folder.mkdir(parents=True,exist_ok=True)
 if mode=='local':
  command=w.config['pdf'].get('local_command',[])
  if not command or not all(isinstance(x,str)for x in command):raise ValueError('local_command_array_required')
  args=[x.replace('{input}',str(source)).replace('{output}',str(folder))for x in command]
  try:
   # 子进程不继承本应用 API 密钥；输出不直接进入诊断或公开材料。
   import os
   env={k:v for k,v in os.environ.items()if not any(x in k.upper()for x in ('TOKEN','KEY','SECRET','PASSWORD'))}
   with (folder/'local.log').open('wb')as log:result=subprocess.run(args,stdout=log,stderr=log,timeout=1800,env=env)
  except FileNotFoundError:raise ValueError('mineru_not_installed; ask Agent for supported installation options')from None
  except subprocess.TimeoutExpired:raise ValueError('local_extract_timeout; local log retained')from None
  if result.returncode:raise ValueError('local_extract_failed; ask Agent to inspect local log')
  return {'status':'local_completed','directory':'extractions/'+ident}
 if not allow_cloud:raise ValueError('cloud_upload_requires_explicit_allow_cloud; this sends the selected PDF to MinerU')
 key=get_secret('mineru')
 result=json_request('https://mineru.net/api/v4/file-urls/batch',{'files':[{'name':'document.pdf','data_id':ident}],'model_version':'vlm'},key)
 if result.get('code')!=0:raise ProviderError('mineru_submission_rejected')
 data=result['data'];upload=data['file_urls'][0]
 if urlsplit(upload).scheme!='https':raise ProviderError('mineru_upload_url_rejected')
 request(upload,raw=source.read_bytes(),method='PUT')
 atomic_json(folder/'task.json',{'batch_id':data['batch_id'],'data_id':ident})
 return {'status':'submitted','extraction_id':ident,'next':'pdf-status --id '+ident}

def status(w,ident):
 import re
 if not re.fullmatch('[a-f0-9]{24}',ident):raise ValueError('extraction_id_invalid')
 folder=w.root/'extractions'/ident;task=json.loads((folder/'task.json').read_text())
 result=json_request('https://mineru.net/api/v4/extract-results/batch/'+quote(task['batch_id'],safe=''),key=get_secret('mineru'))
 if result.get('code')!=0:raise ProviderError('mineru_status_rejected')
 rows=result['data'].get('extract_result',[])
 if not rows:return {'status':'pending'}
 row=rows[0]
 if row['state']!='done':return {'status':row['state']}
 url=row['full_zip_url']
 if urlsplit(url).scheme!='https':raise ProviderError('mineru_result_url_rejected')
 data=request(url)
 with zipfile.ZipFile(io.BytesIO(data))as archive:
  entries=[x for x in archive.infolist()if x.filename.endswith('.md')]
  if not entries or sum(x.file_size for x in entries)>30_000_000:raise ProviderError('extract_output_missing_or_too_large')
  # 仅读取 Markdown 内容，绝不按远程 ZIP 路径写文件。
  for i,entry in enumerate(entries):(folder/f'result-{i}.md').write_bytes(archive.read(entry))
 return {'status':'done','markdown_files':len(entries),'directory':'extractions/'+ident}
