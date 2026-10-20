// 本地规则按用户填写的出刊频率估算月份，不代表已经安排抓取，也不预测Online First论文的上网日。
// 没有可核验的频率时返回未知；不内置任何具体期刊的月份表。
const calendar=date=>Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:globalThis.FRONTIERDOCK_RUNTIME?.timezone||'UTC',year:'numeric',month:'numeric'}).formatToParts(date).filter(p=>['year','month'].includes(p.type)).map(p=>[p.type,Number(p.value)]));
function windowsFor(j,year){
 const frequency=j.publication_frequency||'';
 if(!frequency)return null;
 if(frequency.includes('一月及七月'))return{windows:[[1,1],[7,7]],basis:'按已核验的一月、七月出刊安排'};
 let count=({'月刊':12,'双月刊':6,'季刊':4,'半年刊':2,'年刊':1})[frequency];
 let basis=`按${frequency}常规节奏估算`;
 const annual=[...frequency.matchAll(/(\d{4})年(\d+)期/g)].map(m=>({year:Number(m[1]),count:Number(m[2])})).filter(m=>m.year<=year).sort((a,b)=>b.year-a.year)[0];
 if(annual){count=annual.count;basis=`暂按${annual.year}年${count}期节奏估算，未来可能调整`}
 else if(!count)count=Number(frequency.match(/^每年(\d+)期$/)?.[1]);
 if(!count||12%count!==0)return null;
 const step=12/count;
 return{windows:Array.from({length:count},(_,i)=>[i*step+1,(i+1)*step]),basis};
}
export function publicationForecast(j,now=new Date()){
 if((j.publication_frequency||'').includes('连续'))return{status:'continuous',label:'持续发布新论文',note:'不按固定月份预测单篇上线'};
 const current=calendar(now),latest=j.latest_issue;
 let year=Number(latest?.year),issue=Number(latest?.issue),anchored=Number.isInteger(year)&&year>=1900&&Number.isInteger(issue)&&issue>0;
 if(!anchored)year=current.year;
 let plan=windowsFor(j,year);
 if(!plan)return{status:'unknown',label:'暂难预测',note:'出版周期或月份安排资料不足'};
 let index;
 if(anchored){
  if(issue>plan.windows.length)return{status:'unknown',label:'暂难预测',note:'已收录期号与出版周期不一致，待核验'};
  index=issue; // 第n期之后的第n+1期；不拿论文在线日期代替正式刊期。
  if(index===plan.windows.length){year++;index=0;plan=windowsFor(j,year);if(!plan)return{status:'unknown',label:'暂难预测',note:'下一年度出版节奏尚待核验'}}
 }else{
  index=plan.windows.findIndex(([start])=>start>current.month);
  if(index<0){year++;index=0;plan=windowsFor(j,year)}
 }
 const [start,end]=plan.windows[index];
 const label=`${year}年${start===end?start:start+'–'+end}月左右`;
 const overdue=year<current.year||(year===current.year&&end<current.month);
 return{status:overdue?'overdue':'estimated',label,
  note:overdue?'预测窗口已过，可能已出刊但尚未收录，待核验':plan.basis+(anchored?'':'；当前刊期未核实'),
  year,startMonth:start,endMonth:end,anchored};
}
