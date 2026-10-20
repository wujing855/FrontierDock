import unittest,tempfile,json,sqlite3,threading
from pathlib import Path
from datetime import datetime,timedelta,timezone,date
from unittest.mock import patch
from frontierdock.core import initialize,Workspace,defaults,validate_config,fingerprint,atomic_json
from frontierdock import views
from frontierdock.workflow import update,maintain,plan,doctor,agent_queue,run_lock,conflicts
from frontierdock.providers import crossref_record,rank_free_models,ProviderError,deepseek_search,derive

class CoreTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.w=initialize(self.root/'data',True)
  with self.w.connect()as db:
   for row in db.execute('SELECT id,data FROM papers').fetchall():
    m=json.loads(row['data']);m.pop('abstract_translation',None);m.pop('model_keywords',None);db.execute('UPDATE papers SET data=? WHERE id=?',(json.dumps(m),row['id']))
 def tearDown(self):self.temp.cleanup()
 def record(self,**kwargs):
  return dict(record_id='sample',title='An independently verified fictional test',journal=self.w.config['journals'][0]['name'],authors=['Example'],source_url='https://example.org/record',**kwargs)
 def test_refuse_nonempty_init(self):
  p=self.root/'occupied';p.mkdir();(p/'keep.txt').write_text('preserve')
  with self.assertRaises(ValueError):initialize(p)
  self.assertEqual((p/'keep.txt').read_text(),'preserve')
 def test_require_marker(self):
  with self.assertRaises(ValueError):Workspace(self.root)
 def test_blank_workspace_is_empty(self):self.assertEqual(initialize(self.root/'blank').records(),[])
 def test_no_fixed_journal_defaults(self):self.assertEqual(defaults()['journals'],[])
 def test_config_forbids_embedded_credentials(self):
  c=defaults();c['translation']['api_key']='not-a-real-key'
  with self.assertRaises(ValueError):validate_config(c)
 def test_config_years_and_intervals(self):
  c=defaults();c['project']['years']=[]
  with self.assertRaises(ValueError):validate_config(c)
  c=defaults();c['schedule']['journal_interval_days']=0
  with self.assertRaises(ValueError):validate_config(c)
 def test_unknown_journal_rejected(self):
  m=self.record();m['journal']='unconfigured'
  with self.assertRaises(ValueError):self.w.import_records([m])
 def test_search_summary_rejected(self):
  with self.assertRaises(ValueError):self.w.import_records([self.record(abstract='A search-related summary that is not an original abstract.',abstract_kind='search_summary')])
 def test_date_requires_publication_provenance(self):
  with self.assertRaises(ValueError):self.w.import_records([self.record(publication_date='2026-01-01',date_kind='indexed')])
 def test_partial_date_not_filled(self):
  self.w.import_records([self.record(year=2024)]);self.assertNotIn('publication_date',self.w.get('sample'))
 def test_duplicate_and_identity_conflict(self):
  m=self.record(doi='10.1234/example');self.assertEqual(self.w.import_records([m])['added'],1)
  self.assertEqual(self.w.import_records([m])['existing'],1)
  m['title']='Different identity';self.assertEqual(self.w.import_records([m])['conflicts'],1)
  self.assertNotEqual(self.w.get('doi:10.1234/example')['title'],m['title']);self.assertEqual(len(conflicts(self.w)),1)
 def test_reading_revision_and_restore(self):
  r=self.w.set_reading('demo:0','to_read',0)
  with self.assertRaises(RuntimeError):self.w.set_reading('demo:0','completed',0)
  r=self.w.set_reading('demo:0',None,0,True);self.assertTrue(r['removed'])
  r=self.w.set_reading('demo:0',None,1,False);self.assertFalse(r['removed']);self.assertEqual(r['status'],'to_read')
 def test_enrich_requires_matching_source(self):
  with self.assertRaises(ValueError):self.w.enrich([{'record_id':'demo:0','source_hash':'bad','abstract_translation':'not used'}])
 def test_original_abstract_preserved(self):
  m=self.w.get('demo:0')
  with self.assertRaises(ValueError):self.w.enrich([{'record_id':'demo:0','source_hash':fingerprint(m['title'],m['abstract']),'abstract':'Replacement original abstract that must not be accepted.'}])
 def test_abstract_identity_check(self):
  self.w.import_records([self.record()]);m=self.w.get('sample')
  with self.assertRaises(ValueError):self.w.enrich([{'record_id':'sample','source_hash':fingerprint(m['title'],None),'title':'Wrong title','abstract':'A long enough original-looking abstract from a different paper.','abstract_kind':'publisher_abstract','source_url':'https://example.org/wrong'}])
 def test_translation_and_keywords_fingerprint(self):
  m=self.w.get('demo:0');self.w.enrich([{'record_id':m['record_id'],'source_hash':fingerprint(m['title'],m['abstract']),'abstract_translation':'这是一段虚构的完整摘要译文，仅用来测试缓存与字段的来源指纹。','model_keywords':['虚构演示','研究流程']}])
  self.assertTrue(self.w.get('demo:0')['abstract_translation'])
  with self.w.connect()as db:
   raw=json.loads(db.execute('SELECT data FROM papers WHERE id=?',('demo:0',)).fetchone()[0]);raw['abstract']+=' Source changed.';db.execute('UPDATE papers SET data=? WHERE id=?',(json.dumps(raw),'demo:0'))
  changed=self.w.get('demo:0');self.assertIsNone(changed['abstract_translation']);self.assertEqual(changed['model_keywords'],[])
 def test_enrichment_transaction_rollback(self):
  m=self.w.get('demo:0')
  with self.assertRaises(ValueError):self.w.enrich([{'record_id':'demo:0','source_hash':fingerprint(m['title'],m['abstract']),'model_keywords':['a','b']},{'record_id':'missing'}])
  self.assertFalse(self.w.get('demo:0').get('model_keywords'))
 def test_unknown_issue_remains_unknown(self):
  self.w.import_records([self.record(year=2024)]);g=next(x for x in views.issues(self.w,self.record()['journal'])if x['year']=='2024');self.assertEqual(g['issue'],'unknown')
 def test_dynamic_analytics_year(self):
  self.w.import_records([self.record(year=2024)]);d=views.analytics(self.w,{'year':'2024'});self.assertEqual(d['total'],1);self.assertIn('2024',d['available_years'])
 def test_original_keywords_count(self):
  self.w.import_records([self.record(year=2024,keywords=['reproducibility','research'])]);d=views.analytics(self.w,{'year':'2024'});self.assertEqual(d['keyword_sources']['original'],1)
 def test_agent_mode_does_not_call_provider(self):
  with patch('frontierdock.workflow.crossref',side_effect=AssertionError('must not call')),patch('frontierdock.workflow.deepseek_search',side_effect=AssertionError('must not call')):
   r=update(self.w);self.assertEqual(r['new'],0);self.assertEqual(r['agent_queue']['status'],'awaiting_agent')
 def test_due_check_does_not_repeat(self):
  update(self.w);self.assertEqual(plan(self.w)['due_count'],0);self.assertEqual(update(self.w)['status'],'nothing_due')
 def test_lock_prevents_concurrent_run(self):
  with run_lock(self.w):
   with self.assertRaises(ValueError):update(self.w)
  self.assertFalse((self.w.root/'.run.lock').exists())
 def test_request_limit_and_existing_data(self):
  baseline=len(self.w.records())
  self.w.config['search']['mode']='structured';self.w.config['journals'][0]['issns']=['1234-567X'];self.w.config['limits']['max_journals_per_run']=1
  with patch('frontierdock.workflow.crossref',return_value=([self.record()],['partial']))as provider:
   report=update(self.w);self.assertEqual(report['checked_journals'],1);self.assertEqual(report['new'],1);self.assertEqual(provider.call_count,1)
  self.assertEqual(len(self.w.records()),baseline+1)
 def test_maintenance_budget(self):
  self.w.config['translation'].update(mode='api',model='test-model');self.w.config['limits']['max_model_calls_per_run']=1
  def answer(m,c):return {'record_id':m['record_id'],'source_hash':fingerprint(m['title'],m['abstract']),'model_keywords':['test','example']}
  with patch('frontierdock.workflow.derive',side_effect=answer):r=maintain(self.w)
  self.assertEqual(r['model_calls'],1);self.assertEqual(r['updated'],1)
 def test_free_only_without_inventory_no_calls(self):
  self.w.config['translation'].update(mode='api',free_only=True)
  with patch('frontierdock.workflow.derive',side_effect=AssertionError('must not call')):self.assertEqual(maintain(self.w)['model_calls'],0)
 def free_inventory(self):
  checked=datetime.now(timezone.utc).isoformat();expiry=str(date.today()+timedelta(days=1))
  atomic_json(self.w.root/'free-model-inventory.json',[dict(model=name,expires_at=expiry,remaining_tokens=1000,checked_at=checked,free_confirmed=True,stop_when_exhausted=True,text_generation=True,quality_rank=rank)for name,rank in [('first',90),('second',80)]])
  self.w.config['translation'].update(mode='api',free_only=True);self.w.config['limits']['max_model_calls_per_run']=2
 def test_free_quota_failure_advances_within_budget(self):
  self.free_inventory();called=[]
  def answer(m,c):
   called.append(c['model'])
   if c['model']=='first':raise ProviderError('free_quota_exhausted')
   return {'record_id':m['record_id'],'source_hash':fingerprint(m['title'],m['abstract']),'model_keywords':['test','example']}
  with patch('frontierdock.workflow.derive',side_effect=answer):report=maintain(self.w)
  self.assertEqual(called,['first','second']);self.assertEqual(report['model_calls'],2);self.assertEqual(report['updated'],1)
 def test_auth_failure_does_not_rotate_models(self):
  self.free_inventory()
  with patch('frontierdock.workflow.derive',side_effect=ProviderError('http_403'))as provider:report=maintain(self.w)
  self.assertEqual(provider.call_count,1);self.assertEqual(report['updated'],0)
 def test_database_integrity(self):self.assertEqual(doctor(self.w)['integrity'],'ok')

class ProviderTests(unittest.TestCase):
 def test_crossref_issn_identity(self):
  j={'name':'Any field journal','issns':['1234-567X']};item={'DOI':'10.1234/test','title':['A &amp; B'],'ISSN':['8765-4321']}
  self.assertIsNone(crossref_record(item,j));item['ISSN']=j['issns'];item['indexed']={'date-parts':[[2026,2,1]]}
  m=crossref_record(item,j);self.assertEqual(m['title'],'A & B');self.assertNotIn('publication_date',m)
 def test_crossref_partial_date(self):
  item={'DOI':'10.1234/test','title':['Paper'],'ISSN':['1234-567X'],'published-online':{'date-parts':[[2024,3]]}}
  m=crossref_record(item,{'name':'test','issns':['1234-567X']});self.assertEqual(m['year'],2024);self.assertNotIn('publication_date',m)
 def test_search_only_clues(self):
  with patch('frontierdock.providers.get_secret',return_value='temporary-test'),patch('frontierdock.providers.json_request',return_value={'results':[{'title':'x','url':'https://example.org','summary':'not Abstract','date':'2026-01-01'}]}):r=deepseek_search('test')
  self.assertEqual(r[0]['kind'],'web_clue');self.assertNotIn('abstract',r[0]);self.assertNotIn('date',r[0])
 def test_search_query_limit(self):
  with self.assertRaises(ValueError):deepseek_search('x'*129)
 def test_free_inventory_expiry_then_quality(self):
  today=date.today();checked=datetime.now(timezone.utc).isoformat();base=dict(remaining_tokens=1,stop_when_exhausted=True,free_confirmed=True,text_generation=True,checked_at=checked)
  inventory=[dict(base,model='later-best',expires_at=str(today+timedelta(days=2)),quality_rank=100),dict(base,model='early-low',expires_at=str(today+timedelta(days=1)),quality_rank=50),dict(base,model='early-best',expires_at=str(today+timedelta(days=1)),quality_rank=80)]
  self.assertEqual([x['model']for x in rank_free_models(inventory)],['early-best','early-low','later-best'])
 def test_free_inventory_stale_exhausted_or_unprotected(self):
  base=dict(model='not-free',expires_at=str(date.today()+timedelta(days=2)),remaining_tokens=0,stop_when_exhausted=True,free_confirmed=True,text_generation=True,quality_rank=90,checked_at=datetime.now(timezone.utc).isoformat())
  self.assertEqual(rank_free_models([base]),[]);base['remaining_tokens']=100;base['stop_when_exhausted']=False;self.assertEqual(rank_free_models([base]),[])
  base['stop_when_exhausted']=True;base['checked_at']=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat();self.assertEqual(rank_free_models([base]),[])
 def test_truncated_model_output_not_saved(self):
  with patch('frontierdock.providers.get_secret',return_value='temporary-test'),patch('frontierdock.providers.json_request',return_value={'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}):
   with self.assertRaises(ProviderError):derive({'record_id':'x','title':'x','abstract':'source','region':'INT'},{'model':'test','base_url':'https://example.org/v1'})

if __name__=='__main__':unittest.main()
