import {esc as E} from '../model.js';
const num=n=>Number(n||0).toLocaleString('zh-CN');
function bars(rows,unit='篇',kind=''){
 const max=Math.max(1,...rows.map(r=>r.count));
 return rows.length?`<ol class="p4-stat-bars ${kind}">${rows.map((r,i)=>`<li><div class="p4-bar-caption"><span>${E(r.label)}</span><b>${num(r.count)}<small> ${unit}</small></b></div><div class="p4-bar-track" aria-hidden="true"><i style="width:${100*r.count/max}%;opacity:${1-i*.035}"></i></div></li>`).join('')}</ol>`:'<p class="p4-stat-empty">这个范围暂无可统计的关键词。</p>';
}
const card=(title,n,sub)=>`<article class="p4-stat-metric"><span>${title}</span><strong>${num(n)}</strong><small>${sub}</small></article>`;
export function analyticsPage(d){
 const region=d.region||'',year=d.year||'ALL',years=d.available_years||[];
 const opts=(values,value)=>values.map(([key,label])=>`<option value="${E(key)}" ${key===value?'selected':''}>${E(label)}</option>`).join('');
 return `<section class="page p4-analytics"><div class="page-head"><div><p class="p4-stat-eyebrow">COLLECTION INSIGHTS</p><h1>数据与方法</h1><p>从期刊构成到关键词，看看当前收藏的研究轮廓。</p></div><form data-light-form="data" class="p4-stat-filters"><label>期刊范围<select name="region">${opts([['','全部期刊'],['CN','中文期刊'],['INT','外文期刊']],region)}</select></label><label>题录年份<select name="year">${opts([['ALL','全部配置年份'],...years.map(y=>[y,y+' 年'])],year)}</select></label></form></div>
 <div class="p4-stat-metrics">${card('期刊',d.journal_count,`${num(d.active_journals)} 刊在所选年份有题录`)}${card('收录题录',d.total,'按工作区记录去重')}${card('可用摘要',d.abstracts,`${d.total?(100*d.abstracts/d.total).toFixed(1):0}% 的当前题录`)}${card('有关键词题录',d.keyword_records,`模型提取 ${num(d.keyword_sources?.model)} · 原字段 ${num(d.keyword_sources?.original)}`)}</div>
 <div class="p4-stat-grid"><section class="p4-stat-panel"><div class="p4-stat-heading"><span>01 / JOURNALS</span><h2>期刊领域分布</h2><p>按名录学科归类 · 共 ${num(d.journal_count)} 刊，不随年份改变</p></div>${bars(d.fields,'刊','p4-field-bars')}</section>
 <section class="p4-stat-panel"><div class="p4-stat-heading"><span>02 / COVERAGE</span><h2>题录年份分布</h2><p>当前收录量，体现库存覆盖而非研究产量</p></div>${bars(d.years,'篇','p4-year-bars')}</section>
 ${years.filter(y=>year==='ALL'||year===y).map((y,i)=>`<section class="p4-stat-panel ${year==='ALL'?'':'p4-single-year'}"><div class="p4-stat-heading"><span>0${i+3} / KEYWORDS</span><h2>${E(y)} 年高频关键词</h2><p>${num(d.year_keyword_records?.[y])} 篇有关键词题录 · 前 12 项</p></div>${bars(d.year_keywords?.[y]||[])}<p class="p4-stat-footnote">关键词来自原字段及摘要提取，数量表示库存篇次，不代表学界整体热度。</p></section>`).join('')}</div>
 <details class="p4-stat-method"><summary>统计口径与资料范围</summary><p>${E(d.scope)}。</p><p>${E(d.field_method)}</p><p>${E(d.keyword_method)}</p><p>${E(d.year_method)}</p><p>未使用 Search 网页摘要生成关键词；没有修改既有研究标签。摘要数量只统计非空且非占位的字段，不表示本轮已逐篇核验原文。模型提取词与原字段分别保留；两者可追溯到各篇论文。</p></details></section>`;
}
