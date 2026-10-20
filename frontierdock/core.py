"""独立工作区、来源记录和字段维护；不读取任何外部观察站。"""
from pathlib import Path
from contextlib import contextmanager,closing
from datetime import datetime,date,timezone
from collections import Counter
import hashlib,json,sqlite3,os,tempfile,re,random

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

DEMO_JOURNALS=[
 {'name':'Frontier Methods — Fictional Journal','region':'INT','field':'示例研究方法','description':'虚构演示期刊，用来展示卷期目录、原摘要与译文阅读。不用于学术引用。','publication_frequency':'季刊'},
 {'name':'开放研究观察（虚构）','region':'CN','field':'示例开放科学','description':'虚构演示期刊，展示中文题录与阅读状态的页面效果。可以替换为任何学科的期刊。','publication_frequency':'双月刊'},
 {'name':'Computational Inquiry Review（虚构）','region':'INT','field':'示例计算社会科学','description':'虚构演示期刊，用于展示关键词统计与逐年分布。','publication_frequency':'月刊'},
 {'name':'交叉学科评论（虚构）','region':'CN','field':'示例交叉学科','description':'虚构演示期刊，展示跨学科题录的组织方式。','publication_frequency':'半年刊'},
]
DEMO_TOPICS=[
 ('人工智能',9,'artificial intelligence'),('大语言模型',9,'large language models'),('AI',8,'AI'),
 ('智能体',5,'agents'),('机器学习',4,'machine learning'),('多模态',4,'multimodal models'),('检索增强',4,'retrieval augmentation'),
 ('提示工程',3,'prompt engineering'),('知识图谱',3,'knowledge graphs'),
 ('文献计量',2,'bibliometrics'),('同行评议',2,'peer review'),('开放获取',2,'open access'),('学术写作',2,'academic writing'),
 ('可复现性',2,'reproducibility'),('数据治理',2,'data governance'),('语义检索',2,'semantic search'),
 ('自动摘要',1,'automatic summarisation'),('引用网络',1,'citation networks'),('预印本',1,'preprints'),('计算社会科学',1,'computational social science'),
 ('数字人文',1,'digital humanities'),('模型评估',1,'model evaluation'),('认知负荷',1,'cognitive load'),('文本挖掘',1,'text mining'),
 ('科研伦理',1,'research ethics'),('版本追踪',1,'version tracking'),('实验记录',1,'lab notebooks'),
]
ISSUE_MONTHS={0:[1,4,7,10],1:[1,3,5,7,9,11],2:list(range(1,13)),3:[3,9]}

def demo_corpus(count=400):
 """确定性生成虚构题录，让关键词统计有真实的长尾分布，不含任何真实论文。"""
 rng=random.Random(20261020);words=[t[0] for t in DEMO_TOPICS];weights=[t[1] for t in DEMO_TOPICS];english=[t[2] for t in DEMO_TOPICS]
 rows=[]
 for n in range(count):
  j=rng.choices([0,1,2,3],weights=[18,24,46,12])[0]
  year=rng.choices([2024,2025,2026],weights=[18,34,48])[0]
  month=rng.choice(ISSUE_MONTHS[j]);issue=ISSUE_MONTHS[j].index(month)+1
  picked=list(dict.fromkeys(rng.choices(words,weights=weights,k=6)))[:6]
  if len(picked)<3:picked=(picked+words[:3])[:3]
  en=[english[words.index(k)] for k in picked[:2]]
  if j in (0,2):
   title=rng.choice([f'A fictional study of {en[0]} and {en[1]} ({n})',f'Notes on {en[0]} in research workflows (fictional {n})',f'Toward {en[0]}: a synthetic record ({n})'])
   abstract=f'Fictional entry {n} on {en[0]}. The abstract is generated from a fixed template so that this demo can show how a stored original abstract, a translation and extracted keywords relate to each other. It describes no real study and must not be cited.'
   row={'tr':f'这条合成摘要围绕{picked[0]}与{picked[1]}展开，用来演示译文与原摘要的对应关系。内容完全虚构，不对应任何真实研究，不能用于引用。'}
  else:
   title=rng.choice([f'{picked[0]}与{picked[1]}：虚构研究记录 {n}',f'{picked[0]}视角下的{picked[1]}（虚构示例 {n}）',f'关于{picked[0]}的合成实验笔记 {n}'])
   abstract=f'这是第 {n} 条虚构题录，主题围绕{picked[0]}与{picked[1]}。摘要由固定模板生成，用来演示原摘要、译文与关键词之间的关系，不对应任何真实研究，不能用于引用。'
   row={}
  row.update({'j':j,'year':year,'month':month,'volume':year-2023,'issue':issue,'title':title,'abstract':abstract,'keywords':picked})
  rows.append(row)
 return rows

DEMO_RECORDS=[
 {'j':0,'year':2026,'month':1,'volume':1,'issue':1,'title':'A fictional study of research signals','abstract':'This synthetic abstract demonstrates a research discovery workflow: a journal directory, an issue list, a verified abstract and a reading queue. It is not a real publication and must not be cited.','keywords':['研究信号','发现流程','来源校验'],'tt':'关于研究信号的虚构研究','tr':'这个虚构摘要演示研究发现的工作流程：期刊目录、卷期列表、经核对的摘要与阅读队列。它不是真实出版物，不应被引用。'},
 {'j':1,'year':2026,'month':1,'volume':1,'issue':1,'title':'如何构建可追溯的研究记录（虚构示例）','abstract':'此摘要完全虚构，仅用来展示原始摘要、来源链接与阅读状态的页面效果。使用者可以按自己的领域配置期刊、检索方式与维护节奏。','keywords':['可追溯性','研究记录','开放科学']},
 {'j':2,'year':2026,'month':3,'volume':1,'issue':3,'title':'Agent-assisted literature screening: a fictional benchmark','abstract':'A fictional benchmark asks whether an Agent can separate verified abstracts from search snippets. Every item in this demo is invented; the numbers are illustrative and were never measured on a real corpus.','keywords':['文献筛选','智能体','基准测试'],'tt':'智能体辅助文献筛选：一个虚构基准','tr':'这个虚构基准考察 Agent 能否把经核对的摘要与检索片段区分开。演示中的每一项都是编造的，数字仅作示意，从未在真实语料上测量。'},
 {'j':3,'year':2025,'month':11,'volume':2,'issue':2,'title':'跨学科阅读清单的组织方式（虚构示例）','abstract':'虚构的跨学科清单示例：同一批题录按领域、年份与关键词分别归类，阅读状态独立保存，移除之后仍可还原。','keywords':['阅读清单','跨学科','知识组织']},
 {'j':0,'year':2026,'month':4,'volume':1,'issue':2,'title':'Provenance labels for machine-translated abstracts','abstract':'Fictional note on provenance: a translation carries the fingerprint of the title and abstract it came from, and stale derived text is hidden instead of shown silently.','keywords':['来源标注','机器翻译','摘要'],'tt':'机器翻译摘要的来源标注','tr':'关于来源标注的虚构说明：译文携带来源题名与摘要的指纹，来源变更后旧译文会被隐藏，不会悄悄展示。'},
 {'j':2,'year':2026,'month':2,'volume':1,'issue':2,'title':'Keyword drift in a synthetic corpus','abstract':'A synthetic corpus shows how extracted keywords move across two publication years. The vocabulary here is deliberately invented so that no real research trend is implied.','keywords':['关键词漂移','语料分析','逐年统计'],'tt':'合成语料中的关键词漂移','tr':'一个合成语料展示提取关键词在两个出版年份之间的变化。这里的词表是刻意编造的，不暗示任何真实研究趋势。'},
 {'j':1,'year':2025,'month':7,'volume':1,'issue':6,'title':'开放获取期刊的目录核对流程（虚构示例）','abstract':'虚构流程说明：库存空档不等于出版空档，需要对照出版方目录逐期核对；核对不了的期号保持未知，不为了填齐而补写。','keywords':['目录核对','开放获取','期刊管理']},
 {'j':2,'year':2025,'month':5,'volume':1,'issue':1,'title':'Reading queues as a research instrument','keywords':['阅读队列','研究习惯','工作流']},
 {'j':3,'year':2025,'month':3,'volume':2,'issue':1,'title':'Peer review metadata: a fictional audit','abstract':'A fictional audit of peer review metadata: what is recorded, what is missing and what must stay unknown. Nothing in this entry describes a real journal or a real review.','keywords':['同行评议','元数据','审计'],'tt':'同行评议元数据：一次虚构审计','tr':'一次对同行评议元数据的虚构审计：记录了什么、缺了什么、哪些必须保持未知。这一条不描述任何真实期刊或真实评审。'},
 {'j':0,'year':2025,'month':9,'volume':1,'issue':4,'title':'Issue coverage gaps in local catalogues','abstract':'A fictional account of coverage gaps: local stock never implies a complete issue or a complete year, and partial retrieval stays visibly partial in every view.','keywords':['卷期覆盖','本地目录','缺口记录'],'tt':'本地目录中的卷期缺口','tr':'关于卷期缺口的虚构说明：本地库存从不代表整期或整年完整，任何页面上，部分检索都保持可见的“部分”。'},
]

def initialize(path,demo=False):
 root=Path(path).expanduser().resolve()
 if root.exists() and any(root.iterdir()):raise ValueError('init_requires_empty_directory; existing files preserved')
 root.mkdir(parents=True,exist_ok=True);(root/'.frontierdock-workspace').write_text('frontierdock-v1')
 c=defaults()
 if demo:
  c['demo']=True;c['project']['field']='虚构跨学科演示';c['project']['years']=[2024,2025,2026];c['journals']=DEMO_JOURNALS
 atomic_json(root/'config.json',c)
 with closing(sqlite3.connect(root/'catalog.sqlite')) as db:db.executescript(SCHEMA)
 w=Workspace(root)
 if demo:
  rows=DEMO_RECORDS+demo_corpus()
  values=[]
  for i,d in enumerate(rows):
   value={'record_id':f'demo:{i}','title':d['title'],'journal':c['journals'][d['j']]['name'],'authors':['Example Researcher'],'publication_date':f"{d['year']}-{d['month']:02d}-01",'date_kind':'publisher','year':d['year'],'volume':d['volume'],'issue':d['issue'],'source_url':f'https://example.org/frontierdock/demo/{i}','demo':True}
   if d.get('abstract'):value.update(abstract=d['abstract'],abstract_kind='synthetic_demo')
   values.append(value)
  w.import_records(values)
  hashes={m['record_id']:fingerprint(m['title'],m.get('abstract') or '') for m in w.records()}
  enrich=[]
  for i,d in enumerate(rows):
   if not d.get('abstract'):continue
   value={'record_id':f'demo:{i}','source_hash':hashes[f'demo:{i}'],'model_keywords':d['keywords'],'provider':'synthetic-demo','model':'fictional-example'}
   if d.get('tr'):value.update(abstract_translation=d['tr'])
   if d.get('tt'):value.update(translated_title=d['tt'])
   enrich.append(value)
  w.enrich(enrich)
 return w
