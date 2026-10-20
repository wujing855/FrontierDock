import test from 'node:test';
import assert from 'node:assert/strict';
import {esc} from '../web/model.js';
import {analyticsPage} from '../web/components/p4-analytics.js';
import {issueDirectory,captureTime} from '../web/components/p4-journals.js';
import {readingSubset,recentPapers} from '../web/components/p4-view.js';
import {sharedDetailAnchorIndex} from '../web/components/journal-card.js';
test('escapes untrusted text',()=>assert.equal(esc('<script>"&'), '&lt;script&gt;&quot;&amp;'));
test('analytics uses configured years, not a developer year',()=>{
 const html=analyticsPage({available_years:['2031','2030'],year:'2031',years:[],fields:[]});
 assert.match(html,/2031 年高频关键词/);assert.doesNotMatch(html,/2026 年高频关键词/);
});
test('unknown issue stays unknown and labels incomplete inventory',()=>{
 const html=issueDirectory('Any journal',[{year:'2031',volume:'unknown',issue:'unknown',count:2}]);
 assert.match(html,/未归期/);assert.match(html,/不代表整期完整/);
});
test('capture timestamp uses configurable timezone',()=>{
 globalThis.FRONTIERDOCK_RUNTIME={timezone:'America/New_York'};
 assert.equal(captureTime('2031-01-02T01:00:00Z'),'2031-01-01');
 assert.equal(captureTime('2031-02-31'),'暂无记录');
});
test('reading filter uses author and state',()=>{
 const rows=[{metadata:{title:'A',authors:['Example']},reading:{status:'completed'}}];
 assert.equal(readingSubset(rows,{q:'example',state:'completed'}).length,1);
 assert.equal(readingSubset(rows,{state:'to_read'}).length,0);
});
test('home shows distinct journals sorted by actual publication date',()=>{
 const items=[{record_id:'a',journal:'j',publication_date:'2031-01-02'},{record_id:'b',journal:'j',publication_date:'2031-01-01'},{record_id:'c',journal:'k'}];
 assert.deepEqual(recentPapers([{items}]).map(x=>x.record_id),['a','c']);
});
test('shared journal details use visible row order',()=>assert.equal(sharedDetailAnchorIndex(['a','b','c'],'c',2),2));
