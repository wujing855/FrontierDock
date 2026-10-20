#!/usr/bin/env python3
"""按白名单构建公开源码包；不递归打包工作目录。"""
from pathlib import Path
import argparse,hashlib,json,re,zipfile,sys

ROOT=Path(__file__).resolve().parent.parent
TOP={'README.md','README.en.md','LICENSE','THIRD_PARTY_NOTICES.md','CONTRIBUTING.md','SECURITY.md','AGENTS.md','.gitignore','package.json','pyproject.toml'}
DIRS={'frontierdock','web','docs','skills','tests','scripts','.github','examples'}
EXT={'.py','.js','.mjs','.json','.html','.css','.svg','.woff2','.md','.yaml','.yml','.toml','.txt','.png','.jpg','.jpeg'}
PATTERNS=[('possible_secret',re.compile(r'(?i)\bsk-[a-z0-9_-]{24,}\b|\bAKIA[A-Z0-9]{16}\b|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')),('private_machine_path',re.compile(r'(?:/Users|/home)/[^/\s"\x27<>]+/')),('embedded_bearer',re.compile(r'(?i)Bearer\s+[a-z0-9_-]{24,}'))]

def inventory(root=ROOT,denied=()):
 chosen=[];errors=[]
 for p in sorted(root.rglob('*')):
  rel=p.relative_to(root);parts=rel.parts
  # 私人运行目录即使位于源码根目录也不进入候选。
  if any(x in {'.git','__pycache__','node_modules','.venv','workspace','my-research','dist','backups','secrets','extractions','requests'}for x in parts):continue
  if not p.is_file():continue
  if p.is_symlink():errors.append({'file':str(rel),'reason':'symlink_rejected'});continue
  if not(len(parts)==1 and p.name in TOP or len(parts)>1 and parts[0]in DIRS and(p.suffix in EXT or p.name=='LICENSE')):continue
  if p.suffix in {'.key','.sqlite','.db','.pdf','.log'}or p.name in {'config.json','state.json','free-model-inventory.json'}:errors.append({'file':str(rel),'reason':'runtime_file_in_source'});continue
  data=p.read_bytes()
  if p.suffix not in {'.woff2','.png','.jpg','.jpeg'}:
   try:text=data.decode('utf-8')
   except UnicodeError:errors.append({'file':str(rel),'reason':'unexpected_binary'});continue
   for reason,pattern in PATTERNS:
    if pattern.search(text):errors.append({'file':str(rel),'reason':reason})
   if any(word and word in text for word in denied):errors.append({'file':str(rel),'reason':'private_denylist_match'})
  chosen.append(p)
 return chosen,errors

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');parser.add_argument('--output');parser.add_argument('--deny-file',help='private newline-separated identifiers; never packaged')
 args=parser.parse_args();denied=Path(args.deny_file).read_text().splitlines()if args.deny_file else[]
 files,errors=inventory(denied=denied)
 report={'files':len(files),'bytes':sum(p.stat().st_size for p in files),'findings':errors,'method':'explicit source allowlist; runtime and history excluded'}
 if errors:print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(1)
 if args.output:
  output=Path(args.output).expanduser().resolve();output.parent.mkdir(parents=True,exist_ok=True)
  if output.exists():raise SystemExit('Output already exists; choose a new release name.')
  with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED)as archive:
   for p in files:archive.write(p,'FrontierDock/'+str(p.relative_to(ROOT)))
  report['archive_sha256']=hashlib.sha256(output.read_bytes()).hexdigest();report['archive_bytes']=output.stat().st_size
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
