/* 数学内容只在展示层渲染；原文和笔记锚点保持不变。 */
import katex from '../vendor/katex/katex.js';
import {esc as E} from '../model.js';

const escaped=(s,i)=>{let n=0;while(i>0&&s[--i]==='\\')n++;return n%2===1};
export function tokenizeMath(s){
 const out=[];let start=0,i=0;
 const emit=(end)=>{if(end>start)out.push({kind:'text',raw:s.slice(start,end)})};
 while(i<s.length){
  if(s[i]==='`'&&!escaped(s,i)){
   let n=1;while(s[i+n]==='`')n++;const fence='`'.repeat(n),end=s.indexOf(fence,i+n);
   if(end>=0){emit(i);out.push({kind:'code',raw:s.slice(i,end+n),text:s.slice(i+n,end),block:n>=3});i=end+n;start=i;continue}
  }
  if(s[i]!=='$'||escaped(s,i)){i++;continue}
  const display=s[i+1]==='$',n=display?2:1;let j=i+n,found=-1;
  while(j<s.length){
   if(!display&&s[j]==='\n'&&s[j+1]==='\n')break;
   if(s[j]==='$'&&!escaped(s,j)){
    const run=s[j+1]==='$'?2:1;
    if(n===1||run===n){found=j;break}j+=run;
   }else j++;
  }
  if(found<0||found===i+n){i+=n;continue}
  emit(i);out.push({kind:'math',raw:s.slice(i,found+n),latex:s.slice(i+n,found),display});i=found+n;start=i;
 }
 emit(s.length);return out;
}
function plainMarkdown(text){
 // 先转义；只允许常规链接及本站已受保护的图片，不执行论文中的 HTML。
 return E(text).replace(/(!?)\[([^\]\n]*)\]\(([^\s)]+)\)/g,(all,img,label,url)=>{
  if(img)return /^\/assets\/[a-zA-Z0-9_./-]+$/.test(url)?`<img class="p2-markdown-image" src="${url}" alt="${label}">`:all;
  return /^(https?:\/\/|\/assets\/)/.test(url)?`<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`:all;
 }).replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>');
}
export function renderMath(latex,display=false,raw=(display?'$$':'$')+latex+(display?'$$':'$')){
 try{
  const html=katex.renderToString(latex,{displayMode:display,throwOnError:true,trust:false,strict:'error',maxExpand:1000,maxSize:20,output:'htmlAndMathml'});
  return `<span class="p2-math${display?' is-display':''}" data-latex="${E(latex)}" title="${E(raw)}">${html}</span>`;
 }catch{
  return `<span class="p2-math-fallback" role="note" title="公式渲染失败；保留可复制的 LaTeX 原文"><code>${E(raw)}</code><small>公式待核</small></span>`;
 }
}
export function renderContent(text,{footnotes=[],idPrefix='',isFootnote=false}={}){
 let linked=false;
 return tokenizeMath(text||'').map(t=>{
  if(t.kind==='text'){
   const mark=isFootnote&&!linked?t.raw.match(/^([①-⑳])/):null;
   if(mark&&footnotes.includes(mark[1])){linked=true;return `<sup class="p2-footnote-number" id="${idPrefix}-fn-${mark[1]}" tabindex="-1">${mark[1]}</sup>`+plainMarkdown(t.raw.slice(1))}
   return plainMarkdown(t.raw);
  }
  if(t.kind==='code')return t.block?`<pre><code>${E(t.text)}</code></pre>`:`<code>${E(t.text)}</code>`;
  const number=t.latex.match(/^\^\{(\d+|[①-⑳])\}$/)?.[1];
  if(number&&footnotes.includes(number)){
   const destination=isFootnote&&!linked;linked=true;
   return destination?`<sup class="p2-footnote-number" id="${idPrefix}-fn-${number}" tabindex="-1">${number}</sup>`:`<sup><button class="p2-footnote-link" data-p2="footnote" data-target="${idPrefix}-fn-${number}" aria-label="查看脚注${number}">${number}</button></sup>`;
  }
  return renderMath(t.latex,t.display,t.raw);
 }).join('');
}
