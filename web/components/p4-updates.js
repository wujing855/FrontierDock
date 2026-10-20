import {esc as E} from '../model.js';
import {captureTime} from './p4-journals.js';
export function updateLine(status,journal=''){
 if(!status?.enabled)return '';
 const all=status.all_journals||{},review=all.discovery_review,quality=all.quality;
 const counts=journal?quality?.by_journal?.[journal]:quality?.counts;
 const resolved=all.identity_review?.items?.length||0;
 const conflicts=Math.max(0,(all.last_run?.conflicts||0)-resolved);
 const link=value=>/^https?:\/\//.test(value||'')?value:'';
 const identity=all.identity_review?.items||[];
 return `<div class="p4-update-info" data-update-info data-update-revision="${E(status.revision||'')}"><span>刊物更新检查 ${E(captureTime(status.last_success_at))}</span>
 ${!journal&&all.last_run?`<span>本轮检查 ${E(all.last_run.checked_journals)} 刊 · 新增 ${E(all.last_run.new)} 条题录${conflicts?' · '+E(conflicts)+' 条题录差异由维护程序核对':''}${resolved?' · '+E(resolved)+' 条题名版本差异已核对':''}</span>`:''}
 ${all.unresolved_conflicts?`<span>身份冲突 ${E(all.unresolved_conflicts)} 条，待 Agent 核对来源</span>`:''}
 ${all.last_run?.agent_pending?.length?`<span>待 Agent 执行 ${E(all.last_run.agent_pending.length)} 刊，尚未完成检索</span>`:''}
 ${counts?`<span>质量盘点 ${E(captureTime(quality.checked_at))} · ${journal?'本刊':'全库'}摘要待补 ${E(counts.abstracts_missing||0)} 篇 · 译文待补 ${E(counts.translations_pending||0)} 篇 · 关键词待补 ${E(counts.keywords_pending||0)} 篇</span>`:''}
 ${!journal&&quality?`<details><summary>维护与核对进度</summary><p>文件批次待确认 ${E(quality.file_candidates_pending||0)} 条。来源与题录身份由维护程序与用户选择的 Agent 核对；译文和关键词由所选处理方式生成并记录来源。</p><p>有摘要不表示已经人工精读。缺原摘要的记录继续进入维护队列；出版社未提供摘要的勘误等另行标明。阅读状态独立保存。</p>${identity.map(x=>`<p><strong>${E(x.journal)}</strong> · DOI ${E(x.doi)}<br>${E(x.existing_titles?.join('；'))} ／ ${E(x.incoming_title)}<br>${E(x.decision)}</p>`).join('')}</details>`:''}
 ${!journal&&review?.count?`<details class="p4-clue-review"><summary>旧搜索线索核对结果 · ${E(review.count)} 条</summary><p>入口页、已收录题录、误匹配和访问受限分别保留。</p><div class="p4-review-items">${review.items.map(x=>`<p><span class="p4-clue-status">${E(x.label)}</span><strong>${E(x.journal)}</strong> · ${E(x.reason)}${link(x.official_url)?` <a href="${E(link(x.official_url))}" target="_blank" rel="noopener">期刊入口 ↗</a>`:''}</p>`).join('')}</div></details>`:''}
 ${!journal&&all.discovery_links?.length?`<details><summary>新搜索线索（由维护程序核对）</summary>${all.discovery_links.map(x=>`<p>${E(x.journal)} · ${link(x.url)?`<a href="${E(link(x.url))}" target="_blank" rel="noopener">${E(x.title)}</a>`:E(x.title)}</p>`).join('')}</details>`:''}
 ${status.last_check&&['rejected','error'].includes(status.last_check.status)?`<details><summary>本批次未更新</summary><p>${E(status.last_check.message)}</p></details>`:''}</div>`;
}
export function pendingList(rows=[]){
 if(!rows.length)return '';
 return `<details class="p4-pending"><summary>${rows.length}条论文待确认</summary>${rows.map(row=>{
 const c=row.candidate,url=/^https?:\/\//.test(c.official_url||'')?c.official_url:'';
 const attrs=`data-confirm-batch="${E(row.batch_id)}" data-confirm-candidate="${E(row.candidate_id)}"`;
 return `<article><h3>${E(c.title)}</h3><p>${E((c.authors||[]).map(a=>a.name||a).join('、'))} · ${E(c.journal_name)}</p><p>${E(row.reason)}</p><div class="p3-actions">${url?`<a class="text-btn" href="${E(url)}" target="_blank" rel="noopener">核对原文 ↗</a>`:''}${row.suggestions.map(s=>`<button class="text-btn" ${attrs} data-confirm-action="link" data-confirm-record="${E(s.record_id)}">确认关联：${E(s.title)}</button>`).join('')}${row.can_add?`<button class="btn" ${attrs} data-confirm-action="add">确认是新论文</button>`:''}</div></article>`;
 }).join('')}</details>`;
}
