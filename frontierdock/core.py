"""独立工作区、来源记录和字段维护；不读取任何外部工作台。"""
from pathlib import Path
from contextlib import contextmanager,closing
from datetime import datetime,date,timezone
from collections import Counter
import hashlib,json,sqlite3,os,tempfile,re

SCHEMA='''CREATE TABLE IF NOT EXISTS papers(id TEXT PRIMARY KEY,doi TEXT UNIQUE,title TEXT NOT NULL,journal TEXT NOT NULL,date TEXT,year INTEGER,data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reading(id TEXT PRIMARY KEY,status TEXT,removed INTEGER DEFAULT 0,revision INTEGER DEFAULT 0,visibility_revision INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY,incoming TEXT,reason TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS conflict_reviews(conflict_id INTEGER PRIMARY KEY,decision TEXT,evidence_url TEXT,reviewed_at TEXT);'''
def now():return datetime.now(timezone.utc).isoformat()
def fingerprint(title,abstract):return hashlib.sha256(json.dumps([title,abstract],ensure_ascii=False).encode()).hexdigest()
def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(dir=path.parent,prefix='.frontierdock-')
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)

def defaults():
 y=date.today().year
 return {'schema':1,'project':{'name':'FrontierDock','field':'','languages':['en','zh'],'timezone':'UTC','years':[y-1,y]},'journals':[],
 'search':{'mode':'agent','crossref':True,'deepseek':False},
 'translation':{'mode':'agent','base_url':'https://api.openai.com/v1','model':'','key_env':'FRONTIERDOCK_LLM_KEY','free_model_policy':'expiry_then_quality'},
 'pdf':{'mode':'disabled','local_command':['mineru','-p','{input}','-o','{output}']},
 'schedule':{'mode':'manual','times':['09:00'],'timezone':'UTC','journal_interval_days':3},
 'limits':{'max_journals_per_run':5,'max_items_per_journal':30,'max_model_calls_per_run':10,'max_deepseek_calls_per_run':2},'notifications':{'mode':'actionable_only'}}
def validate_config(c):
 if not isinstance(c,dict) or c.get('schema')!=1:raise ValueError('config_schema_invalid')
 def visit(v):
  if isinstance(v,dict):
   for k,x in v.items():
    if k.lower() in {'api_key','token','api_token','password','access_token','secret'}:raise ValueError('secrets_must_be_stored_separately')
    visit(x)
  elif isinstance(v,list):
   for x in v:visit(x)
 visit(c)
 for section in ('project','search','translation','pdf','schedule','limits','notifications'):
  if not isinstance(c.get(section),dict):raise ValueError('config_section_required_'+section)
 from zoneinfo import ZoneInfo
 ZoneInfo(c['project']['timezone']);ZoneInfo(c['schedule']['timezone'])
 years=c['project']['years']
 if not isinstance(years,list)or not years or not all(type(y)is int and 1600<=y<=2200 for y in years):raise ValueError('project_years_required')
 if not isinstance(c['schedule'].get('journal_interval_days'),int)or not 1<=c['schedule']['journal_interval_days']<=366:raise ValueError('interval_1_to_366_days')
 if c['search']['mode'] not in ('agent','structured','hybrid'):raise ValueError('search_mode_invalid')
 if c['translation']['mode'] not in ('agent','api','disabled'):raise ValueError('translation_mode_invalid')
 if c['pdf']['mode'] not in ('disabled','cloud','local'):raise ValueError('pdf_mode_invalid')
 if c['schedule']['mode'] not in ('manual','external'):raise ValueError('schedule_mode_invalid')
 if not isinstance(c['journals'],list):raise ValueError('journals_must_be_list')
 names=[]
 for j in c['journals']:
  if not isinstance(j,dict) or not isinstance(j.get('name'),str) or not j['name'].strip():raise ValueError('journal_name_required')
  names.append(j['name'])
  if 'check_interval_days'in j and(type(j['check_interval_days'])is not int or not 1<=j['check_interval_days']<=366):raise ValueError('journal_interval_invalid')
  for issn in j.get('issns',[]):
   if not re.fullmatch(r'\d{4}-\d{3}[\dXx]',issn):raise ValueError('issn_format_invalid')
 if len(set(names))!=len(names):raise ValueError('duplicate_journal')
 for t in c['schedule']['times']:
  if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',t):raise ValueError('schedule_time_invalid')
 if any(type(v)is not int or not 0<=v<=1000 for v in c['limits'].values()):raise ValueError('limit_invalid')
 return c

class Workspace:
 def __init__(self,path):
  self.root=Path(path).expanduser().resolve()
  marker=self.root/'.frontierdock-workspace'
  if not marker.is_file() or marker.read_text().strip()!='frontierdock-v1':raise ValueError('not_a_frontierdock_workspace; run init in a new directory')
  self.config=validate_config(json.loads((self.root/'config.json').read_text()))
  self.db=self.root/'catalog.sqlite'
  if not self.db.is_file():raise ValueError('workspace_database_missing; ask your Agent to restore a backup')
 @contextmanager
 def connect(self):
  db=sqlite3.connect(self.db,timeout=10);db.row_factory=sqlite3.Row
  try:
   yield db;db.commit()
  except BaseException:db.rollback();raise
  finally:db.close()
 def records(self):
  with self.connect() as db:rows=db.execute('SELECT data FROM papers ORDER BY coalesce(date,\'\') DESC,id').fetchall()
  return [self.present(json.loads(r['data'])) for r in rows]
 def present(self,m):
  m=dict(m);valid=m.get('translation_source_hash')==fingerprint(m['title'],m.get('abstract'))
  if not valid:m['abstract_translation']=None
  if m.get('keywords_source_hash')!=fingerprint(m['title'],m.get('abstract')):m['model_keywords']=[]
  return m
 def get(self,rid):
  with self.connect() as db:r=db.execute('SELECT data FROM papers WHERE id=?',(rid,)).fetchone()
  return self.present(json.loads(r['data'])) if r else None
 def import_records(self,items):
  if not isinstance(items,list) or len(items)>5000:raise ValueError('records_list_max_5000')
  report={'added':0,'existing':0,'conflicts':0}
  with self.connect() as db:
   for value in items:
    m=validate_record(value,self.config['journals']);doi=str(m.get('doi')or'').lower();rid=('doi:'+doi) if doi else m.get('record_id')or('record:'+hashlib.sha256((m['journal']+'|'+m['title']).encode()).hexdigest()[:24]);m['record_id']=rid
    old=db.execute('SELECT data FROM papers WHERE id=? OR (doi IS NOT NULL AND doi=?)',(rid,doi or None)).fetchone()
    if old:
     previous=json.loads(old['data'])
     if normalize(previous['title'])!=normalize(m['title']) or previous['journal']!=m['journal']:
      db.execute('INSERT INTO conflicts(incoming,reason,created_at)VALUES(?,?,?)',(json.dumps(m,ensure_ascii=False),'identity_diff_preserved_existing',now()));report['conflicts']+=1
     else:report['existing']+=1
     continue
    db.execute('INSERT INTO papers VALUES(?,?,?,?,?,?,?)',(rid,doi or None,m['title'],m['journal'],m.get('publication_date'),m.get('year'),json.dumps(m,ensure_ascii=False)));report['added']+=1
  return report
 def enrich(self,items):
  report={'updated':0,'unchanged':0}
  with self.connect() as db:
   for v in items:
    r=db.execute('SELECT data FROM papers WHERE id=?',(v.get('record_id'),)).fetchone()
    if not r:raise ValueError('record_not_found')
    m=json.loads(r['data']);expected=fingerprint(m['title'],m.get('abstract'))
    if v.get('source_hash')!=expected:raise ValueError('source_fingerprint_mismatch')
    if v.get('abstract'):
     if m.get('abstract'):raise ValueError('existing_original_abstract_preserved')
     if v.get('abstract_kind')!='publisher_abstract' or not v.get('source_url'):raise ValueError('original_abstract_requires_publisher_source')
     if normalize(v.get('title'))!=normalize(m['title']) or str(v.get('doi')or'').lower()!=str(m.get('doi')or'').lower():raise ValueError('abstract_identity_mismatch')
     if not isinstance(v['abstract'],str) or not 30<=len(v['abstract'])<=100000:raise ValueError('abstract_length_invalid')
     from urllib.parse import urlsplit
     if urlsplit(v['source_url']).scheme not in ('https','http'):raise ValueError('source_url_invalid')
     m.update(abstract=v['abstract'],abstract_provenance={'url':v['source_url'],'method':'publisher_abstract','checked_at':now()});expected=fingerprint(m['title'],m['abstract'])
    if v.get('abstract_translation'):
     if not m.get('abstract'):raise ValueError('translation_requires_original')
     if not isinstance(v['abstract_translation'],str) or not 10<=len(v['abstract_translation'])<=100000:raise ValueError('translation_invalid')
     if v.get('translated_title') is not None and not isinstance(v['translated_title'],str):raise ValueError('translated_title_invalid')
     m.update(abstract_translation=v['abstract_translation'],translated_title=v.get('translated_title'),translation_source_hash=expected,translation_provenance={'provider':v.get('provider','agent'),'model':v.get('model','unspecified'),'created_at':now()})
    if v.get('model_keywords'):
     kw=v['model_keywords']
     if not m.get('abstract') or not isinstance(kw,list) or not 2<=len(kw)<=10 or not all(isinstance(x,str) and 0<len(x)<100 for x in kw):raise ValueError('keywords_require_abstract_and_2_to_10_terms')
     m.update(model_keywords=list(dict.fromkeys(kw)),keywords_source_hash=expected,keywords_provenance={'provider':v.get('provider','agent'),'model':v.get('model','unspecified'),'created_at':now()})
    db.execute('UPDATE papers SET data=? WHERE id=?',(json.dumps(m,ensure_ascii=False),m['record_id']));report['updated']+=1
  return report
 def reading_state(self,rid):
  with self.connect() as db:r=db.execute('SELECT * FROM reading WHERE id=?',(rid,)).fetchone()
  return {'record_id':rid,'status':r['status'] if r else 'unread','revision':r['revision'] if r else 0,'removed':bool(r['removed'])if r else False,'visibility_revision':r['visibility_revision']if r else 0,'in_library':bool(r),'history':[],'history_conflict':False}
 def all_reading(self):
  with self.connect()as db:rows=db.execute('SELECT * FROM reading').fetchall()
  return {r['id']:{'record_id':r['id'],'status':r['status'],'revision':r['revision'],'removed':bool(r['removed']),'visibility_revision':r['visibility_revision'],'in_library':True,'history':[],'history_conflict':False}for r in rows}
 def set_reading(self,rid,state,revision,removed=None):
  if not self.get(rid):raise ValueError('record_not_found')
  with self.connect() as db:
   db.execute('BEGIN IMMEDIATE');r=db.execute('SELECT * FROM reading WHERE id=?',(rid,)).fetchone();rev=(r['visibility_revision']if r else 0)if removed is not None else(r['revision']if r else 0)
   if type(revision)is not int or rev!=revision:raise RuntimeError('revision_conflict')
   if removed is None:
    if state not in ('unread','to_read','completed'):raise ValueError('reading_state_invalid')
    db.execute('INSERT INTO reading(id,status,revision)VALUES(?,?,1) ON CONFLICT(id)DO UPDATE SET status=excluded.status,revision=reading.revision+1',(rid,state))
   else:
    if type(removed)is not bool or not r:raise ValueError('visibility_invalid')
    db.execute('UPDATE reading SET removed=?,visibility_revision=visibility_revision+1 WHERE id=?',(int(removed),rid))
  return self.reading_state(rid)
 def quality(self):
  counts=Counter();by={}
  for m in self.records():
   c=by.setdefault(m['journal'],Counter());c['records']+=1
   if m.get('abstract'):
    c['abstracts']+=1
    if m.get('region')=='INT' and not m.get('abstract_translation') and self.config['translation']['mode']!='disabled':c['translations_pending']+=1
    c['model_keywords' if m.get('model_keywords') else 'keywords_pending']+=1
   else:c['abstracts_missing']+=1
  for c in by.values():counts.update(c)
  return {'checked_at':now(),'counts':dict(counts),'by_journal':{k:dict(v)for k,v in by.items()}}

def normalize(t):return ''.join(x.casefold()for x in str(t or '') if x.isalnum())
def validate_record(value,journals):
 if not isinstance(value,dict):raise ValueError('record_object_required')
 fields=('record_id','title','authors','doi','journal','publication_date','year','volume','issue','abstract','abstract_kind','abstract_language','source_url','date_kind','keywords','demo')
 m={k:value[k]for k in fields if k in value}
 if not isinstance(m.get('title'),str) or not m['title'].strip() or not 1<=len(m['title'])<=3000:raise ValueError('title_required')
 if m.get('journal') not in {j['name']for j in journals}:raise ValueError('journal_not_configured')
 if not isinstance(m.get('authors',[]),list) or not all(isinstance(a,str) or (isinstance(a,dict) and isinstance(a.get('name'),str)) for a in m.get('authors',[])):raise ValueError('authors_list_required')
 from urllib.parse import urlsplit
 if urlsplit(str(m.get('source_url',''))).scheme not in ('http','https'):raise ValueError('source_url_required')
 if 'keywords'in m and(not isinstance(m['keywords'],list)or not all(isinstance(x,str)and 0<len(x)<=200 for x in m['keywords'])):raise ValueError('keywords_array_of_strings_required')
 if m.get('doi'):
  m['doi']=re.sub(r'^https?://(?:dx\.)?doi.org/','',str(m['doi']),flags=re.I).lower()
  if not re.fullmatch(r'10\.\d{4,9}/\S+',m['doi']):raise ValueError('invalid_doi')
 if m.get('publication_date'):
  date.fromisoformat(m['publication_date'])
  if m.get('date_kind') not in ('online','print','publisher'):raise ValueError('publication_date_kind_required; indexing date is not publication date')
 if m.get('year') is not None and (type(m['year'])is not int or not 1600<=m['year']<=2200):raise ValueError('year_invalid')
 if m.get('abstract'):
  if not isinstance(m['abstract'],str) or m.get('abstract_kind') not in ('publisher_abstract','crossref_deposited','synthetic_demo'):raise ValueError('search_snippet_is_not_original_abstract')
  if not 30<=len(m['abstract'])<=100000 or normalize(m['abstract'])==normalize(m['title']) or re.fullmatch(r'(?:no abstract|abstract (?:not available|unavailable)|摘要(?:缺失|暂无|待补)).*',m['abstract'].strip(),re.I):raise ValueError('abstract_placeholder_or_length_invalid')
  if m['abstract_kind']=='synthetic_demo' and not m.get('demo'):raise ValueError('demo_label_required')
 meta=next(j for j in journals if j['name']==m['journal']);m['region']=meta.get('region','INT');m['authors']=m.get('authors',[]);m['imported_at']=now()
 return m

def initialize(path,demo=False):
 root=Path(path).expanduser().resolve()
 if root.exists() and any(root.iterdir()):raise ValueError('init_requires_empty_directory; existing files preserved')
 root.mkdir(parents=True,exist_ok=True);(root/'.frontierdock-workspace').write_text('frontierdock-v1')
 c=defaults()
 if demo:
  c['demo']=True;c['project']['field']='虚构跨学科演示';c['journals']=[{'name':'Frontier Methods — Fictional Journal','region':'INT','field':'示例研究方法','description':'虚构演示期刊，不用于学术引用。'},{'name':'开放研究观察（虚构）','region':'CN','field':'示例开放科学','description':'可替换为任何学科的期刊。'}]
 atomic_json(root/'config.json',c)
 with closing(sqlite3.connect(root/'catalog.sqlite')) as db:db.executescript(SCHEMA)
 w=Workspace(root)
 if demo:
  w.import_records([{'record_id':f'demo:{i}','title':t,'journal':c['journals'][i%2]['name'],'authors':['Example Researcher'],'publication_date':f'{date.today().year}-01-0{i+1}','date_kind':'publisher','year':date.today().year,'volume':1,'issue':1,'source_url':f'https://example.org/frontierdock/demo/{i}','abstract':a,'abstract_kind':'synthetic_demo','demo':True}for i,(t,a) in enumerate([('A fictional study of research signals','This synthetic abstract demonstrates a research discovery workflow. It is not a real publication and must not be cited.'),('如何构建可追溯的研究记录（虚构示例）','此摘要完全虚构，仅展示原始摘要、来源与阅读状态的页面效果。用户可以按自己的领域配置期刊与研究流程。')])])
  for m in w.records():
   value={'record_id':m['record_id'],'source_hash':fingerprint(m['title'],m['abstract']),'model_keywords':['虚构演示','研究流程','来源记录'] if m['region']=='INT'else['开放科学','可追溯性','资料管理'],'provider':'synthetic-demo','model':'fictional-example'}
   if m['region']=='INT':value.update(translated_title='关于研究信号的虚构研究',abstract_translation='这个虚构摘要演示研究发现的工作流程。它不是真实出版物，不应被引用。')
   w.enrich([value])
 return w
