/* 期刊、题录和轻阅读页面。 */
import {esc as E} from '../model.js';
import {issueDirectory,catalogCard,catalogDetails,journalKey,journalToggleId,sharedDetailAnchorIndex,updateCatalogDetails} from './p4-journals.js';
import {originFor} from './p3-state.js';
import {updateLine,pendingList} from './p4-updates.js';
import {prefs,savePrefs} from '../store.js';
import {readingSubset,recentPapers} from './p4-view.js';
import {analyticsPage} from './p4-analytics.js';
import {renderContent} from './math-content.js';

export const readingNames={unread:'未读',to_read:'待读',completed:'已读'};
export function safeLink(value){try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)?u.href:''}catch{return ''}}
export const paperHref=id=>'#/reader/'+encodeURIComponent(id);
const author=m=>(m.authors||[]).map(a=>typeof a==='string'?a:a.name).filter(Boolean).join('、')||'作者待核';
const title=m=>m.translated_title||m.title||'题名待核';
export function abstractContent(m){
 const keyword=m.model_keywords?.length?`<section class="p4-derived-keywords"><small>摘要提取关键词</small><p>${m.model_keywords.map(k=>`<span>${E(k)}</span>`).join('')}</p></section>`:'';
 const source=safeLink(m.abstract_source_url)?`<p class="p4-supplement-source"><a href="${E(safeLink(m.abstract_source_url))}" target="_blank" rel="noopener">查看本次补全的摘要来源 ↗</a></p>`:'';
 if(m.abstract_translation&&m.abstract)return `<p class="p4-translation" lang="zh-CN">${renderContent(m.abstract_translation)}</p><details class="p4-original"><summary>英文原摘要</summary><p lang="en">${renderContent(m.abstract)}</p></details>${source}${keyword}`;
 return `<p>${renderContent(m.abstract||(m.abstract_requirement?'出版社勘误，无独立摘要。':'暂无摘要。'))}</p>${m.abstract&&m.region==='INT'?`<small class="muted">${m.translation_status==='source_changed_cache_not_used'?'原摘要已变更，旧译文未使用':'暂无匹配的中文摘要缓存'}</small>`:''}${source}${keyword}`;
}

let pageController,journalsCache,readingCache=null,readingCacheKey='';
const issueCache=new Map(),previewRecords=new Map();
function overviewOrigin(){try{const value=sessionStorage.getItem('frontierdock-ui-journal-overview');return value?.startsWith('#/journals')?value:'#/journals'}catch{return '#/journals'}}
let epoch=0,refresh,currentRecord,expandedJournal='',filterTimer,filterFocus,toastTimer,catalogView;
const gridColumns=()=>typeof matchMedia==='function'&&matchMedia('(max-width:1100px)').matches?1:2;
let lastColumns=gridColumns(),updateRevision=null,updatePolling=false,lastCheckId=0;
const importing=()=>Boolean(globalThis.FRONTIERDOCK_RUNTIME?.file_import);
// 从全目录分页读取近期题录。
export async function homeCatalog(read){
 const groups=[];
 for(let page=1;page<=6;page++){
  let group;
  try{group=await read(page===1?'catalog':'catalog?page='+page)}
  catch(error){if(error.name==='AbortError')throw error;groups.push({items:[],unavailable:true});break}
  groups.push(group);
  if(recentPapers(groups).length>=6||!(group.items||[]).length||page*(group.page_size||30)>=(group.total||0))break;
 }
 return groups;
}
async function refreshView(){
 const y=scrollY,hash=location.hash,open=[...document.querySelectorAll('.p3-doc details[open]')].map(d=>d.closest('[data-record]').dataset.record);
 await refresh?.();if(hash!==location.hash)return;
 for(const row of document.querySelectorAll('.p3-doc[data-record]'))if(open.includes(row.dataset.record))row.querySelector('details')?.setAttribute('open','');
 scrollTo({top:y,behavior:'instant'});
}
async function checkUpdates(){
 if(!importing()||updatePolling||document.visibilityState==='hidden')return;updatePolling=true;
 try{const status=await api('update-status');if(status.revision!==updateRevision&&!document.activeElement?.matches('input,select,textarea')){journalsCache=null;issueCache.clear();await refreshView();}else if(status.last_check?.id!==lastCheckId){const note=document.querySelector('[data-update-info]');if(note)note.outerHTML=updateLine(status);lastCheckId=status.last_check?.id}}catch{}finally{updatePolling=false}
}
if(typeof window!=='undefined'&&importing())window.setInterval(checkUpdates,10000);
async function api(path,body,signal){
 const controller=body===undefined?new AbortController():null;let timedOut=false;
 const abort=()=>controller?.abort();signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)abort();
 const timer=controller?setTimeout(()=>{timedOut=true;controller.abort()},12000):null;
 try{
  const response=await fetch('/api/v1/'+path,body===undefined?{signal:controller.signal}:{method:'POST',headers:{'Content-Type':'application/json','X-FrontierDock':'1'},body:JSON.stringify(body)});
  const data=await response.json();if(!response.ok){const error=Error(data.error||'暂时无法读取');error.status=response.status;throw error}return data;
 }catch(error){if(timedOut)throw Error('读取超时，请重试；已显示的内容保留。');throw error}
 finally{clearTimeout(timer);signal?.removeEventListener('abort',abort)}
}
function toast(text,undo){const box=document.getElementById('toast');box.innerHTML=E(text)+(undo?` <button data-light-undo="${E(undo.record_id)}" data-revision="${undo.visibility_revision}">撤销</button>`:'');box.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>box.classList.remove('show'),undo?8000:3000)}
const head=(name,description='',extra='')=>`<div class="page-head"><div><h1>${E(name)}</h1>${description?`<p>${E(description)}</p>`:''}</div>${extra}</div>`;
const stateSelect=(rid,reading)=>`<select data-light-state="${E(rid)}" data-revision="${reading.revision}" data-current="${reading.history_conflict?'':reading.status}" aria-label="阅读状态">${reading.history_conflict?'<option value="" selected disabled>历史状态待确认</option>':''}${Object.entries(readingNames).map(([key,name])=>`<option value="${key}" ${!reading.history_conflict&&key===reading.status?'selected':''}>${name}</option>`).join('')}</select>`;
const historyDetails=reading=>reading.history.length?`<details class="p4-history"><summary>历史阅读状态</summary>${reading.history.map(h=>`<p>${E(({unread:'待读',in_progress:'正在读',completed:'已读'})[h.raw_status]||h.raw_status)} <span class="muted">（原记录 ${E(h.raw_status)}，只读保留）</span></p>`).join('')}</details>`:'';
function personalRow(item){const m=item.metadata,r=item.reading;return `<article class="p3-doc" data-record="${E(m.record_id)}"><div><h3><a href="${paperHref(m.record_id)}">${E(title(m))}</a></h3><p>${E(author(m))}${m.journal?' · '+E(m.journal):''}</p></div><div class="p3-doc-actions"><a class="text-btn" href="${paperHref(m.record_id)}">阅读摘要</a>${r.removed?`<button class="text-btn" data-light-restore="${E(m.record_id)}" data-revision="${r.visibility_revision||0}">还原</button>`:stateSelect(m.record_id,r)+`<button class="text-btn p4-remove" data-light-remove="${E(m.record_id)}" data-revision="${r.visibility_revision||0}">移除</button>`}</div></article>`}
function pages(base,q,data){const count=Math.max(1,Math.ceil(data.total/data.page_size));return `<div class="pagination"><a class="btn" ${data.page<=1?'aria-disabled="true" tabindex="-1"':`href="#/${base}?${new URLSearchParams({...q,page:data.page-1})}"`}>上一页</a><span>${data.page} / ${count}</span><a class="btn" ${data.page>=count?'aria-disabled="true" tabindex="-1"':`href="#/${base}?${new URLSearchParams({...q,page:data.page+1})}"`}>下一页</a></div>`}

export async function renderLight(r,shell){
 pageController?.abort();
 const controller=new AbortController();pageController=controller;
 const read=path=>api(path,undefined,controller.signal);
 const request=++epoch,hash=location.hash;
 const expectedView=r.page==='reading'?'reading:'+(r.query.get('removed')==='1'?'removed':'active'):r.page==='journals'&&!r.query.get('journal')?'journal-overview':r.page==='search'?'search':r.page==='journals'?r.page+':'+(r.query.get('journal')||''):null;
 const localReadingKey=r.page==='reading'?(r.query.get('removed')==='1'?'removed':'active'):'';
 if(r.page!=='reading'||localReadingKey!==readingCacheKey)readingCache=null;
 readingCacheKey=localReadingKey;
 document.querySelector('#main')?.setAttribute('aria-busy','true');
 currentRecord=null;catalogView=null;
 refresh=()=>renderLight(r,shell);
 const paint=(html,section)=>{
  if(request!==epoch||hash!==location.hash)return;
  document.body.classList.remove('focus-mode');
  shell(html,section);
  document.querySelector('#main')?.removeAttribute('aria-busy');
  const status=document.querySelector('[data-light-search-status]');if(status)status.textContent='';

  const label=document.querySelector('.prototype-label');if(label)label.textContent=globalThis.FRONTIERDOCK_RUNTIME?.demo?'虚构演示数据':'本地工作区';
  const env=document.querySelector('.environment span');if(env)env.textContent=globalThis.FRONTIERDOCK_RUNTIME?.demo?'虚构演示工作区':'本地运行环境';
  const help=document.querySelector('[data-action="help"]');if(help)help.lastChild.textContent=' 关于';
  const top=document.querySelector('.top-label');if(section==='reader'&&top)top.textContent='论文摘要';
  document.title='FrontierDock · '+(section==='reader'?'论文摘要':document.querySelector('.top-label')?.textContent||'轻量模式');
  if(filterFocus?.hash===hash){const focus=filterFocus;filterFocus=null;const input=document.querySelector(`[data-light-form] [name="${focus.name}"]`);input?.focus({preventScroll:true});try{input?.setSelectionRange(focus.start,focus.end)}catch{}}
  if(section==='journals'&&!r.query.get('journal')){try{const y=Number(sessionStorage.getItem('frontierdock-p1-v1:scroll:'+hash)||0);requestAnimationFrame(()=>{if(hash===location.hash)scrollTo({top:y,behavior:'instant'})})}catch{}}
  try{const back=JSON.parse(sessionStorage.getItem('frontierdock-p3-return')||'null');if(back?.hash===hash){sessionStorage.removeItem('frontierdock-p3-return');for(const row of document.querySelectorAll('.p3-doc[data-record]'))if(back.expanded?.includes(row.dataset.record))row.querySelector('details')?.setAttribute('open','');requestAnimationFrame(()=>{if(hash===location.hash)scrollTo({top:back.y||0,behavior:'instant'})})}}catch{}
 };
 // 点击后立即更新导航，正文仍由当前请求的版本校验后替换。
 const activeSection=r.page==='reader'?(originFor(sessionStorage,r.id).hash.split('/')[1]?.split('?')[0]||'reading'):r.page;
 for(const link of document.querySelectorAll?.('.nav a')||[]){
  const selected=link.getAttribute('href')==='#/'+activeSection;
  link.classList.toggle('active',selected);
  if(selected)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
 }
 const topLabel=document.querySelector('.top-label');
 const pageName=({workbench:'研究工作台',journals:'期刊浏览',search:'论文检索',reading:'我的阅读',data:'数据与方法',reader:'论文摘要'})[r.page];
 if(topLabel&&pageName)topLabel.textContent=pageName;
 try{
  const journal=r.query.get('journal')||'',overview=r.page==='journals'&&!journal;
  const query=new URLSearchParams(Object.fromEntries(r.query));
  if(r.page==='reading'){
   const old=r.query.get('state')||r.query.get('tab')||'all';
   query.set('state','all');query.delete('q');
  }
  // 页面数据、更新提示和候选互不依赖，同时读取，避免逐项等待。
  const cachedJournals=overview?journalsCache:null;
  let [updates,candidates,pageData,issueData]=await Promise.all([
   importing()?read('update-status').catch(()=>null):null,
   importing()&&['journals','search'].includes(r.page)?read('candidates?'+new URLSearchParams({journal})).catch(()=>[]):[],
   overview?(journalsCache?Promise.resolve(journalsCache):read('journals').then(data=>{if(request===epoch)journalsCache=data;return data})):['journals','search'].includes(r.page)?read('catalog?'+query):r.page==='reader'?read('record?id='+encodeURIComponent(r.id)):r.page==='reading'?(readingCache||read('reading?'+query)):r.page==='workbench'?Promise.all([read('reading?state=to_read'),homeCatalog(read)]):null,
   r.page==='search'?(journalsCache||read('journals').then(data=>{if(request===epoch)journalsCache=data;return data})):r.page==='journals'&&journal?(issueCache.has(journal)?issueCache.get(journal):read('issues?journal='+encodeURIComponent(journal)).then(data=>{if(request===epoch)issueCache.set(journal,data);return data})):[]
  ]);
  if(request!==epoch||hash!==location.hash)return;
  // 同步版本在导航期间变化时，也不能复用旧目录缓存。
  if(updates&&cachedJournals&&updates.revision!==updateRevision){
   journalsCache=null;issueCache.clear();pageData=await read('journals');
   if(request!==epoch||hash!==location.hash)return;
   journalsCache=pageData;
  }
  if(updates){updateRevision=updates.revision;lastCheckId=updates.last_check?.id}
  if(r.page==='journals'&&!r.query.get('journal')){
   try{sessionStorage.setItem('frontierdock-ui-journal-overview',hash)}catch{}
   const journals=pageData,q=r.query.get('q')||'',region=r.query.get('region')||'ALL';
   const list=journals.filter(j=>(region==='ALL'||j.region===region)&&[j.journal,j.name_zh,j.description].join(' ').toLowerCase().includes(q.toLowerCase())).sort((a,b)=>Number(b.count>0)-Number(a.count>0));
   if(!list.some(j=>journalKey(j)===expandedJournal))expandedJournal='';
   catalogView={list,hash};lastColumns=gridColumns();const anchor=sharedDetailAnchorIndex(list.map(journalKey),expandedJournal,lastColumns),selected=list.find(j=>journalKey(j)===expandedJournal);
   paint(`<section class="page catalog-page" data-light-view="journal-overview">${head('期刊浏览')}<div data-light-notices>${updateLine(updates,journal)}${pendingList(candidates)}</div><form data-light-form="journals" class="filters p3-inline-form"><input name="q" type="search" aria-label="搜索期刊" placeholder="搜索期刊名称" value="${E(q)}"><select name="region" aria-label="国内外期刊">${[['ALL','全部期刊'],['CN','国内期刊'],['INT','国外期刊']].map(([k,v])=>`<option value="${k}" ${region===k?'selected':''}>${v}</option>`).join('')}</select></form><p class="p4-search-status" data-light-search-status role="status" aria-live="polite"></p><div data-light-results><div class="result-info" aria-live="polite"><span>${list.length}本目标期刊 · ${list.filter(j=>j.count>0).length}本有题录</span><span>实际收录题录，非完整年度总量</span></div><div class="journal-grid journal-catalog-grid">${list.map((j,i)=>catalogCard(j,journalKey(j)===expandedJournal)+(i===anchor&&selected?catalogDetails(selected):'')).join('')||'<p>没有匹配的期刊，试试其他刊名或地区。</p>'}</div></div></section>`,'journals');return;
  }
  if(r.page==='search'||r.page==='journals'){
   const journal=r.query.get('journal')||'',q=r.query.get('q')||'',year=r.query.get('year')||'',issue=r.query.get('issue')||'',base=r.page==='journals'?'journals':'search',date_from=r.query.get('date_from')||'',date_to=r.query.get('date_to')||'';
   const volume=r.query.get('volume')||'';
   const data=pageData,issues=issueData,journalOptions=r.page==='search'?issueData.map(j=>j.journal):[];
   previewRecords.clear();for(const m of data.items)previewRecords.set(m.record_id,m);
   const directory=r.page==='journals'&&journal&&(r.query.get('tab')==='directory'||(!r.query.get('tab')&&!year&&!issue&&!q&&!date_from&&!date_to));
   const journalTabs=journal&&r.page==='journals'?`<nav class="tabs" aria-label="期刊内容"><a href="#/journals?${E(new URLSearchParams({journal,tab:'directory'}).toString())}" class="${directory?'active':''}" ${directory?'aria-current="page"':''}>期刊目录</a><a href="#/journals?${E(new URLSearchParams({journal,tab:'papers'}).toString())}" class="${!directory?'active':''}" ${!directory?'aria-current="page"':''}>全部论文</a></nav>`:'';
   if(directory){paint(`<section class="page" data-light-view="issues:${E(journal)}"><a class="text-btn p4-back" href="${E(overviewOrigin())}">← 返回期刊总览</a>${head(journal)}${journalTabs}<div data-light-results>${issueDirectory(journal,issues)}</div></section>`,'journals');return}
   paint(`<section class="page p4-papers" data-light-view="${E(r.page==='search'?'search':base+':'+journal)}">${journal&&r.page==='journals'?`<a class="text-btn p4-back" href="${E(overviewOrigin())}">← 返回期刊总览</a>`:''}${head(r.page==='search'?'论文检索':journal)}${journalTabs}<div data-light-notices>${updateLine(updates,journal)}${pendingList(candidates)}</div><form data-light-form="${base}" class="filters p3-inline-form"><input name="q" type="search" aria-label="搜索论文" placeholder="题名、DOI 或作者" value="${E(q)}">${r.page==='search'?`<select name="journal" aria-label="筛选期刊"><option value="">全部期刊</option>${[...new Set([...journalOptions,...(journal?[journal]:[])])].map(j=>`<option value="${E(j)}" ${journal===j?'selected':''}>${E(j)}</option>`).join('')}</select>`:''}${r.page==='journals'&&journal?`<input name="journal" type="hidden" value="${E(journal)}"><input name="tab" type="hidden" value="papers"><input name="volume" type="hidden" value="${E(volume)}"><input name="issue" type="hidden" value="${E(issue)}"><label>年份 <select name="year"><option value="">全部年份</option>${[...new Set(issues.map(x=>x.year))].map(y=>`<option value="${E(y)}" ${y===year?'selected':''}>${E(y==='unknown'?'年份待核':y)}</option>`).join('')}</select></label>`:''}<label>发表日期 <input type="date" name="date_from" aria-label="发表日期起" value="${E(date_from)}"></label><label>至 <input type="date" name="date_to" aria-label="发表日期止" value="${E(date_to)}"></label></form><p class="p4-search-status" data-light-search-status role="status" aria-live="polite"></p><div data-light-results>${journal&&year?`<nav class="p3-issues" aria-label="横向刊期导航"><a class="btn ${!issue?'primary':''}" href="#/journals?${new URLSearchParams({journal,q,year,date_from,date_to})}">全部刊期</a>${issues.filter(x=>x.year===year).map(x=>`<a class="btn ${issue===x.issue&&(!volume||volume===x.volume)?'primary':''}" href="#/journals?${new URLSearchParams({journal,q,year,issue:x.issue,volume:x.volume||'unknown',date_from,date_to,tab:'papers'})}">${x.volume&&x.volume!=='unknown'?'第'+E(x.volume)+'卷 · ':''}${x.issue==='unknown'?'刊期待核':'第'+E(x.issue)+'期'} · ${x.count}</a>`).join('')}</nav>`:''}<p class="section-note">${year?E(year==='unknown'?'年份待核':year+'年')+' · ':''}${volume&&volume!=='unknown'?'第'+E(volume)+'卷 · ':''}${issue?E(issue==='unknown'?'未归期 / 刊期待核':'第'+issue+'期')+' · ':''}${data.total}条库存记录</p><div class="plain-list">${data.items.map(m=>`<article class="p3-doc" data-record="${E(m.record_id)}"><div><h3><a href="${paperHref(m.record_id)}">${E(title(m))}</a></h3>${m.translated_title?`<p class="p4-english-title" lang="en">${E(m.title)}</p>`:''}<p class="p4-paper-meta">${E(author(m))} · ${E(m.publication_date||'日期待核')}${journal?'':' · '+E(m.journal)}${m.scope_label?' · '+E(m.scope_label):''}</p><details class="p3-abstract-preview" data-light-preview="${E(m.record_id)}"><summary>展开摘要</summary><div data-light-abstract-body></div></details></div><div class="p3-doc-actions"><a class="text-btn" href="${paperHref(m.record_id)}">阅读摘要</a>${m.reading?.in_library&&!m.reading?.removed?`<a class="text-btn" href="#/reading?q=${encodeURIComponent(m.title)}">已在我的阅读</a>${stateSelect(m.record_id,m.reading)}`:`<button class="text-btn" data-light-save="${E(m.record_id)}">加入待读</button>`}</div></article>`).join('')||'<p>没有匹配的论文。</p>'}</div>${pages(base,{journal,q,year,issue,date_from,date_to,volume,tab:'papers'},data)}</div></section>`,base);return;
  }
  if(r.page==='reader'){
   const data=pageData;if(request!==epoch||hash!==location.hash)return;
   const m=data.metadata,reading=data.reading,origin=originFor(sessionStorage,r.id),theme=prefs().lightTheme||'rice';
   const source=safeLink(m.source_url),doi=m.doi?safeLink('https://doi.org/'+m.doi):'';
   paint(`<section class="page p3-record p4-record"><a class="text-btn" href="${E(origin.hash)}" data-light-return="${E(r.id)}">← ${origin.hash.startsWith('#/journals')?'返回期刊目录':origin.hash.startsWith('#/search')?'返回检索结果':origin.hash.startsWith('#/workbench')?'返回工作台':'返回我的阅读'}</a><article class="reader p4-abstract" data-theme="${['rice','night','white'].includes(theme)?theme:'rice'}"><p class="muted">${E(m.journal||'个人文献')}${m.scope_label?' · '+E(m.scope_label):''}${m.publication_date?' · '+E(m.publication_date):''}</p><h1 class="serif">${E(title(m))}</h1>${m.translated_title?`<p class="p4-english-title" lang="en">${E(m.title)}</p>`:''}<p>${E(author(m))}</p><div class="p3-actions">${source&&source!==doi?`<a class="text-btn" href="${E(source)}" target="_blank" rel="noopener">原文来源 ↗</a>`:''}${doi?`<a class="text-btn" href="${E(doi)}" title="DOI: ${E(m.doi)}" target="_blank" rel="noopener">查看原文 ↗</a>`:''}${stateSelect(r.id,reading)}${reading.in_library&&!reading.removed?'<span class="muted">已在我的阅读</span>':reading.removed?`<button class="text-btn" data-light-restore="${E(r.id)}" data-revision="${reading.visibility_revision}">重新加入我的阅读</button>`:''}<label class="p4-theme">阅读主题 <select id="p4-theme">${[['rice','米纸'],['white','清白'],['night','夜读']].map(([k,v])=>`<option value="${k}" ${theme===k?'selected':''}>${v}</option>`).join('')}</select></label></div><section class="reader-summary"><h2>摘要</h2>${abstractContent(m)}</section>${historyDetails(reading)}</article></section>`,'reader');currentRecord=data;return;
  }
  if(r.page==='reading'){
   const q=r.query.get('q')||'',old=r.query.get('state')||r.query.get('tab')||'all',state=({in_progress:'to_read',saved:'to_read'})[old]||(['unread','to_read','completed'].includes(old)?old:'all');
   const removed=r.query.get('removed')==='1';readingCache=pageData;
   const items=readingSubset(pageData.items,{q,state});
   paint(`<section class="page p32-reading p4-library" data-light-view="reading:${removed?'removed':'active'}">${head(removed?'已移除文献':'我的阅读','',`<a class="text-btn" href="#/reading${removed?'':'?removed=1'}">${removed?'返回我的阅读':'已移除'}</a>`)}<form data-light-form="reading" class="p4-library-filter">${removed?'<input type="hidden" name="removed" value="1">':''}<input type="search" name="q" aria-label="搜索我的阅读" placeholder="搜索题名、作者或 DOI" value="${E(q)}"><input type="hidden" name="state" value="${E(state)}"><div class="segment" role="group" aria-label="阅读状态筛选">${[['all','全部'],...Object.entries(readingNames)].map(([key,name])=>`<button type="button" data-light-reading-filter="${key}" aria-pressed="${key===state}" class="${key===state?'active':''}">${name}</button>`).join('')}</div></form><p class="p4-search-status" data-light-search-status role="status" aria-live="polite"></p><div data-light-results><p class="p4-list-count" aria-live="polite">${items.length} 篇${q||state!=='all'?` / 全部 ${pageData.items.length} 篇`:''}</p><div class="plain-list">${items.map(personalRow).join('')||`<div class="p32-empty"><h2>${removed?'没有已移除文献':q||state!=='all'?'没有匹配的文献':'这里还没有文献'}</h2><a class="text-btn" href="${q||state!=='all'?'#/reading':'#/journals'}">${q||state!=='all'?'清除筛选':'浏览期刊'}</a></div>`}</div></div></section>`,'reading');return;
  }
  if(r.page==='workbench'){
   const [reading,groups]=pageData,latest=recentPapers(groups),failed=groups.some(g=>g.unavailable);
   previewRecords.clear();for(const m of latest)previewRecords.set(m.record_id,m);
   paint(`<section class="page p4-workbench">${head('研究工作台')}<div class="p4-home-grid"><section class="p4-discovery"><div class="p4-section-head"><h2>期刊近期论文</h2><a class="text-btn" href="#/journals">浏览期刊</a></div><p class="p4-section-caption">各刊先展示一篇，按发表日期排列</p>${failed?'<p class="p4-inline-error" role="status">部分题录暂时无法读取，可稍后重新打开。</p>':''}<div class="plain-list">${latest.map(m=>`<article class="p3-doc" data-record="${E(m.record_id)}"><div><p class="p4-paper-meta">${E(m.journal)} · ${E(m.publication_date||'日期待核')}</p><h3><a href="${paperHref(m.record_id)}">${E(title(m))}</a></h3>${m.translated_title?`<p class="p4-english-title" lang="en">${E(m.title)}</p>`:''}<p class="p4-paper-meta">${E(author(m))}</p></div><div class="p3-doc-actions">${m.reading?.in_library&&!m.reading?.removed?`<span class="p4-saved-label">${E(readingNames[m.reading.status]||'已在我的阅读')}</span>`:`<button class="text-btn" data-light-save="${E(m.record_id)}">加入待读</button>`}</div></article>`).join('')||'<p class="section-note">暂时没有可显示的期刊论文。</p>'}</div></section><aside class="p4-home-reading"><div class="p4-section-head"><h2>我的待读</h2><span>${reading.items.length} 篇</span></div><div class="plain-list">${reading.items.slice(0,4).map(({metadata:m})=>`<article class="p4-reading-pick"><h3><a href="${paperHref(m.record_id)}">${E(title(m))}</a></h3><p>${E(author(m))}</p></article>`).join('')||'<p class="section-note">找到想读的论文后，加入待读。</p>'}</div><a class="text-btn" href="#/reading?state=to_read">查看全部待读</a></aside></div></section>`,'workbench');return;
  }
  if(r.page==='topics'){
   paint(`<section class="page">${head('研究专题已暂时停用')}<a class="text-btn" href="#/journals">前往期刊浏览</a></section>`,'journals');return;
  }
  if(r.page==='data'){
   const stats=await read('analytics?'+new URLSearchParams({region:r.query.get('region')||'',year:r.query.get('year')||''}));
   paint(analyticsPage(stats),'data');return;
  }
  paint(`<section class="page">${head('没有找到这个页面')}<a class="btn" href="#/journals">返回期刊浏览</a></section>`,'journals');
 }catch(error){if(error.name==='AbortError')return;
  const status=document.querySelector('[data-light-search-status]');
  if(status&&expectedView&&document.querySelector('[data-light-view]')?.dataset.lightView===expectedView&&request===epoch&&hash===location.hash){document.querySelector('#main')?.removeAttribute('aria-busy');const form=document.querySelector('[data-light-form]');form?.removeAttribute('aria-busy');status.innerHTML=E(error.message)+' <button class="text-btn" data-light-retry>重试</button>';return}
  paint(`<section class="page">${head('暂时无法读取')}<p role="alert">${E(error.message)}</p><button class="btn" data-light-retry>重新读取</button><a class="text-btn" href="#/journals">返回期刊浏览</a></section>`,r.page==='reader'?'reader':r.page)}
}

export const filterHash=(page,data)=>'#/'+page+'?'+new URLSearchParams(data);
function applyFilters(form,replace=false){
 if(!form.isConnected)return;clearTimeout(filterTimer);
 const fields=Object.fromEntries(new FormData(form));
 if(document.activeElement?.name==='year'){fields.issue='';fields.volume=''}
 if(fields.date_from&&fields.date_to&&fields.date_from>fields.date_to){const status=document.querySelector('[data-light-search-status]');if(status)status.textContent='起始日期不能晚于结束日期。';return}
 const hash=filterHash(form.dataset.lightForm,fields);
 if(hash===location.hash){form.removeAttribute('aria-busy');document.querySelector('#main')?.removeAttribute('aria-busy');const status=document.querySelector('[data-light-search-status]');if(status)status.textContent='';return;}
 const active=document.activeElement;
 if(form.contains(active)&&['q','region','year','state','date_from','date_to','journal'].includes(active.name))filterFocus={hash,name:active.name,start:active.selectionStart,end:active.selectionEnd};
 form.setAttribute('aria-busy','true');
 if(replace){history.replaceState({},'',hash);window.dispatchEvent(new Event('hashchange'))}else location.hash=hash;
}
// 只在用户展开时排版摘要，避免关闭的30条目录也预先渲染公式。
document.addEventListener('toggle',event=>{
 const details=event.target;if(!details.matches?.('[data-light-preview]')||!details.open)return;
 const body=details.querySelector('[data-light-abstract-body]'),record=previewRecords.get(details.dataset.lightPreview);
 if(body&&record&&!body.hasAttribute('data-rendered')){body.innerHTML=abstractContent(record);body.setAttribute('data-rendered','true')}
},true);
document.addEventListener('submit',event=>{const form=event.target.closest('[data-light-form]');if(!form)return;event.preventDefault();applyFilters(form)});
document.addEventListener('input',event=>{const input=event.target,form=input.closest('[data-light-form]');if(!form||input.type!=='search')return;clearTimeout(filterTimer);pageController?.abort();++epoch;if(event.isComposing)return;const status=document.querySelector('[data-light-search-status]');if(status)status.textContent='正在搜索…';const local=form.dataset.lightForm==='reading'||form.dataset.lightForm==='journals'&&!form.querySelector('[name=journal]');filterTimer=setTimeout(()=>applyFilters(form,true),local?70:180)});
document.addEventListener('compositionend',event=>{if(event.target.matches('[data-light-form] input[type=search]'))event.target.dispatchEvent(new Event('input',{bubbles:true}))});
document.addEventListener('click',async event=>{
 const filter=event.target.closest('[data-light-reading-filter]');if(filter){const form=filter.closest('form');form.elements.state.value=filter.dataset.lightReadingFilter;applyFilters(form);return}
 const confirmation=event.target.closest('[data-confirm-action]');if(confirmation){confirmation.disabled=true;try{const d=confirmation.dataset;await api('confirm-candidate',{batch_id:d.confirmBatch,candidate_id:d.confirmCandidate,action:d.confirmAction,record_id:d.confirmRecord||null});await refreshView();toast('已确认，原有资料保留')}catch(error){toast(error.message)}finally{confirmation.disabled=false}return}
 const details=event.target.closest('[data-light-details],[data-light-close-details]');if(details){
  const grid=document.querySelector('.journal-catalog-grid');if(!grid||catalogView?.hash!==location.hash)return;
  const previous=expandedJournal,closing=details.hasAttribute('data-light-close-details');
  expandedJournal=closing||details.dataset.lightDetails===expandedJournal?'':details.dataset.lightDetails;
  const y=scrollY;updateCatalogDetails(grid,catalogView.list,expandedJournal,gridColumns());
  if(closing)document.getElementById(journalToggleId(previous))?.focus({preventScroll:true});
  scrollTo({top:y,behavior:'instant'});return;
 }
 const visibility=event.target.closest('[data-light-remove],[data-light-restore],[data-light-undo]');if(visibility){visibility.disabled=true;const ds=visibility.dataset,rid=ds.lightRemove??ds.lightRestore??ds.lightUndo,y=scrollY;try{const result=await api('visibility',{record_id:rid,removed:visibility.hasAttribute('data-light-remove'),revision:Number(ds.revision)});readingCache=null;await refresh?.();requestAnimationFrame(()=>scrollTo({top:y,behavior:'instant'}));toast(result.removed?'已从我的阅读移除':'已还原',result.removed?result:null)}catch(error){if(error.status===409){readingCache=null;await refresh?.()}toast(error.message)}finally{visibility.disabled=false}return}
 const back=event.target.closest('[data-light-return]');if(back){event.preventDefault();event.stopImmediatePropagation();const origin=originFor(sessionStorage,back.dataset.lightReturn);sessionStorage.setItem('frontierdock-p3-return',JSON.stringify(origin));location.hash=origin.hash;return}
 if(event.target.closest('[data-light-retry]')){refresh?.();return}
 const button=event.target.closest('[data-light-save]');if(!button)return;
 button.disabled=true;
 try{const cached=previewRecords.get(button.dataset.lightSave)?.reading;const record=cached?{reading:cached}:await api('record?id='+encodeURIComponent(button.dataset.lightSave));const result=await api('reading',{record_id:button.dataset.lightSave,state:'to_read',revision:record.reading.revision});if(result.removed)await api('visibility',{record_id:button.dataset.lightSave,removed:false,revision:result.visibility_revision});readingCache=null;button.outerHTML=stateSelect(button.dataset.lightSave,result);toast('已加入待读')}catch(error){if(error.status===409){readingCache=null;previewRecords.clear();await refresh?.()}toast(error.message)}finally{button.disabled=false}
});
document.addEventListener('change',async event=>{
 const select=event.target;
 const form=select.closest('[data-light-form]');if(form&&(select.tagName==='SELECT'||select.type==='date')){applyFilters(form);return}
 if(select.id==='p4-theme'){savePrefs({lightTheme:select.value});const paper=document.querySelector('.p4-abstract');if(paper)paper.dataset.theme=select.value;return}
 if(!select.dataset.lightState)return;
 const previous=select.dataset.current;select.disabled=true;
 try{const result=await api('reading',{record_id:select.dataset.lightState,state:select.value,revision:Number(select.dataset.revision)});select.dataset.revision=result.revision;select.dataset.current=result.status;readingCache=null;toast('阅读状态已保存');if(currentRecord?.metadata.record_id===result.record_id)currentRecord.reading=result;else if(location.hash.startsWith('#/reading')||location.hash.startsWith('#/workbench'))await refreshView()}
 catch(error){select.value=previous;if(error.status===409){readingCache=null;await refresh?.()}toast(error.message)}finally{select.disabled=false}
});
if(typeof window!=='undefined')window.addEventListener('resize',()=>{const columns=gridColumns(),grid=document.querySelector('.journal-catalog-grid');if(grid&&catalogView?.hash===location.hash&&columns!==lastColumns){lastColumns=columns;updateCatalogDetails(grid,catalogView.list,expandedJournal,columns)}});
