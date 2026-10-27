import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/breederkeeper.js',import.meta.url),'utf8');
function element(tag){return {tag,children:[],style:{},attributes:{},setAttribute(k,v){this.attributes[k]=v;},textContent:'',blur(){if(context.document.activeElement===this)context.document.activeElement=null;},appendChild(n){if(n.parentNode)n.parentNode.removeChild(n);this.children.push(n);n.parentNode=this;return n;},removeChild(n){this.children.splice(this.children.indexOf(n),1);n.parentNode=null;},get firstChild(){return this.children[0];}};}
const body=element('body'),hooks={},calls=[],timers=[];
const context={document:{body,createElement:element},window:{setInterval(fn){timers.push(fn);},engine:{on(n,f){hooks[n]=f;},trigger(...args){calls.push(args);}}}};
vm.runInNewContext(fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/breederkeeper.species.js',import.meta.url),'utf8'),context);vm.runInNewContext(source,context);
const launch=body.children[0],panel=body.children[1];
assert.equal(launch.style.display,'none');context.window.BreederKeeperUI.open();assert.equal(panel.style.display,'none');
const habitats=Array.from({length:8},(_,i)=>({kind:'habitat',id:String(i+1),name:'Habitat '+(i+1),species:'Species_'+i,animals:[{id:i*10,kind:'habitat',name:'Adult',mature:true},{id:i*10+1,kind:'habitat',name:'Young',mature:false}],rule:{enabled:false}}));
const exhibit={kind:'exhibit',id:'99',name:'Axolotls',species:'Axolotl',animals:[],rule:{enabled:false}};
const fixture={supported:true,eligible:true,sessionId:'zoo-1',mode:'PREVIEW',persistence:{available:true,dirty:false},capacity:{used:160,total:200},exhibitCapacity:{used:4,total:50},enclosures:[...habitats,exhibit]};
const initial=panel.children[0];hooks.BKSnapshot(JSON.stringify(fixture));assert.equal(panel.children[0],initial,'closed snapshots do not redraw');
const beforeOpen=calls.length;launch.onclick();assert.equal(calls.length,beforeOpen,'opening never scans');
const opened=panel.children[0];hooks.BKSnapshot(JSON.stringify(fixture));assert.equal(panel.children[0],opened,'identical snapshot does not redraw');
function all(root=body){const output=[],queue=[root];while(queue.length){const n=queue.shift();output.push(n);queue.push(...n.children);}return output;}
function button(text){const n=all().find(n=>n.attributes.role==='button'&&n.textContent===text);assert.ok(n,'Missing button '+text);return n;}
function checkbox(label){const n=all().find(n=>n.attributes.role==='checkbox'&&n.attributes['aria-label']===label);assert.ok(n,'Missing checkbox '+label);return n;}
function text(value){return all().some(n=>n.textContent===value);}
assert.ok(!all().some(n=>n.textContent==='Save enclosure rule'),'rules apply without Save step');
assert.ok(text('Paused'));assert.equal(all().filter(n=>n.textContent==='Store juveniles when they mature.').length,1);assert.ok(text('1 adult'));assert.ok(text('1 juvenile'));assert.ok(!text('PREVIEW'));assert.ok(!text('Changes apply immediately. Save this zoo to keep them.'));
assert.equal(all().filter(n=>n.attributes.role==='checkbox').length,6,'list is bounded to six readable rows');
for(const control of all().filter(n=>n.attributes.role==='button'||n.attributes.role==='checkbox')){assert.equal(control.tabIndex,-1);assert.equal(control.onkeydown,undefined);let prevented=false;control.onmousedown({button:0,preventDefault(){prevented=true;}});assert.ok(prevented);}
const first=checkbox('Habitat 1 / Species_0');context.document.activeElement=first;first.onclick();assert.equal(context.document.activeElement,null);assert.equal(calls.at(-1)[1],'set_rule_on');assert.equal(calls.at(-1)[2],'1');assert.equal(calls.at(-1)[3],'Species_0');assert.equal(calls.at(-1)[4],'');assert.equal(calls.at(-1)[5],'');assert.equal(calls.at(-1).length,6);assert.equal(checkbox('Habitat 1 / Species_0').attributes['aria-checked'],'true');
assert.ok(!calls.some(c=>c[1]==='set_mode_apply'),'checking a rule never activates global transfers');
button('Next').onclick();checkbox('Habitat 7 / Species_6');button('All').onclick();assert.equal(calls.at(-1)[1],'bulk_habitats_on');assert.equal(calls.at(-1)[2],'','bulk scope is entire catalog, not selected enclosure/page');
button('Exhibits').onclick();assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'false','habitat bulk leaves exhibits off');button('All').onclick();assert.equal(calls.at(-1)[1],'bulk_exhibits_on');assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'true');button('None').onclick();assert.equal(calls.at(-1)[1],'bulk_exhibits_off');assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'false');assert.ok(!all().some(n=>/Choose (male|female)|breeding pair/.test(n.textContent)));checkbox('Axolotls / Axolotl').onclick();assert.equal(calls.at(-1)[1],'set_rule_on');assert.equal(calls.at(-1)[2],'99');
button('Enable').onclick();assert.equal(calls.at(-1)[1],'set_mode_apply');
const active=JSON.parse(JSON.stringify(fixture));active.mode='ACTIVE';active.enclosures.forEach(e=>e.rule.enabled=true);hooks.BKSnapshot(JSON.stringify(active));button('Pause').onclick();assert.equal(calls.at(-1)[1],'set_mode_preview');assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'true','pausing does not erase rules');
button('Habitats').onclick();button('None').onclick();assert.equal(calls.at(-1)[1],'bulk_habitats_off');button('Exhibits').onclick();assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'true');
const close=button('X');context.document.activeElement=close;close.onclick();assert.equal(context.document.activeElement,null);const beforeDelta=panel.children[0];hooks.BKDelta(JSON.stringify({animals:[{id:1,kind:'habitat',enclosure:'1',species:'Species_0',mature:true}],eventLog:[{id:1,name:'Young',species:'Species_0',result:'requested storage'}],diagnostics:{eventMode:'events',eventsReceived:1,eventsProcessed:1,pendingEvents:0,scansStarted:1},persistence:{available:true,dirty:true}}));assert.equal(panel.children[0],beforeDelta,'closed delta does not redraw');context.window.BreederKeeperUI.open();button('Habitats').onclick();assert.equal(context.window.BreederKeeperUI.inspect().enclosures.find(e=>e.id==='1').population,'2 adults / 0 young');assert.ok(text('Last: Young / requested storage'));assert.ok(text('Save pending'));
button('Details').onclick();assert.ok(text('Autostorage 1.0'));assert.ok(!text('Events queued 1 / handled 1 / pending 0'));assert.ok(!text('Discovery scans: 1'));button('Back').onclick();
while(body.firstChild)body.removeChild(body.firstChild);timers[0]();assert.equal(body.children.length,2,'watchdog recovers after game HUD render');
const stale=checkbox('Habitat 1 / Species_0');context.window.BreederKeeperUI.receive({supported:false,eligible:false,sessionId:'reserve',worldKind:'reserve',mode:'PREVIEW',enclosures:[]});assert.equal(launch.style.display,'none');assert.equal(panel.style.display,'none');const beforeBlocked=calls.length;stale.onclick();context.window.BreederKeeperUI.open();assert.equal(calls.length,beforeBlocked);while(body.firstChild)body.removeChild(body.firstChild);timers[0]();assert.equal(body.children.length,0);
context.window.BreederKeeperUI.receive({...fixture,sessionId:'zoo-2'});assert.equal(launch.style.display,'flex');assert.equal(panel.style.display,'none');context.window.BreederKeeperUI.open();assert.equal(checkbox('Habitat 1 / Species_0').attributes['aria-checked'],'false','new zoo clears optimistic changes');
context.window.BreederKeeperUI.receive({supported:true,sessionId:'zoo-2',mode:'PREVIEW',status:'Paused',error:'unknown age',persistence:{available:false,error:'serializer unavailable'},messages:['scan halted'],enclosures:[]});assert.ok(text('unknown age'));assert.ok(text('Rule saving unavailable: serializer unavailable'));button('Details').onclick();assert.ok(text('Rules are session-only in this zoo.'));button('Back').onclick();
assert.ok(!all().some(n=>n.tag==='button'||n.tag==='input'||n.tag==='select'));
const loading={...fixture,sessionId:'zoo-loading',sessionEpoch:10,uiSequence:100,phase:'loading',loading:true,enclosures:[]};context.window.BreederKeeperUI.receive(loading);context.window.BreederKeeperUI.open();assert.ok(text('Loading your zoo...'));assert.equal(all().filter(n=>n.attributes.role==='checkbox').length,0);const beforeLoadingClick=calls.length;button('Enable').onclick();button('Refresh').onclick();assert.equal(calls.length,beforeLoadingClick,'loading controls are disabled');
const refreshBeforeReady=calls.filter(c=>c[0]==='BKCommand'&&c[1]==='refresh').length;context.window.BreederKeeperUI.receive({...fixture,sessionId:'zoo-loading',sessionEpoch:10,uiSequence:101,phase:'ready',loading:false});checkbox('Habitat 1 / Species_0');assert.equal(calls.filter(c=>c[0]==='BKCommand'&&c[1]==='refresh').length,refreshBeforeReady,'ready snapshot automatically populates without Refresh');assert.ok(text('Autostorage'));
context.window.BreederKeeperUI.receive({supported:false,eligible:false,sessionId:'old-reserve',sessionEpoch:9,uiSequence:102,phase:'unsupported'});assert.equal(launch.style.display,'flex','old session cannot hide current zoo even if delivered late');context.window.BreederKeeperUI.receive({supported:false,sessionId:'zoo-loading',sessionEpoch:10,uiSequence:100});assert.equal(launch.style.display,'flex','older publication cannot regress state');
context.window.BreederKeeperUI.receive({supported:false,sessionId:'reserve-current',sessionEpoch:11,uiSequence:103,phase:'unsupported'});assert.equal(launch.style.display,'none');context.window.BreederKeeperUI.receive({...fixture,sessionId:'same-zoo-return',sessionEpoch:12,uiSequence:104,phase:'ready',loading:false});assert.equal(launch.style.display,'flex','same zoo returns after reserve');assert.equal(panel.style.display,'none');context.window.BreederKeeperUI.receive({supported:false,sessionId:'reserve-current',sessionEpoch:11,uiSequence:105});assert.equal(launch.style.display,'flex');assert.equal(context.window.BreederKeeperUI.inspect().sessionEpoch,12);assert.ok(calls.some(c=>c[0]==='BKViewState'&&c[1]==='same-zoo-return'&&c[2]===1),'client acknowledges rendered eligibility for diagnostics');
context.window.BreederKeeperUI.receive({...fixture,sessionId:'names-proof',sessionEpoch:50,uiSequence:5000,enclosures:[{...habitats[0],name:'Warthogs',species:'Warthog_Common'},{...habitats[1],name:'Elephants',species:'Elephant_Indian'},{...habitats[2],name:'Unknown species',species:'Unknown_Future_Species'}]});context.window.BreederKeeperUI.open();checkbox('Warthogs / Common Warthog');checkbox('Elephants / Asian Elephant');const unknownRow=checkbox('Unknown species / Unknown_Future_Species');assert.ok(!unknownRow.children.some(n=>n.tag==='img'),'unknown species never guesses an image URI');const rowPortrait=checkbox('Warthogs / Common Warthog').children.find(n=>n.tag==='img');assert.equal(rowPortrait.attributes.src,'/img/AnimalThumbnails/Textures/thumbnail_Warthog_Common_m_normal.png');rowPortrait.onerror();assert.equal(rowPortrait.style.display,'none','failed native image leaves readable row');assert.equal(Object.keys(context.window.AutostorageSpeciesIcons).length,134);assert.equal(Object.keys(context.window.AutostorageSpeciesNames).length,135);const icon=launch.children.find(n=>n.tag==='img'),fallback=launch.children.find(n=>n.className==='bk-crate-fallback');assert.equal(icon.attributes.src,'/img/icons/Icon_AnimalMovedNoPenalty.svg');icon.onerror();assert.equal(fallback.style.display,'flex');assert.equal(icon.style.display,'none');icon.onload();assert.equal(fallback.style.display,'none');assert.equal(launch.attributes['aria-label'],'Autostorage');const tooltip=launch.children.find(n=>n.id==='bk-launch-tooltip');assert.equal(tooltip.textContent,'Autostorage');launch.onmouseenter();assert.equal(tooltip.style.display,'flex');launch.onmouseleave();assert.equal(tooltip.style.display,'none');assert.equal(tooltip.onkeydown,undefined);assert.equal(tooltip.onmousedown,undefined,'tooltip cannot steal keyboard or mouse focus');
assert.ok(!source.includes('AutostorageDiagnostics'),'shipping UI has no temporary diagnostic toggle');
assert.ok(!fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/BreederKeeperHUD.html',import.meta.url),'utf8').includes('AutostorageDiagnostics = true'),'production hides temporary diagnostics');
console.log('UI DOM: immediate checklist, tab-scoped bulk, global mode separation, paging, focus, deltas, persistence, reserve and session reset passed');









const shippingHTML=fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/BreederKeeperHUD.html',import.meta.url),'utf8');
assert.ok(shippingHTML.includes('css/project/components/Button.css'));
assert.ok(shippingHTML.includes('css/project/components/PaperPanelBackground.css'));
assert.ok(panel.className.includes('PaperPanelBackground_bg'));
assert.ok(source.includes('Button_bg secondary bk-native-button-bg'));
assert.ok(!source.includes('Focusable')&&!source.includes('createGameOwnerControlContext'),'native visual skins do not claim keyboard input');

assert.ok(shippingHTML.includes('css/project/components/Tick.css'));
assert.ok(source.includes("tick.className='Tick_tick'+(rule.enabled?' ticked':'')"));
assert.ok(source.includes("frame.className='Tick_background'"));
assert.ok(!source.includes('\\u2713'),'checkbox uses installed native SVG shapes, not a font glyph');

context.window.BreederKeeperUI.receive({...fixture,sessionId:'tick-proof',sessionEpoch:60,uiSequence:6000,enclosures:[{...habitats[0],name:'Tick on',species:'Warthog_Common',rule:{enabled:true}},{...habitats[1],name:'Tick off',species:'Meerkat',rule:{enabled:false}}]});
context.window.BreederKeeperUI.open();
function nativeTick(row){return row.children.find(n=>n.className.includes('bk-checkbox')).children.find(n=>n.className.includes('Tick_tick'));}
assert.equal(nativeTick(checkbox('Tick on / Common Warthog')).className,'Tick_tick ticked');
assert.equal(nativeTick(checkbox('Tick off / Meerkat')).className,'Tick_tick');
checkbox('Tick off / Meerkat').onclick();
assert.equal(nativeTick(checkbox('Tick off / Meerkat')).className,'Tick_tick ticked','pending enabled draft displays same native mark');
assert.ok(text('...'),'pending rule still indicated separately');
