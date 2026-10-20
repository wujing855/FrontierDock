import {esc as E} from '../model.js';
import {publicationForecast} from './p4-publication-forecast.js';
import {journalSummary,sharedDetailAnchorIndex} from './journal-card.js';
export {sharedDetailAnchorIndex};
export const journalKey=j=>j.journal_id||j.journal;
export const journalToggleId=key=>'light-journal-'+encodeURIComponent(key);
const source=value=>/^https?:\/\//i.test(value||'')?value:'';

// 同步记录只显示日期；带时区的原始时刻先转换为工作区时区对应的日期。
export function captureTime(value){
 if(typeof value!=='string')return '暂无记录';
 if(/^\d{4}-\d{2}-\d{2}$/.test(value)){
  const date=new Date(value+'T00:00:00Z');return Number.isFinite(date.getTime())&&date.toISOString().slice(0,10)===value?value:'暂无记录';
 }
 if(!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value))return '暂无记录';
 const date=new Date(value);if(!Number.isFinite(date.getTime()))return '暂无记录';
 const parts=Object.fromEntries(new Intl.DateTimeFormat('zh-CN',{timeZone:globalThis.FRONTIERDOCK_RUNTIME?.timezone||'UTC',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(date).map(p=>[p.type,p.value]));
 return `${parts.year}-${parts.month}-${parts.day}`;
}

export function issueLabel(x){return !x?'未取得刊期':`${x.year==='unknown'?'年份待核':x.year+'年'}${x.volume&&x.volume!=='unknown'?' · 第'+x.volume+'卷':''}${x.issue==='unknown'?' · 未归期 / 刊期待核':'第'+x.issue+'期'}`}
export function coverageLabel(c){
 if(!c?.first_issue)return '暂无明确刊期';
 if(c.has_special_issues)return `已收录 ${c.first_issue.year}—${c.last_issue.year}年 · ${c.issue_count}个刊期（含增刊等期号）`;
 return c.issue_count===1?`已收录 ${issueLabel(c.first_issue)}`:`已收录 ${issueLabel(c.first_issue)} — ${issueLabel(c.last_issue)} · ${c.issue_count}个刊期`;
}
export function issueDirectory(journal,issues){
 const years=[...new Set(issues.map(x=>x.year))],sum=k=>issues.reduce((n,x)=>n+(x[k]||0),0);
 return `<section class="p4-issue-directory"><p class="section-note">${sum('count')}条题录 · ${issues.filter(x=>x.issue!=='unknown'&&x.year!=='unknown').length}个已标注卷期 · 缺原摘要 ${sum('missing_abstracts')}篇${sum('abstract_not_required')?' · 勘误等无需摘要 '+sum('abstract_not_required')+'篇':''} · 英文摘要待译 ${sum('pending_translations')}篇</p><p class="section-note">仅展示已收录的期次与篇数，不代表整期完整。年份沿用题录来源年，部分为在线发表年，正式刊年另待核对；未归期单列。网页搜索摘要不算论文原始摘要。</p>${years.map(year=>`<section class="p4-issue-year"><h2>${E(year==='unknown'?'年份待核':year+'年')}</h2><div class="p4-issue-grid">${issues.filter(x=>x.year===year).map(x=>`<a class="p4-issue-card" href="#/journals?${E(new URLSearchParams({journal,tab:'papers',year:x.year,issue:x.issue,volume:x.volume||'unknown'}).toString())}"><strong>${x.volume&&x.volume!=='unknown'?'第'+E(x.volume)+'卷 · ':''}${E(x.issue==='unknown'?'未归期 / 刊期待核':'第'+x.issue+'期')}</strong><span>已收录 ${x.count}篇</span><small>原摘要 ${x.abstracts||0}篇 · 缺失 ${x.missing_abstracts||0}篇${x.abstract_not_required?' · 勘误等无摘要 '+E(x.abstract_not_required)+'篇':''}</small>${x.pending_translations?`<small>英文摘要待译 ${x.pending_translations}篇</small>`:''}${x.formal_year_unverified?`<small>正式刊年待核 ${x.formal_year_unverified}篇</small>`:''}<span class="text-btn">查看当期目录 →</span></a>`).join('')}</div></section>`).join('')||'<p>暂无题录，尚不能建立期次目录。</p>'}</section>`;
}

export function catalogCard(j,expanded=false){
 const key=journalKey(j),latest=j.latest_issue;
 const issue=j.coverage?coverageLabel(j.coverage):latest?`${latest.year}年${latest.issue!=='unknown'?' · 第'+latest.issue+'期':' · 刊期待核'}`:j.count?'刊期待核':'暂无收录';
 return `<article class="journal-card ${expanded?'is-expanded':''}" data-journal="${E(key)}"><button class="journal-card-hit" id="${journalToggleId(key)}" data-light-details="${E(key)}" aria-label="${E(j.name_zh||j.journal)}：查看或收起期刊详情" aria-controls="light-journal-details" aria-expanded="${expanded}"></button><div class="journal-card-summary"><div class="card-top"><span class="pill">${E(j.field||'目标期刊')}</span><span class="journal-region">${j.region==='CN'?'国内':'国外'}期刊</span></div><h2>${E(j.name_zh||j.journal)}</h2>${j.name_en?`<p class="english-name" lang="en">${E(j.name_en)}</p>`:''}<p class="description">${E(journalSummary(j.description||'期刊资料待核'))}</p><div class="card-bottom"><div class="card-latest"><span>${j.count?j.count+'条题录':'尚无题录'}</span><strong>${E(issue)}</strong></div><div class="card-actions"><a class="card-entry" href="#/journals?journal=${encodeURIComponent(j.journal)}">进入期刊目录</a></div></div></div></article>`;
}

function frequencyLabel(value=''){
 if(value.includes('连续'))return '连续出版';
 const annual=[...value.matchAll(/(\d{4})年(\d+)期/g)].sort((a,b)=>Number(b[1])-Number(a[1]))[0];
 return annual?`${annual[1]}年${annual[2]}期`:value.replace(/（[^）]*）|\([^)]*\)/g,'').trim();
}

export function catalogDetails(j){
 const url=source(j.official_url),captured=captureTime(j.last_sync_at||j.last_record_retrieved_at),forecast=publicationForecast(j);
 const forecastNote=forecast.status==='overdue'?'已过预测月份，待核验':forecast.status==='estimated'&&!forecast.anchored?'当前刊期待核验':'';
 return `<section id="light-journal-details" class="journal-row-detail" role="region" aria-labelledby="light-journal-title"><div class="shared-detail-header"><div><h3 id="light-journal-title">${E(j.name_zh||j.journal)}</h3>${j.name_en?`<p lang="en">${E(j.name_en)}</p>`:''}<div class="journal-detail-meta">${j.publication_frequency?`<span>${E(frequencyLabel(j.publication_frequency))}</span>`:''}${url?`<a href="${E(url)}" target="_blank" rel="noopener">官网 ↗</a>`:''}</div></div><button class="btn quiet" data-light-close-details>关闭详情 ×</button></div><div class="shared-detail-body"><div class="journal-profile"><p class="detail-description">${E(j.description||'简介待补充')}</p>${j.reading_value?`<p class="journal-reading-value" title="阅读建议">${E(j.reading_value)}</p>`:''}</div><dl class="journal-facts"><div><dt>上次同步时间</dt><dd>${captured==='暂无记录'?captured:`<time datetime="${E(j.last_sync_at||j.last_record_retrieved_at)}">${E(captured)}</time>`}</dd></div><div class="publication-forecast"><dt>预计下期出刊</dt><dd title="${E(forecast.note)}">${E(forecast.label)}${forecastNote?`<span class="schedule-note">${E(forecastNote)}</span>`:''}</dd></div>${j.issn?.length?`<div><dt>ISSN</dt><dd>${E(j.issn.join(' / '))}</dd></div>`:''}</dl></div></section>`;
}

// 只替换共享详情区，保留卡片、筛选框与焦点；展开不读取网络。
export function updateCatalogDetails(grid,list,key,columns=2){
 const cards=[...grid.querySelectorAll('.journal-card')];
 grid.querySelector('#light-journal-details')?.remove();
 for(const card of cards){
  const expanded=card.dataset.journal===key;
  card.classList.toggle('is-expanded',expanded);
  card.querySelector('[data-light-details]')?.setAttribute('aria-expanded',String(expanded));
 }
 const selected=list.find(j=>journalKey(j)===key);
 const anchor=sharedDetailAnchorIndex(list.map(journalKey),key,columns);
 if(selected&&cards[anchor])cards[anchor].insertAdjacentHTML('afterend',catalogDetails(selected));
}
