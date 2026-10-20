"""从仓库根目录运行 python -m frontierdock；不依赖全局安装。"""
import argparse,getpass,json,os,sys,stat
from pathlib import Path
from .core import Workspace,initialize,validate_config,atomic_json
from .workflow import plan,update,maintain,doctor,agent_queue,backup,run_lock,conflicts,review_conflict
from .providers import ProviderError,secret_path,deepseek_fetch

def main():
 parser=argparse.ArgumentParser(description='FrontierDock — Build your own research frontier.')
 sub=parser.add_subparsers(dest='command',required=True)
 for name in ('init','serve','configure','doctor','plan','update','maintain','agent-queue','import','enrich','pdf','pdf-status','fetch','conflicts','review-conflict'):
  cmd=sub.add_parser(name);cmd.add_argument('--workspace',required=True,help='independent FrontierDock workspace')
  if name=='init':cmd.add_argument('--demo',action='store_true')
  if name=='serve':cmd.add_argument('--port',type=int,default=8876)
  if name in ('configure','import','enrich','pdf'):cmd.add_argument('--file',required=True)
  if name=='update':cmd.add_argument('--deepseek',action='store_true',help='optional paid search; requires config opt-in too')
  if name=='pdf':cmd.add_argument('--allow-cloud',action='store_true')
  if name=='pdf-status':cmd.add_argument('--id',required=True)
  if name=='fetch':cmd.add_argument('--url',required=True)
  if name=='review-conflict':cmd.add_argument('--id',type=int,required=True);cmd.add_argument('--evidence-url',required=True)
 key=sub.add_parser('key');key.add_argument('action',choices=['set']);key.add_argument('provider',choices=['llm','deepseek','mineru'])
 args=parser.parse_args()
 try:
  if args.command=='key':
   if not sys.stdin.isatty():raise ValueError('interactive_terminal_required; use environment variables for automation')
   value=getpass.getpass('API key (hidden): ').strip()
   if not value or any(x.isspace()for x in value):raise ValueError('credential_empty_or_contains_whitespace')
   path=secret_path(args.provider);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
   if path.is_symlink()or path.parent.is_symlink():raise ValueError('secret_symlink_rejected')
   os.chmod(path.parent,0o700);fd=os.open(path,os.O_CREAT|os.O_WRONLY|os.O_TRUNC,0o600)
   with os.fdopen(fd,'w')as f:f.write(value+'\n')
   os.chmod(path,0o600);print('Saved outside workspace, permission 600. Network access and free quota not verified.');return
  if args.command=='init':w=initialize(args.workspace,args.demo);result={'status':'initialized','demo':args.demo}
  else:
   w=Workspace(args.workspace)
   if args.command=='serve':
    from .server import serve
    serve(w,args.port);return
   elif args.command=='configure':
    config=validate_config(json.loads(Path(args.file).read_text()))
    with run_lock(w):
     atomic_json(w.root/'backups'/'previous-config.json',w.config);atomic_json(w.root/'config.json',config)
    result={'status':'configured','journals':len(config['journals'])}
   elif args.command in ('import','enrich'):
    values=json.loads(Path(args.file).read_text())
    with run_lock(w):backup(w);result=w.import_records(values)if args.command=='import'else w.enrich(values)
   elif args.command=='plan':result=plan(w)
   elif args.command=='update':result=update(w,args.deepseek)
   elif args.command=='maintain':result=maintain(w)
   elif args.command=='doctor':result=doctor(w)
   elif args.command=='conflicts':result=conflicts(w)
   elif args.command=='review-conflict':result=review_conflict(w,args.id,args.evidence_url)
   elif args.command=='agent-queue':result=agent_queue(w)
   elif args.command=='pdf':
    from .pdf import extract
    result=extract(w,args.file,args.allow_cloud)
   elif args.command=='pdf-status':
    from .pdf import status
    result=status(w,args.id)
   elif args.command=='fetch':
    if not w.config['search'].get('deepseek'):raise ValueError('deepseek_not_enabled')
    from .core import fingerprint
    if w.config['limits']['max_deepseek_calls_per_run']<1:raise ValueError('deepseek_budget_zero')
    value=deepseek_fetch(args.url);value={'source_url':args.url,'kind':'unverified_page','page':value}
    filename='fetch-'+fingerprint(args.url,'')[:20]+'.json';atomic_json(w.root/'requests'/filename,value);result={'status':'page_saved_for_agent_identity_and_abstract_verification','file':'requests/'+filename}
  print(json.dumps(result,ensure_ascii=False,indent=2))
 except (ValueError,KeyError,TypeError,OSError,ProviderError,json.JSONDecodeError)as e:
  # 不打印可能含密钥、签名 URL 或私人路径的底层异常。
  code=str(e)if isinstance(e,(ValueError,ProviderError))and not isinstance(e,json.JSONDecodeError)else type(e).__name__
  if len(code)>180 or any(x in code for x in ('http://','https://','/Users/','/home/','Bearer')):code=type(e).__name__
  print(json.dumps({'error':code,'next':'Ask your Agent to diagnose locally; do not publish config, requests, logs or keys.'},ensure_ascii=False),file=sys.stderr);raise SystemExit(1)

if __name__=='__main__':main()
