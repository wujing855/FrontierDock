import {esc as E} from '../model.js';

// 取完整首句作速览；完整简介保留在详情中，不对题名或简介作视觉裁切。
export function journalSummary(description='') {
  const text=description.trim();
  const stop=text.indexOf('。');
  return stop<0?text:text.slice(0,stop+1);
}

export function journalCard(j,latest,href,expanded=false) {
  const issue=latest?`${latest.year}年 · 第${latest.volume}卷第${latest.issue}期`:'暂无演示记录';
  return `<article class="journal-card ${expanded?'is-expanded':''}" data-journal="${E(j.id)}">
    <div class="journal-card-summary">
    <div class="card-top"><span class="pill">${E(j.field)}</span><span class="journal-region">${j.region==='CN'?'国内期刊':'国外期刊'}</span></div>
    <h2>${E(j.name)}</h2>
    <p class="english-name" lang="en">${E(j.en)}</p>
    <p class="description">${E(journalSummary(j.description))}</p>
    <div class="card-bottom">
      <div class="card-latest"><span>最新示例收录</span><strong>${E(issue)}</strong></div>
      <div class="card-actions">
        <button class="card-details-toggle" id="journal-toggle-${E(j.id)}" data-action="journal-details" data-id="${E(j.id)}" aria-expanded="${expanded}" aria-controls="journal-shared-details" aria-label="${expanded?'收起':'展开'}详情：${E(j.name)}"><span>${expanded?'收起':'展开'}详情</span><svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></button>
        <a class="card-entry" href="${E(href)}">进入期刊</a>
      </div>
    </div>
    </div>
  </article>`;
}

// 用可见 ID 顺序计算行尾，避免筛选后沿用旧索引或误关联另一张卡片。
export function sharedDetailAnchorIndex(ids,selectedId,columns=2) {
  const index=ids.indexOf(selectedId);
  if(index<0)return -1;
  const count=Math.max(1,Math.trunc(Number(columns))||1);
  return Math.min(ids.length-1,Math.floor(index/count)*count+count-1);
}

export function journalDetails(j) {
  return `<div class="shared-detail-header">
      <div><span class="badge-demo">期刊资料 · 演示</span><h3 id="journal-shared-title">${E(j.name)}</h3><p lang="en">${E(j.en)}</p></div>
      <button class="btn quiet" data-action="close-journal-details">关闭详情 <span aria-hidden="true">×</span></button>
    </div>
    <div class="shared-detail-body">
      <p class="detail-description">${E(j.description)}</p>
      <dl class="journal-facts">
        <div><dt>出版周期</dt><dd>${E(j.frequency||'待核')}</dd></div>
        <div><dt>ISSN</dt><dd>${E(j.issn||'待核')}</dd></div>
        <div><dt>资料核验</dt><dd>${E(j.verifiedAt||'待核，核验资料未接入')}</dd></div>
        <div><dt>来源信息</dt><dd>${E(j.official||'待核，原型未接入来源')}</dd></div>
      </dl>
    </div>
    <p class="card-evidence-note">简介与刊期为独立演示，不代表实际出版更新或全刊覆盖。</p>`;
}
