/* 轻量工作台的纯数据规则与局部绘制，不包含网络或持久化副作用。 */
export function readingSubset(items,{q='',state='all'}={}){
 const needle=q.trim().toLocaleLowerCase();
 return items.filter(({metadata:m,reading:r})=>(state==='all'||r.status===state||r.history_conflict)&&(!needle||[m.title,m.translated_title,(m.authors||[]).map(a=>typeof a==='string'?a:a?.name||'').join(' '),m.doi].join(' ').toLocaleLowerCase().includes(needle)));
}
export function recentPapers(groups,limit=6){
 const unique=new Map();
 for(const group of groups)for(const m of group?.items||[])if(!m.scope_label)unique.set(m.record_id,m);
 const journals=new Set();
 return [...unique.values()].sort((a,b)=>(b.publication_date||'').localeCompare(a.publication_date||'')||a.record_id.localeCompare(b.record_id)).filter(m=>{const key=m.journal||m.record_id;if(journals.has(key))return false;journals.add(key);return true}).slice(0,limit);
}
export function patchPage(main,html){
 const template=document.createElement('template');template.innerHTML=html;
 const next=template.content.querySelector('[data-light-view]'),current=main.querySelector('[data-light-view]');
 if(!next||!current||next.dataset.lightView!==current.dataset.lightView){main.innerHTML=html;return false}
 const target=current.querySelector('[data-light-results]'),source=next.querySelector('[data-light-results]');
 if(!target||!source){main.innerHTML=html;return false}
 target.replaceChildren(...source.childNodes);
 // 保留输入节点与键盘焦点；按新路由同步非活动控件和按钮状态。
 const form=current.querySelector('[data-light-form]'),nextForm=next.querySelector('[data-light-form]');
 if(form&&nextForm){
  for(const control of form.elements){const fresh=nextForm.elements.namedItem(control.name);if(fresh&&control!==document.activeElement){if(control.tagName==='SELECT'&&control.innerHTML!==fresh.innerHTML)control.replaceChildren(...fresh.childNodes);control.value=fresh.value}}
  for(const button of form.querySelectorAll('[data-light-reading-filter]')){const fresh=[...nextForm.querySelectorAll('[data-light-reading-filter]')].find(b=>b.dataset.lightReadingFilter===button.dataset.lightReadingFilter);button.className=fresh.className;button.setAttribute('aria-pressed',fresh.getAttribute('aria-pressed'))}
  form.removeAttribute('aria-busy');
 }
 const notice=current.querySelector('[data-light-notices]'),newNotice=next.querySelector('[data-light-notices]');if(notice&&newNotice)notice.replaceChildren(...newNotice.childNodes);
 return true;
}
