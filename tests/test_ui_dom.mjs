import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/autostorage.js',import.meta.url),'utf8');
function element(tag){return {tag,children:[],style:{},attributes:{},setAttribute(k,v){this.attributes[k]=v;},textContent:'',blur(){if(context.document.activeElement===this)context.document.activeElement=null;},appendChild(n){if(n.parentNode)n.parentNode.removeChild(n);this.children.push(n);n.parentNode=this;return n;},removeChild(n){this.children.splice(this.children.indexOf(n),1);n.parentNode=null;},get firstChild(){return this.children[0];}};}
const body=element('body'),hooks={},calls=[],timers=[];
const context={document:{body,createElement:element},window:{setInterval(fn){timers.push(fn);},engine:{on(n,f){hooks[n]=f;},trigger(...args){calls.push(args);}}}};
vm.runInNewContext(fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/autostorage.species.js',import.meta.url),'utf8'),context);vm.runInNewContext(source,context);
const launch=body.children[0],panel=body.children[1];
assert.equal(launch.style.display,'none');context.window.BreederKeeperUI.open();assert.equal(panel.style.display,'none');
const habitats=Array.from({length:8},(_,i)=>({kind:'habitat',id:String(i+1),name:'Habitat '+(i+1),species:'Species_'+i,animals:[{id:i*10,kind:'habitat',name:'Adult',mature:true},{id:i*10+1,kind:'habitat',name:'Young',mature:false}],rule:{enabled:false}}));
const exhibit={kind:'exhibit',id:'99',name:'Axolotls',species:'Axolotl',animals:[],rule:{enabled:false}};
const fixture={supported:true,eligible:true,sessionId:'zoo-1',mode:'PREVIEW',persistence:{available:true,dirty:false},capacity:{used:160,total:200},exhibitCapacity:{used:4,total:50},enclosures:[...habitats,exhibit]};
const initial=panel.children[0];hooks.BKSnapshot(JSON.stringify(fixture));assert.equal(panel.children[0],initial,'closed snapshots do not redraw');
const beforeOpen=calls.length;launch.onclick();assert.equal(calls.length,beforeOpen+1,'opening queues one refresh');assert.deepEqual(calls[calls.length-1],['BKCommand','refresh','','','','']);
const afterOpen=calls.length;launch.onclick();assert.equal(calls.length,afterOpen,'closing never refreshes');launch.onclick();assert.equal(calls.length,afterOpen+1,'each reopening refreshes once');
const opened=panel.children[0];hooks.BKSnapshot(JSON.stringify(fixture));assert.equal(panel.children[0],opened,'identical snapshot does not redraw');
function all(root=body){const output=[],queue=[root];while(queue.length){const n=queue.shift();output.push(n);queue.push(...n.children);}return output;}
function button(text){const n=all().find(n=>n.attributes.role==='button'&&n.textContent===text);assert.ok(n,'Missing button '+text);return n;}
function checkbox(label){const n=all().find(n=>n.attributes.role==='checkbox'&&n.attributes['aria-label']===label);assert.ok(n,'Missing checkbox '+label);return n;}
function text(value){return all().some(n=>n.textContent===value);}
assert.ok(!all().some(n=>n.textContent==='Save enclosure rule'),'rules apply without Save step');
assert.ok(text('Paused'));assert.equal(all().filter(n=>n.textContent==='Habitats: store maturing juveniles. Exhibits: keep the oldest male and female after births.').length,1);assert.ok(text('1 adult'));assert.ok(text('1 juvenile'));assert.ok(!text('PREVIEW'));assert.ok(!text('Changes apply immediately. Save this zoo to keep them.'));
assert.equal(all().filter(n=>n.attributes.role==='checkbox').length,7,'list is bounded to six readable rows plus master');
for(const control of all().filter(n=>n.attributes.role==='button'||n.attributes.role==='checkbox')){assert.equal(control.tabIndex,-1);assert.equal(control.onkeydown,undefined);let prevented=false;control.onmousedown({button:0,preventDefault(){prevented=true;}});assert.ok(prevented);}
const first=checkbox('Habitat 1 / Species_0');context.document.activeElement=first;first.onclick();assert.equal(context.document.activeElement,null);assert.equal(calls.at(-1)[1],'set_rule_on');assert.equal(calls.at(-1)[2],'1');assert.equal(calls.at(-1)[3],'Species_0');assert.equal(calls.at(-1)[4],'false');assert.equal(calls.at(-1)[5],'false');assert.equal(calls.at(-1).length,6);assert.equal(checkbox('Habitat 1 / Species_0').attributes['aria-checked'],'true');
assert.ok(!calls.some(c=>c[1]==='set_mode_apply'),'checking a rule never activates global transfers');
button('Next').onclick();checkbox('Habitat 7 / Species_6');checkbox('Enable all habitats').onclick();assert.equal(calls.at(-1)[1],'bulk_habitats_on');assert.equal(calls.at(-1)[2],'','bulk scope is entire catalog, not selected enclosure/page');
button('Exhibits').onclick();assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'false','habitat bulk leaves exhibits off');checkbox('Enable all exhibits').onclick();assert.equal(calls.at(-1)[1],'bulk_exhibits_on');assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'true');checkbox('Enable all exhibits').onclick();assert.equal(calls.at(-1)[1],'bulk_exhibits_off');assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'false');assert.ok(!all().some(n=>/Choose (male|female)|breeding pair/.test(n.textContent)));checkbox('Axolotls / Axolotl').onclick();assert.equal(calls.at(-1)[1],'set_rule_on');assert.equal(calls.at(-1)[2],'99');
button('Enable').onclick();assert.equal(calls.at(-1)[1],'set_mode_apply');
const active=JSON.parse(JSON.stringify(fixture));active.mode='ACTIVE';active.enclosures.forEach(e=>e.rule.enabled=true);hooks.BKSnapshot(JSON.stringify(active));button('Pause').onclick();assert.equal(calls.at(-1)[1],'set_mode_preview');assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'true','pausing does not erase rules');
button('Habitats').onclick();checkbox('Enable all habitats').onclick();assert.equal(calls.at(-1)[1],'bulk_habitats_off');button('Exhibits').onclick();assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'true');
const close=button('X');context.document.activeElement=close;close.onclick();assert.equal(context.document.activeElement,null);const beforeDelta=panel.children[0];hooks.BKDelta(JSON.stringify({animals:[{id:1,kind:'habitat',enclosure:'1',species:'Species_0',mature:true}],eventLog:[{id:1,name:'Young',species:'Species_0',result:'requested storage'}],diagnostics:{eventMode:'events',eventsReceived:1,eventsProcessed:1,pendingEvents:0,scansStarted:1},persistence:{available:true,dirty:true}}));assert.equal(panel.children[0],beforeDelta,'closed delta does not redraw');context.window.BreederKeeperUI.open();button('Habitats').onclick();assert.equal(context.window.BreederKeeperUI.inspect().enclosures.find(e=>e.id==='1').population,'2 adults / 0 young');assert.ok(text('Last: Young / requested storage'));assert.ok(text('Save pending'));
button('Details').onclick();assert.ok(text('Autostorage '+fs.readFileSync(new URL('../VERSION.txt',import.meta.url),'utf8').trim()));assert.ok(!text('Events queued 1 / handled 1 / pending 0'));assert.ok(!text('Discovery scans: 1'));button('Back').onclick();
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
assert.ok(!fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/AutostorageHUD.html',import.meta.url),'utf8').includes('AutostorageDiagnostics = true'),'production hides temporary diagnostics');
console.log('UI DOM: immediate checklist, tab-scoped bulk, global mode separation, paging, focus, deltas, persistence, reserve and session reset passed');









const shippingHTML=fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/AutostorageHUD.html',import.meta.url),'utf8');
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

// Launcher discovery keeps activation/rule drafts and does not run in loading worlds.
const refreshCount=()=>calls.filter(c=>c[0]==='BKCommand'&&c[1]==='refresh').length;
const tickDraft=checkbox('Tick off / Meerkat').attributes['aria-checked'];
const modeCommands=calls.filter(c=>c[0]==='BKCommand'&&c[1].startsWith('set_mode')).length;
const rulesBefore=calls.filter(c=>c[0]==='BKCommand'&&c[1].startsWith('set_rule')).length;
const beforeToggle=refreshCount();launch.onclick();assert.equal(refreshCount(),beforeToggle);launch.onclick();assert.equal(refreshCount(),beforeToggle+1);
assert.equal(checkbox('Tick off / Meerkat').attributes['aria-checked'],tickDraft,'opening preserves pending rule draft');
assert.equal(calls.filter(c=>c[0]==='BKCommand'&&c[1].startsWith('set_mode')).length,modeCommands);
assert.equal(calls.filter(c=>c[0]==='BKCommand'&&c[1].startsWith('set_rule')).length,rulesBefore);
context.window.BreederKeeperUI.receive({...fixture,sessionId:'loading-launch',sessionEpoch:70,uiSequence:7000,phase:'loading',loading:true});
const loadingRefreshes=refreshCount();launch.onclick();assert.equal(refreshCount(),loadingRefreshes,'opening while loading uses automatic initial discovery');

// Advanced columns are presentation only; every row has independent options.
context.window.BreederKeeperUI.receive({...fixture,sessionId:'options-zoo',sessionEpoch:80,uiSequence:8000});
context.window.BreederKeeperUI.open();
assert.equal(button('Advanced').attributes['aria-expanded'],'false');
assert.ok(!all().some(n=>String(n.attributes['aria-label']).startsWith('Males only:')));
assert.ok(!text('Options'),'per-row options buttons removed');
const beforeAdvanced=calls.length;button('Advanced').onclick();assert.equal(calls.length,beforeAdvanced,'visibility is local UI state');
assert.equal(button('Advanced').attributes['aria-expanded'],'true');
assert.equal(all().filter(n=>n.className==='bk-rule-row').length,6);
assert.equal(all().filter(n=>n.className==='bk-option-check').length,12,'two independent options per visible row');
const maleLabel='Males only: Habitat 1 / Species_0';
const contraLabel='Contraception instead of storage: Habitat 1 / Species_0';
assert.equal(checkbox(maleLabel).attributes['aria-checked'],'false');
assert.equal(checkbox(contraLabel).attributes['aria-checked'],'false');
const heading=all().find(n=>n.className==='bk-option-heading'&&n.attributes['aria-label']==='Toggle males only for all habitats');
assert.equal(heading.children.find(n=>n.tag==='img').attributes.src,'/img/icons/IconMale.svg');
const maleTip=heading.children.find(n=>n.attributes.role==='tooltip');
assert.equal(maleTip.textContent,'Only affect males');assert.ok(text('Enable contraception instead of sending to storage'));assert.equal(maleTip.style.display,'none');heading.onmouseenter();assert.equal(maleTip.style.display,'flex');heading.onmouseleave();assert.equal(maleTip.style.display,'none');
assert.ok(all().some(n=>n.tag==='img'&&n.attributes.src==='/img/icons/Icon_Contracepted.svg'));
assert.ok(checkbox(maleLabel).children.some(n=>n.className.includes('smallTick')),'inline options use native compact Tick');
checkbox(maleLabel).onclick();
assert.deepEqual(calls.at(-1),['BKCommand','set_rule_off','1','Species_0','true','false']);
checkbox(contraLabel).onclick();
assert.deepEqual(calls.at(-1),['BKCommand','set_rule_off','1','Species_0','true','true']);
checkbox('Habitat 1 / Species_0').onclick();
assert.deepEqual(calls.at(-1),['BKCommand','set_rule_on','1','Species_0','true','true']);
assert.equal(checkbox('Enable all habitats').attributes['aria-checked'],'mixed');
const beforeCollapse=calls.length;button('Advanced').onclick();assert.equal(calls.length,beforeCollapse);
assert.ok(!all().some(n=>n.className==='bk-option-check'),'collapse only hides option columns');
button('Advanced').onclick();assert.equal(checkbox(maleLabel).attributes['aria-checked'],'true');assert.equal(checkbox(contraLabel).attributes['aria-checked'],'true');
const optionsAck=JSON.parse(JSON.stringify(fixture));
Object.assign(optionsAck,{sessionId:'options-zoo',sessionEpoch:80,uiSequence:8001});
optionsAck.enclosures[0].rule={enabled:true,malesOnly:true,contraception:true};
hooks.BKSnapshot(JSON.stringify(optionsAck));
assert.ok(!text('...'),'matching complete rule acknowledges option draft');
checkbox('Enable all habitats').onclick();
assert.equal(calls.at(-1)[1],'bulk_habitats_on','mixed master enables all current-tab pages');
assert.equal(checkbox('Enable all habitats').attributes['aria-checked'],'true');
button('Next').onclick();assert.equal(checkbox('Habitat 8 / Species_7').attributes['aria-checked'],'true','master affects other pages');button('Previous').onclick();
checkbox('Enable all habitats').onclick();assert.equal(calls.at(-1)[1],'bulk_habitats_off');
assert.equal(checkbox('Enable all habitats').attributes['aria-checked'],'false');
assert.equal(checkbox(maleLabel).attributes['aria-checked'],'true','bulk disabling preserves males only');
assert.equal(checkbox(contraLabel).attributes['aria-checked'],'true','bulk disabling preserves contraception');
checkbox(maleLabel).onclick();
assert.deepEqual(calls.at(-1),['BKCommand','set_rule_off','1','Species_0','false','true']);
button('Exhibits').onclick();
assert.equal(checkbox('Enable all exhibits').attributes['aria-checked'],'false','master selection is tab scoped');
assert.equal(checkbox('Males only: Axolotls / Axolotl').attributes['aria-checked'],'false','options belong to one enclosure');
checkbox('Contraception instead of storage: Axolotls / Axolotl').onclick();
assert.deepEqual(calls.at(-1),['BKCommand','set_rule_off','99','Axolotl','false','true']);
context.window.BreederKeeperUI.receive({...fixture,sessionId:'new-advanced-session',sessionEpoch:81,uiSequence:8002});context.window.BreederKeeperUI.open();
assert.equal(button('Advanced').attributes['aria-expanded'],'false','new session starts collapsed');
console.log('Advanced inline native columns, tooltips, mixed master, pagination, option preservation and bridge passed');

const tooltipCSS=fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/autostorage.css',import.meta.url),'utf8');
const opaqueTooltips=tooltipCSS.match(/#bk-launch \.bk-launch-tooltip,#bk-panel \.bk-column-tooltip\{([^}]+)\}/);
assert.ok(opaqueTooltips,'both tooltip types share opaque native styling');
for(const declaration of ['background-color:#f1e3ce','background-image:none','color:#725b4a','opacity:1','filter:none'])assert.ok(opaqueTooltips[1].includes(declaration),declaration);
console.log('Launcher and column tooltips use explicit opaque native colors without opacity/filter tint');

const columnTooltipCSS=tooltipCSS.match(/#bk-panel \.bk-column-tooltip\{([^}]+)\}/)[1];
assert.ok(columnTooltipCSS.includes('width:auto;max-width:15rem;min-width:0'),'column tooltip hugs short text and caps long text');
assert.ok(!columnTooltipCSS.includes(';width:15rem;'),'column tooltip has no fixed width');
const launcherTooltipCSS=tooltipCSS.match(/#bk-launch \.bk-launch-tooltip\{([^}]+)\}/)[1];
assert.ok(launcherTooltipCSS.includes('min-width:0;max-width:15rem'),'launcher tooltip sizes to its content');

// Internal Lua source labels stay diagnostic data and never become product names.
const rawFailure=String.raw`.\BreederKeeper\Runtime.lua:508: Animal record unavailable`;
const errorSnapshot={...fixture,sessionId:'error-labels',sessionEpoch:82,uiSequence:9000,error:rawFailure,diagnostics:{lastError:rawFailure},messages:[rawFailure]};
context.window.BreederKeeperUI.receive(errorSnapshot);context.window.BreederKeeperUI.open();
assert.equal(all().filter(n=>n.className==='bk-alert'&&n.textContent==='Animal record unavailable').length,1,'same failure is shown once with useful description');
assert.ok(!all().some(n=>n.textContent.includes('BreederKeeper')),'internal source names are not shown as product names');
assert.equal(errorSnapshot.error,rawFailure,'raw diagnostic payload remains unchanged');
context.window.BreederKeeperUI.receive({...errorSnapshot,uiSequence:9001,error:'[string "Autostorage.Runtime"]:508: Animal record unavailable',diagnostics:{},messages:[],persistence:{available:false,error:'C:\\mods\\BreederKeeper\\Persistence.lua:99: serializer unavailable'}});
assert.ok(text('Animal record unavailable'));assert.ok(text('Rule saving unavailable: serializer unavailable'));
console.log('Lua error locations are hidden in UI, useful messages retained and duplicate alerts collapsed');

// Clickable native icon headers aggregate options across the current tab/pages.
function optionHeader(label){const control=all().find(n=>n.attributes.role==='button'&&n.attributes['aria-label']===label);assert.ok(control,'Missing header '+label);return control;}
const bulkFixture=JSON.parse(JSON.stringify(fixture));
Object.assign(bulkFixture,{sessionId:'bulk-option-ui',sessionEpoch:83,uiSequence:10000});
bulkFixture.enclosures.forEach((e,i)=>e.rule={enabled:i===0,malesOnly:i===0,contraception:i===1});
context.window.BreederKeeperUI.receive(bulkFixture);context.window.BreederKeeperUI.open();button('Advanced').onclick();
const maleHeaderLabel='Toggle males only for all habitats',contraHeaderLabel='Toggle contraception instead of storage for all habitats';
assert.equal(optionHeader(maleHeaderLabel).attributes['aria-pressed'],'mixed');
assert.ok(optionHeader(maleHeaderLabel).className.includes('bk-option-mixed'));
const beforeMaleBulk=calls.length;optionHeader(maleHeaderLabel).onclick();
assert.equal(calls.length,beforeMaleBulk+1,'one command for the entire bulk operation');
assert.deepEqual(calls.at(-1),['BKCommand','bulk_habitats_males_on','','','','']);
assert.equal(optionHeader(maleHeaderLabel).attributes['aria-pressed'],'true');
assert.ok(optionHeader(maleHeaderLabel).className.includes('bk-option-all'));
assert.equal(checkbox('Habitat 1 / Species_0').attributes['aria-checked'],'true');
assert.equal(checkbox('Habitat 2 / Species_1').attributes['aria-checked'],'false','bulk options do not enable disabled rules');
assert.equal(checkbox('Contraception instead of storage: Habitat 2 / Species_1').attributes['aria-checked'],'true','other option preserved');
button('Next').onclick();assert.equal(checkbox('Males only: Habitat 8 / Species_7').attributes['aria-checked'],'true','option header covers off-page groups');assert.equal(checkbox('Habitat 8 / Species_7').attributes['aria-checked'],'false');
optionHeader(maleHeaderLabel).onclick();assert.deepEqual(calls.at(-1),['BKCommand','bulk_habitats_males_off','','','','']);assert.equal(optionHeader(maleHeaderLabel).attributes['aria-pressed'],'false');
optionHeader(contraHeaderLabel).onclick();assert.deepEqual(calls.at(-1),['BKCommand','bulk_habitats_contraception_on','','','','']);
assert.equal(checkbox('Males only: Habitat 8 / Species_7').attributes['aria-checked'],'false','contraception bulk preserves males-only state');
const bulkAck=JSON.parse(JSON.stringify(bulkFixture));bulkAck.uiSequence=10001;bulkAck.enclosures.filter(e=>e.kind==='habitat').forEach(e=>{e.rule.malesOnly=false;e.rule.contraception=true;});
hooks.BKSnapshot(JSON.stringify(bulkAck));assert.ok(!text('...'),'bulk option drafts acknowledge complete runtime rule state');
button('Exhibits').onclick();const exhibitHeaderLabel='Toggle males only for all exhibits';assert.equal(optionHeader(exhibitHeaderLabel).attributes['aria-pressed'],'false','habitat bulk leaves exhibits unchanged');optionHeader(exhibitHeaderLabel).onclick();assert.deepEqual(calls.at(-1),['BKCommand','bulk_exhibits_males_on','','','','']);assert.equal(checkbox('Axolotls / Axolotl').attributes['aria-checked'],'false');
hooks.BKSnapshot(JSON.stringify({...bulkAck,uiSequence:10002,enclosures:[]}));const emptyHeader=optionHeader(exhibitHeaderLabel),beforeEmpty=calls.length;assert.equal(emptyHeader.attributes['aria-disabled'],'true');emptyHeader.onclick();assert.equal(calls.length,beforeEmpty,'empty-tab option header is disabled');
console.log('Bulk option headers: native mixed/all states, one command, all pages, independent flags, enablement, tab scope and acknowledgement passed');

// Rejected commands restore authoritative state; successful rapid drafts remain optimistic.
const rapidFixture=JSON.parse(JSON.stringify(fixture));Object.assign(rapidFixture,{sessionId:'rapid-rejections',sessionEpoch:84,uiSequence:11000,bridge:{received:0}});
context.window.BreederKeeperUI.receive(rapidFixture);context.window.BreederKeeperUI.open();button('Advanced').onclick();
optionHeader(maleHeaderLabel).onclick();optionHeader(contraHeaderLabel).onclick();
const partialAck=JSON.parse(JSON.stringify(rapidFixture));partialAck.uiSequence=11001;partialAck.bridge={received:1};partialAck.enclosures.filter(e=>e.kind==='habitat').forEach(e=>e.rule.malesOnly=true);
hooks.BKSnapshot(JSON.stringify(partialAck));assert.equal(optionHeader(contraHeaderLabel).attributes['aria-pressed'],'true','earlier accepted snapshot retains newer optimistic option');assert.ok(text('...'));
const rapidAck=JSON.parse(JSON.stringify(partialAck));rapidAck.uiSequence=11002;rapidAck.bridge={received:2};rapidAck.enclosures.filter(e=>e.kind==='habitat').forEach(e=>e.rule.contraception=true);
hooks.BKSnapshot(JSON.stringify(rapidAck));assert.ok(!text('...'),'complete rapid edits acknowledge');
optionHeader(maleHeaderLabel).onclick();assert.equal(optionHeader(maleHeaderLabel).attributes['aria-pressed'],'false');assert.ok(text('...'));
const rejected=JSON.parse(JSON.stringify(rapidAck));rejected.uiSequence=11003;rejected.bridge={received:3,error:'Command queue rejected'};
hooks.BKSnapshot(JSON.stringify(rejected));assert.equal(optionHeader(maleHeaderLabel).attributes['aria-pressed'],'true','rejection restores authoritative rules');assert.ok(!text('...'),'rejection does not leave stuck drafts');assert.ok(text('Command queue rejected'),'failure remains visible');
optionHeader(maleHeaderLabel).onclick();const acceptedAfterFailure=JSON.parse(JSON.stringify(rapidAck));acceptedAfterFailure.uiSequence=11004;acceptedAfterFailure.bridge={received:4};acceptedAfterFailure.enclosures.filter(e=>e.kind==='habitat').forEach(e=>e.rule.malesOnly=false);
hooks.BKSnapshot(JSON.stringify(acceptedAfterFailure));assert.equal(optionHeader(maleHeaderLabel).attributes['aria-pressed'],'false');assert.ok(!text('...'));assert.ok(!text('Command queue rejected'),'next accepted snapshot clears bridge failure');
console.log('Rejected command drafts restore authority, rapid accepted edits persist and later success renders normally');
