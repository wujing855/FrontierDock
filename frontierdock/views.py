"""从当前库存生成 UI 视图；统计不代表期刊的完整出版总量。"""
from collections import Counter, defaultdict
import hashlib,json
from .core import now

def issues(w,journal,records=None):
 groups={}
 for m in records if records is not None else w.records():
  if m['journal']!=journal:continue
  key=tuple(str(m.get(k)or'unknown')for k in ('year','volume','issue'))
  g=groups.setdefault(key,dict(zip(('year','volume','issue'),key),count=0,abstracts=0,missing_abstracts=0,pending_translations=0,translated_abstracts=0))
  g['count']+=1;g['abstracts' if m.get('abstract') else 'missing_abstracts']+=1
  if m.get('abstract_translation'):g['translated_abstracts']+=1
  elif m.get('abstract') and m.get('region')=='INT' and w.config['translation']['mode']!='disabled':g['pending_translations']+=1
 return sorted(groups.values(),key=lambda g:tuple((int(g[k])if g[k].isdigit()else -1)for k in ('year','volume','issue')),reverse=True)

def journals(w):
 out=[];records=w.records()
 state=load_state(w)
 for j in w.config['journals']:
  name=j['name'];rows=[m for m in records if m['journal']==name];groups=issues(w,name,records)
  known=[g for g in groups if g['issue']!='unknown' and g['year']!='unknown']
  coverage={k:sum(g.get(k,0)for g in groups)for k in ('count','abstracts','missing_abstracts','translated_abstracts','pending_translations')}
  coverage.update(issue_count=len(known),unknown_issue_records=sum(g['count']for g in groups if g not in known),first_issue=known[-1]if known else None,last_issue=known[0]if known else None)
  out.append({**j,'journal':name,'journal_id':name,'issn':j.get('issns',[]),'count':len(rows),'latest_issue':known[0]if known else None,'coverage':coverage,'last_sync_at':state.get('journals',{}).get(name,{}).get('last_checked')})
 return out

def catalog(w,q):
 records=w.records();needle=q.get('q','').casefold()
 for k in ('journal','year','issue','volume'):
  if q.get(k):records=[m for m in records if str(m.get(k)or'unknown')==q[k]]
 if needle:records=[m for m in records if needle in json.dumps([m.get(k)for k in ('title','translated_title','authors','doi')],ensure_ascii=False).casefold()]
 if q.get('date_from'):records=[m for m in records if m.get('publication_date','')>=q['date_from']]
 if q.get('date_to'):records=[m for m in records if m.get('publication_date')and m['publication_date']<=q['date_to']]
 states=w.all_reading()
 total=len(records);page=max(1,min(int(q.get('page')or 1),max(1,(total+29)//30)))
 return {'total':total,'page':page,'page_size':30,'items':[{**m,'reading':states.get(m['record_id'])}for m in records[(page-1)*30:page*30]]}

def reading(w,q):
 removed=q.get('removed')=='1';state=q.get('state','all');items=[];states=w.all_reading()
 for m in w.records():
  r=states.get(m['record_id'])
  if not r:continue
  if r['in_library']and r['removed']==removed and(state=='all'or r['status']==state):items.append({'metadata':m,'reading':r})
 return {'items':items}

def analytics(w,q):
 records=w.records();region=q.get('region','');year=q.get('year')or'ALL'
 js=[j for j in w.config['journals']if not region or j.get('region')==region]
 all_rows=[m for m in records if not region or m.get('region')==region]
 years=sorted(set(str(m['year'])for m in all_rows if m.get('year'))|set(map(str,w.config['project']['years'])),reverse=True)
 rows=[m for m in all_rows if year=='ALL'or str(m.get('year'))==year]
 keywords={};keyword_counts={}
 for y in years:
  counter=Counter();count=0
  for m in all_rows:
   if str(m.get('year'))!=y:continue
   terms=m.get('model_keywords')or m.get('keywords')or[]
   if terms:count+=1;counter.update(set(terms))
  keywords[y]=[{'label':k,'count':n}for k,n in counter.most_common(12)];keyword_counts[y]=count
 return dict(region=region,year=year,available_years=years,total=len(rows),journal_count=len(js),active_journals=len(set(m['journal']for m in rows)),abstracts=sum(bool(m.get('abstract'))for m in rows),keyword_records=sum(bool(m.get('model_keywords')or m.get('keywords'))for m in rows),keyword_sources={'model':sum(bool(m.get('model_keywords'))for m in rows),'original':sum(bool(m.get('keywords'))and not m.get('model_keywords')for m in rows)},fields=[{'label':k,'count':v}for k,v in Counter(j.get('field')or'未分类'for j in js).most_common()],years=[{'label':k,'count':v}for k,v in sorted(Counter(str(m.get('year')or'待核')for m in all_rows).items(),reverse=True)],year_keywords=keywords,year_keyword_records=keyword_counts,scope='仅统计此工作区实际收录的题录，不代表整期完整或学界总体',field_method='领域由用户与 Agent 在期刊配置中共同确定。',keyword_method='原始关键词与根据原摘要提取的模型关键词分别保留；网页搜索摘要不参与提取。',year_method='年份来自题录来源的出版字段；在线发表年与正式卷期年可能不同，未归期不强行补齐。')

def load_state(w):
 p=w.root/'state.json'
 return json.loads(p.read_text())if p.is_file()else{'journals':{}}

def status(w):
 s=load_state(w);quality=w.quality()
 with w.connect()as db:conflicts=db.execute('SELECT count(*)FROM conflicts c LEFT JOIN conflict_reviews r ON c.id=r.conflict_id WHERE r.conflict_id IS NULL').fetchone()[0]
 revision=hashlib.sha256((str(w.db.stat().st_mtime_ns)+str((w.root/'config.json').stat().st_mtime_ns)).encode()).hexdigest()[:16]
 return {'enabled':True,'revision':revision,'last_success_at':s.get('last_run',{}).get('completed_at')if s.get('last_run',{}).get('sources')else None,'last_check':{'id':s.get('last_run',{}).get('started_at'),'status':'error'if s.get('last_run',{}).get('failures')else'ok','message':'部分来源未完成，请让 Agent 查看工作区的运行报告。'},'all_journals':{'quality':quality,'last_run':s.get('last_run'),'discovery_links':s.get('clues',[])[:30],'unresolved_conflicts':conflicts}}
