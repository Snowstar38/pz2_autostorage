import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
let created=0,styleWrites=0,idReads=0;
function element(tag){created++;return {tag,children:[],attributes:{},style:new Proxy({},{set(target,key,value){styleWrites++;target[key]=value;return true;}}),setAttribute(k,v){this.attributes[k]=v;},appendChild(node){if(node.parentNode)node.parentNode.removeChild(node);this.children.push(node);node.parentNode=this;return node;},removeChild(node){this.children.splice(this.children.indexOf(node),1);node.parentNode=null;},get firstChild(){return this.children[0];},blur(){}};}
const body=element('body'),hooks={},timers=[];
const context={document:{body,createElement:element},window:{setInterval(fn){timers.push(fn);},engine:{on(name,fn){hooks[name]=fn;},trigger(){}}}};
vm.runInNewContext(fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/autostorage.js',import.meta.url),'utf8'),context);
const ui=context.window.BreederKeeperUI;
function animal(id,enclosure,kind='habitat'){return {get id(){idReads++;return String(id);},kind,enclosure:String(enclosure),species:'Species',mature:false};}
const enclosures=Array.from({length:100},(_,i)=>({kind:'habitat',id:String(i),species:'Species',rule:{enabled:true},animals:Array.from({length:100},(_,j)=>animal(i*100+j,i))}));
enclosures.push({kind:'exhibit',id:'exhibit',species:'Species',rule:{enabled:true},animals:[animal(1,'exhibit','exhibit')]});
ui.receive({supported:true,sessionId:'performance',sessionEpoch:1,uiSequence:1,enclosures});
let sequence=1;function delta(fields){hooks.BKDelta(JSON.stringify({sessionId:'performance',sessionEpoch:1,uiSequence:++sequence,...fields}));}
function group(id,kind='habitat'){return ui.inspect().enclosures.find(e=>e.id===id&&e.kind===kind);}
created=0;styleWrites=0;idReads=0;
delta({animals:[{id:'1',kind:'habitat',enclosure:'0',species:'Species',mature:true}]});
assert.equal(created,0,'closed animal update creates no DOM');
assert.ok(idReads<=2,'one update reads only indexed animal, not 10,000 unrelated animals');
assert.equal(styleWrites,0,'supported closed update does not rewrite display');
const indexedReads=idReads;
assert.equal(group('0').population,'1 adults / 99 young');
assert.equal(group('exhibit','exhibit').population,'0 adults / 1 young','animal kind is part of identity');
delta({animals:[{id:'1',kind:'habitat',enclosure:'1',species:'Species'}]});
assert.equal(group('0').population,'0 adults / 99 young');assert.equal(group('1').population,'1 adults / 100 young','moving animal preserves cached maturity');
delta({animals:[{id:'1',kind:'habitat',enclosure:'missing',species:'Species'}]});
assert.equal(group('1').population,'0 adults / 100 young','unknown target removes old group membership');
ui.open();created=0;styleWrites=0;
delta({diagnostics:{ticks:200}});
assert.equal(created,0,'diagnostic counters do not redraw an open menu');
assert.equal(styleWrites,0);
const panel=body.children[1],beforeError=panel.children[0];delta({diagnostics:{ticks:201,lastError:'Useful failure'}});
assert.notEqual(panel.children[0],beforeError,'new diagnostic error still redraws');
created=0;styleWrites=0;timers[0]();assert.equal(created,0);assert.equal(styleWrites,0,'idle watchdog is read-only while mounted');
const beforeStale=group('0').population;hooks.BKDelta(JSON.stringify({sessionEpoch:0,uiSequence:999,animals:[{id:'2',kind:'habitat',enclosure:'1',species:'Species',mature:true}]}));assert.equal(group('0').population,beforeStale,'stale deltas cannot mutate index');
// A replacement snapshot rebuilds object references, even in the same session.
ui.receive({supported:true,sessionId:'performance',sessionEpoch:1,uiSequence:++sequence,enclosures:[{kind:'habitat',id:'new',species:'Species',animals:[animal('new-animal','new')]}]});
delta({animals:[{id:'new-animal',kind:'habitat',enclosure:'new',species:'Species',mature:true}]});assert.equal(group('new').population,'1 adults / 0 young');
// A session with only deltas cannot retain old group or animal pointers.
ui.receive({supported:true,sessionId:'next-zoo',sessionEpoch:2,uiSequence:++sequence,enclosures:[]});
hooks.BKDelta(JSON.stringify({sessionId:'next-zoo',sessionEpoch:2,uiSequence:++sequence,animals:[{id:'new-animal',kind:'habitat',enclosure:'new',species:'Species',mature:true}]}));assert.equal(ui.inspect().enclosures.length,0);
console.log(`UI performance: indexed delta ${indexedReads} animal ID reads (10,001 before), diagnostics redraw 0 nodes (119 before), idle watchdog 0 style writes (1 before); moves/removals/snapshots/sessions preserved`);
