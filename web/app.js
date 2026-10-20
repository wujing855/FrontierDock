import {renderLight} from './components/p4-workspace.js';
import {patchPage} from './components/p4-view.js';
import {icon} from './components/icons.js';
import {prefs,savePrefs} from './store.js';
const labels={workbench:'研究工作台',journals:'期刊浏览',search:'论文检索',reading:'我的阅读',data:'数据与方法'};
document.getElementById('app').innerHTML=`<aside class="sidebar"><a href="#/workbench" class="brand"><span class="brand-mark">${icon('book',28)}</span><div class="brand-copy"><div class="brand-name" style="font-size:19px;letter-spacing:-.5px">FrontierDock</div><div class="brand-sub">前沿工作站</div></div></a><div class="nav-caption">研究空间</div><nav class="nav" aria-label="主要导航">${Object.entries(labels).map(([k,v])=>`<a href="#/${k}">${icon(k==='workbench'?'home':k)}<span class="nav-label">${v}</span></a>`).join('')}</nav><div class="nav-foot"><button class="nav-theme" data-action="nav-theme">${icon('sun')}<span>切换侧栏配色</span></button><div class="environment"><i></i><span>本地工作区</span></div></div></aside><div class="app-area"><header class="topbar"><div class="top-left"><button class="icon-btn" data-action="nav-toggle" aria-label="折叠侧栏">${icon('menu')}</button><span class="top-label">研究工作台</span></div><div class="top-right"><span class="prototype-label"></span><button class="text-btn" data-action="help">${icon('info')} 关于</button></div></header><main id="main" tabindex="-1"></main></div>`;
if(prefs().navLight)document.body.classList.add('nav-light');
if(prefs().navCollapsed)document.body.classList.add('nav-collapsed');
function route(){const text=location.hash.slice(2)||'workbench',[path,query='']=text.split('?');const [page,...rest]=path.split('/');return {page,id:decodeURIComponent(rest.join('/')),query:new URLSearchParams(query)}}
function paint(html){patchPage(document.getElementById('main'),html)}
let previous=location.hash||'#/workbench';
function render(){const hash=location.hash;if(hash!==previous){try{sessionStorage.setItem('frontierdock-p1-v1:scroll:'+previous,String(scrollY))}catch{}previous=hash;scrollTo(0,0)}renderLight(route(),paint)}
window.addEventListener('hashchange',render);
document.addEventListener('click',event=>{
 const action=event.target.closest('[data-action]')?.dataset.action;
 if(action==='nav-toggle'){document.body.classList.toggle('nav-collapsed');savePrefs({navCollapsed:document.body.classList.contains('nav-collapsed')})}
 if(action==='nav-theme'){document.body.classList.toggle('nav-light');savePrefs({navLight:document.body.classList.contains('nav-light')})}
 if(action==='help')document.getElementById('about').showModal();
 if(action==='close-help')document.getElementById('about').close();
 const href=event.target.closest('a')?.getAttribute('href');
 if(href==='#main'){event.preventDefault();document.getElementById('main').focus();return}
 if(href?.startsWith('#/reader/')){try{const id=decodeURIComponent(href.slice(9));sessionStorage.setItem('frontierdock-origin:'+id,JSON.stringify({hash:location.hash||'#/workbench',y:scrollY,expanded:[...document.querySelectorAll('[data-light-preview][open]')].map(x=>x.dataset.lightPreview)}))}catch{}}
});
if(!location.hash)history.replaceState({},'','#/workbench');render();
