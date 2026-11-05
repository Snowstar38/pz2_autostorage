/* Original Autostorage UI. Gameface controls are authored buttons. */
(function () {
'use strict';
var state={mode:'PREVIEW',enclosures:[],status:'Waiting for park data'};
var animalIndex=new Map(),groupIndex=new Map();
var selected='',drafts={},previewPage=0,picker=null,engineReady=false,lastPayload='',stopPending=false,sentCount=0,lastSent='',detailsOpen=false,advancedOpen=false,currentSession=null,listKind='habitat',listPage=0,pageSize=6,lastPublication=0,currentEpoch=-1,rejectedPublications=0,lastIncoming=null;
function el(tag,text,parent){var n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(parent)parent.appendChild(n);return n;}
function key(e){return String(e.kind)+'|'+String(e.id)+'|'+String(e.species);}
function supported(){return state.supported===true&&state.eligible!==false;}
function send(action,e,male,female,enabled){if(!supported())return;if(window.engine&&engineReady){sentCount++;lastSent=action;var wireAction=action;if(action==='set_rule')wireAction=enabled?'set_rule_on':'set_rule_off';if(action==='set_mode')wireAction=enabled?'set_mode_apply':'set_mode_preview';window.engine.trigger('BKCommand',wireAction,String(e&&e.id||''),String(e&&e.species||''),String(male==null?'':male),String(female==null?'':female));render();}else{state.status='Game bridge unavailable';render();}}
// Match the game mouse-button pattern: DIV controls with no native button focus.
function bindButton(b,fn){b.setAttribute('role','button');b.tabIndex=-1;b.onmousedown=function(event){if(event&&event.button===0)event.preventDefault();};b.onclick=function(event){if(b.disabled)return;try{return fn(event);}finally{if(typeof b.blur==='function')b.blur();}};return b;}
function button(text,fn,parent,disabled){var b=bindButton(el('div',text,parent),fn);b.disabled=!!disabled;b.setAttribute('aria-disabled',b.disabled?'true':'false');var skin=el('div',undefined,b);skin.className='Button_bg secondary bk-native-button-bg'+(b.disabled?' disabled':'');skin.setAttribute('aria-hidden','true');b.onmouseenter=function(){skin.className='Button_bg secondary bk-native-button-bg hover'+(b.disabled?' disabled':'');};b.onmouseleave=function(){skin.className='Button_bg secondary bk-native-button-bg'+(b.disabled?' disabled':'');};return b;}
var launch=el('div',undefined,document.body);launch.id='bk-launch';launch.setAttribute('aria-label','Autostorage');launch.setAttribute('aria-describedby','bk-launch-tooltip');
var crateFallback=el('span',undefined,launch);crateFallback.className='bk-crate-fallback';crateFallback.setAttribute('aria-hidden','true');var crateIcon=el('img',undefined,launch);crateIcon.className='bk-launch-icon';crateIcon.setAttribute('alt','');crateIcon.setAttribute('aria-hidden','true');crateIcon.onerror=function(){crateIcon.style.display='none';crateFallback.style.display='flex';};crateIcon.onload=function(){crateIcon.style.display='block';crateFallback.style.display='none';};crateIcon.setAttribute('src','/img/icons/Icon_AnimalMovedNoPenalty.svg');
var launcherTooltip=el('span','Autostorage',launch);launcherTooltip.id='bk-launch-tooltip';launcherTooltip.className='bk-launch-tooltip';launcherTooltip.setAttribute('role','tooltip');launcherTooltip.style.display='none';launch.onmouseenter=function(){if(supported())launcherTooltip.style.display='flex';};launch.onmouseleave=function(){launcherTooltip.style.display='none';};
var panel=el('section',undefined,document.body);panel.id='bk-panel';panel.className='PaperPanelBackground_bg noTopFlap noBottomFlap';panel.style.display='none';
bindButton(launch,function(){if(!supported())return;panel.style.display=panel.style.display==='none'?'flex':'none';if(panel.style.display!=='none'){if(!state.loading&&state.phase!=='loading')send('refresh');else render();}});
function display(node,value){if(node.style.display!==value)node.style.display=value;}
function mount(){if(!supported()){display(launch,'none');display(launcherTooltip,'none');display(panel,'none');return;}display(launch,'flex');if(launch.parentNode!==document.body)document.body.appendChild(launch);if(panel.parentNode!==document.body)document.body.appendChild(panel);}
function animalKey(kind,id){return String(kind)+'\x1f'+String(id);}
function indexGroups(){animalIndex.clear();groupIndex.clear();(state.enclosures||[]).forEach(function(group){groupIndex.set(key(group),group);(group.animals||[]).forEach(function(animal){if(animal.id!=null)animalIndex.set(animalKey(animal.kind||group.kind,animal.id),{group:group,animal:animal});});});}
function nice(text){var id=String(text||'Unknown'),names=window.AutostorageSpeciesNames||{};return Object.prototype.hasOwnProperty.call(names,id)?names[id]:id;}
function label(e){return (e.name||e.id)+' / '+nice(e.species||e.kind);}
function displayMessage(value){return String(value).replace(/\[string ["'][^"']+["']\]:\d+:\s*/g,'').replace(/(?:[A-Za-z]:)?[^\s:]*[\\/][^\r\n:]*\.lua:\d+:\s*/g,'').replace(/^[^\s:]+\.lua:\d+:\s*/,'');}
function capacity(title,c){if(c)el('p',title+': '+String(c.used==null?'?':c.used)+' / '+String(c.total==null?'?':c.total),panel).className='bk-small';}
function normalizedRule(e){return {enabled:stopPending?false:!!(e.rule&&e.rule.enabled),malesOnly:!!(e.rule&&e.rule.malesOnly),contraception:!!(e.rule&&e.rule.contraception)};}
function sameRule(a,b){return !!a.enabled===!!b.enabled&&!!a.malesOnly===!!b.malesOnly&&!!a.contraception===!!b.contraception;}
function ruleFor(enclosure){return drafts[key(enclosure)]||normalizedRule(enclosure);}
function applyRule(enclosure,enabled,option){selected=key(enclosure);var old=ruleFor(enclosure),next={enabled:enabled,malesOnly:!!old.malesOnly,contraception:!!old.contraception,pending:true};if(option)next[option]=!next[option];drafts[selected]=next;send('set_rule',enclosure,next.malesOnly,next.contraception,enabled);}
function ruleCheckbox(title,checked,fn,parent,mixed,small){var control=button('',fn,parent);control.className='bk-check-row';control.setAttribute('role','checkbox');control.setAttribute('aria-label',title);control.setAttribute('aria-checked',mixed?'mixed':(checked?'true':'false'));var box=el('span',undefined,control);box.className='bk-checkbox Tick_content'+(small?' smallTick':'')+(checked?' bk-checked':'');box.setAttribute('aria-hidden','true');el('span',undefined,box).className='Tick_background'+(small?' smallTick':'');el('span',undefined,box).className='Tick_tick'+(small?' smallTick':'')+(checked?' ticked':'');if(mixed){box.className+=' bk-mixed';el('span',undefined,box).className='bk-mixed-mark';}return control;}
function columnHeader(parent,id,label,path,help,count,total,fn){var cell=button('',fn,parent,!total);cell.className='bk-option-heading'+(total&&count===total?' bk-option-all':(count?' bk-option-mixed':''));cell.setAttribute('aria-label','Toggle '+label.toLowerCase()+' for all '+(listKind==='habitat'?'habitats':'exhibits'));cell.setAttribute('aria-pressed',count===0?'false':(count===total?'true':'mixed'));cell.setAttribute('aria-describedby',id);var icon=el('img',undefined,cell);icon.className='bk-column-icon';icon.setAttribute('src',path);icon.setAttribute('alt',label);var tip=el('span',help,cell);tip.id=id;tip.className='bk-column-tooltip';tip.setAttribute('role','tooltip');tip.style.display='none';var enter=cell.onmouseenter,leave=cell.onmouseleave;cell.onmouseenter=function(){enter();tip.style.display='flex';};cell.onmouseleave=function(){leave();tip.style.display='none';};return cell;}
function applyAllOptions(option,enabled){(state.enclosures||[]).forEach(function(e){if(e.kind!==listKind)return;var old=ruleFor(e),next={enabled:!!old.enabled,malesOnly:!!old.malesOnly,contraception:!!old.contraception,pending:true};next[option]=enabled;drafts[key(e)]=next;});send('bulk_'+(listKind==='habitat'?'habitats':'exhibits')+'_'+(option==='malesOnly'?'males':'contraception')+(enabled?'_on':'_off'));}

function population(enclosure){var adults=0,young=0;(enclosure.animals||[]).forEach(function(a){if(a.mature===true)adults++;else if(a.mature===false)young++;});return adults+' adults / '+young+' young';}
function applyAllListed(enabled){(state.enclosures||[]).filter(function(e){return e.kind===listKind;}).forEach(function(e){var old=ruleFor(e);drafts[key(e)]={enabled:enabled,malesOnly:!!old.malesOnly,contraception:!!old.contraception,pending:true};});send('bulk_'+(listKind==='habitat'?'habitats':'exhibits')+(enabled?'_on':'_off'));}
function render(){
 mount();if(!supported())return;var loading=state.loading===true||state.phase==='loading',active=/^(APPLY|ACTIVE)$/i.test(String(state.mode));while(panel.firstChild)panel.removeChild(panel.firstChild);
 var header=el('div',undefined,panel);header.className='bk-header';
 var title=el('div',undefined,header);title.className='bk-heading';el('h2','Autostorage',title);
 button(detailsOpen?'Back':'Details',function(){detailsOpen=!detailsOpen;render();},header,loading).className='bk-header-button';
 button('X',function(){panel.style.display='none';},header).className='bk-close';
 var content=el('div',undefined,panel);content.className='bk-content';
 var summary=el('div',undefined,content);summary.className='bk-row bk-summary';
 el('div',loading?'Loading':(active?'Active':'Paused'),summary).className='bk-mode';
 el('span',state.persistence&&state.persistence.available&&state.persistence.dirty?'Save pending':'',summary).className='bk-status';
 if(loading){el('p','Loading your zoo...',content).className='bk-loading';var waiting=el('div',undefined,content);waiting.className='bk-row';button('Enable',function(){},waiting,true);button('Refresh',function(){},waiting,true);return;}
 var persistence=state.persistence||{};
 var bridge=state.bridge||{},diagnostics=state.diagnostics||{};
 var shownAlerts={};function showAlert(message){var text=displayMessage(typeof message==='string'?message:JSON.stringify(message));if(!Object.prototype.hasOwnProperty.call(shownAlerts,text)){shownAlerts[text]=true;el('p',text,content).className='bk-alert';}}
 [state.error,bridge.error,diagnostics.lastError,persistence.error&&('Rule saving unavailable: '+persistence.error)].filter(Boolean).forEach(showAlert);
 (state.messages||[]).concat(state.pauses||[]).slice(0,1).forEach(showAlert);
 var controls=el('div',undefined,content);controls.className='bk-row bk-transfer-controls';
 var active=/^(APPLY|ACTIVE)$/i.test(String(state.mode));
 button(active?'Pause':'Enable',function(){send('set_mode',null,null,null,!active);},controls,!active&&!(state.enclosures||[]).some(function(e){return ruleFor(e).enabled;})).className='bk-primary';
 button('Refresh',function(){send('refresh');},controls);
 if(detailsOpen){
  el('h3','Autostorage 1.2.1',content);
  el('p',String(state.status||'Ready'),content).className='bk-small';
  el('p','The header checkbox enables or disables the current tab across every page.',content).className='bk-small';
  el('p',persistence.available?'Save the zoo to keep rule changes.':'Rules are session-only in this zoo.',content).className='bk-small';
  if(state.capacity)el('p','Storage '+String(state.capacity.used===undefined?'?':state.capacity.used)+' / '+String(state.capacity.total===undefined?'?':state.capacity.total),content).className='bk-small';
  (state.eventLog||[]).slice(-5).reverse().forEach(function(event){el('p',(event.name||'Animal')+' / '+nice(event.species)+': '+String(event.result||'observed'),content).className='bk-log';});
  return;
 }
 var enclosures=state.enclosures||[];
 var tabs=el('div',undefined,content);tabs.className='bk-row bk-tabs';
 button('Habitats',function(){listKind='habitat';listPage=0;render();},tabs).className=listKind==='habitat'?'bk-tab bk-tab-active':'bk-tab';
 button('Exhibits',function(){listKind='exhibit';listPage=0;render();},tabs).className=listKind==='exhibit'?'bk-tab bk-tab-active':'bk-tab';
 var listed=enclosures.filter(function(e){return e.kind===listKind;}),enabledCount=0,maleCount=0,contraceptionCount=0;listed.forEach(function(e){var rule=ruleFor(e);if(rule.enabled)enabledCount++;if(rule.malesOnly)maleCount++;if(rule.contraception)contraceptionCount++;});
 el('p',listKind==='habitat'?'Habitats: '+enabledCount+' / '+listed.length+' on':'Exhibits: '+enabledCount+' / '+listed.length+' on',content).className='bk-list-summary';
 var listTools=el('div',undefined,content);listTools.className='bk-row bk-list-tools';
 var advanced=button('Advanced',function(){advancedOpen=!advancedOpen;render();},listTools);advanced.setAttribute('aria-pressed',advancedOpen?'true':'false');advanced.setAttribute('aria-expanded',advancedOpen?'true':'false');
 var columns=el('div',undefined,content);columns.className='bk-column-headings';
 var master=ruleCheckbox('Enable all '+(listKind==='habitat'?'habitats':'exhibits'),listed.length>0&&enabledCount===listed.length,function(){applyAllListed(enabledCount!==listed.length);},columns,enabledCount>0&&enabledCount<listed.length);master.className='bk-master-check';master.disabled=!listed.length;master.setAttribute('aria-disabled',master.disabled?'true':'false');master.setAttribute('title','Enable or disable every '+(listKind==='habitat'?'habitat':'exhibit')+' on this tab, across all pages');
 el('span','Enclosure / species',columns).className='bk-column-label';
 if(advancedOpen){columnHeader(columns,'bk-male-tip','Males only','/img/icons/IconMale.svg','Only affect males',maleCount,listed.length,function(){applyAllOptions('malesOnly',maleCount!==listed.length);});columnHeader(columns,'bk-contraception-tip','Contraception instead of storage','/img/icons/Icon_Contracepted.svg','Enable contraception instead of sending to storage',contraceptionCount,listed.length,function(){applyAllOptions('contraception',contraceptionCount!==listed.length);});}
 if(listPage*pageSize>=listed.length)listPage=0;
 var list=el('div',undefined,content);list.className='bk-list';
 listed.slice(listPage*pageSize,listPage*pageSize+pageSize).forEach(function(enclosure){
  var rule=ruleFor(enclosure),group=el('div',undefined,list);group.className='bk-rule-row';var row=button('',function(){applyRule(enclosure,!rule.enabled);},group);row.className='bk-check-row'+(selected===key(enclosure)?' bk-selected':'');row.setAttribute('role','checkbox');row.setAttribute('aria-checked',rule.enabled?'true':'false');row.setAttribute('aria-label',label(enclosure));
  var box=el('span','',row);box.className='bk-checkbox Tick_content'+(rule.enabled?' bk-checked':'');box.setAttribute('aria-hidden','true');var frame=el('span',undefined,box);frame.className='Tick_background';var tick=el('span',undefined,box);tick.className='Tick_tick'+(rule.enabled?' ticked':'');
  var imagePaths=window.AutostorageSpeciesIcons||{};if(Object.prototype.hasOwnProperty.call(imagePaths,enclosure.species)){var portrait=el('img',undefined,row);portrait.className='bk-species-icon';portrait.setAttribute('alt','');portrait.setAttribute('aria-hidden','true');portrait.onerror=function(){this.style.display='none';};portrait.setAttribute('src',imagePaths[enclosure.species]);}
  var info=el('div',undefined,row);info.className='bk-enclosure-info';el('span',enclosure.name||String(enclosure.id),info).className='bk-enclosure-name';el('span',nice(enclosure.species),info).className='bk-enclosure-species';
  if(enclosure.kind==='habitat'){var adults=0,juveniles=0;(enclosure.animals||[]).forEach(function(animal){if(animal.mature===true)adults++;else if(animal.mature===false)juveniles++;});var count=el('div',undefined,row);count.className='bk-pop-count';el('span',adults+' adult'+(adults===1?'':'s'),count);el('span',juveniles+' juvenile'+(juveniles===1?'':'s'),count);}
  el('span',drafts[key(enclosure)]?'...':'',row).className='bk-rule-state';
  if(advancedOpen){var maleCheck=ruleCheckbox('Males only: '+label(enclosure),rule.malesOnly,function(){applyRule(enclosure,ruleFor(enclosure).enabled,'malesOnly');},group,false,true);maleCheck.className='bk-option-check';var contraceptionCheck=ruleCheckbox('Contraception instead of storage: '+label(enclosure),rule.contraception,function(){applyRule(enclosure,ruleFor(enclosure).enabled,'contraception');},group,false,true);contraceptionCheck.className='bk-option-check';}
 });
 if(!listed.length)el('p','No '+(listKind==='habitat'?'habitats':'exhibits')+' loaded. Use Refresh list to discover enclosures.',list).className='bk-empty';
 var pages=el('div',undefined,content);pages.className='bk-row bk-pages';button('Previous',function(){listPage--;render();},pages,listPage===0);el('span','Page '+(listPage+1)+' of '+Math.max(1,Math.ceil(listed.length/pageSize)),pages);button('Next',function(){listPage++;render();},pages,(listPage+1)*pageSize>=listed.length);
 el('p','Habitats: store maturing juveniles. Exhibits: keep the oldest male and female after births.',content).className='bk-small';
 var storage=el('div',undefined,content);storage.className='bk-row bk-storage';var space=state.capacity||state.exhibitCapacity;if(space)el('span','Storage '+space.used+' / '+space.total,storage);
 var proposals=state.preview||state.proposals||[];if(proposals.length)el('span',proposals.length+' pending',storage);
 (state.eventLog||[]).slice(-1).forEach(function(event){el('p','Last: '+(event.name||'Animal #'+event.id)+' / '+String(event.result||'observed'),content).className='bk-log';});
}
function acceptSession(snapshot){if(snapshot.sessionId===undefined)return;var nextSession=String(snapshot.sessionId);if(currentSession===nextSession)return;currentSession=nextSession;launcherTooltip.style.display='none';selected='';drafts={};previewPage=0;picker=null;stopPending=false;detailsOpen=false;advancedOpen=false;listKind='habitat';listPage=0;panel.style.display='none';state={supported:false,mode:'PREVIEW',enclosures:[]};animalIndex.clear();groupIndex.clear();}
function freshPublication(snapshot){lastIncoming={uiSequence:snapshot.uiSequence,sessionEpoch:snapshot.sessionEpoch,phase:snapshot.phase,supported:snapshot.supported};if(typeof snapshot.sessionEpoch==='number'){if(snapshot.sessionEpoch<currentEpoch){rejectedPublications++;return false;}currentEpoch=snapshot.sessionEpoch;}if(typeof snapshot.uiSequence==='number'){if(snapshot.uiSequence<=lastPublication){rejectedPublications++;return false;}lastPublication=snapshot.uiSequence;}return true;}
function acknowledge(source){if(engineReady&&window.engine)window.engine.trigger('BKViewState',String(currentSession||''),supported()?1:0,source+':'+lastPublication);}
function receive(payload){try{var signature=typeof payload==='string'?payload:JSON.stringify(payload);if(signature===lastPayload)return;var snapshot=typeof payload==='string'?JSON.parse(payload):payload;if(!freshPublication(snapshot))return;acceptSession(snapshot);lastPayload=signature;state=snapshot;if(snapshot.bridge&&/^(Command (?:queue rejected|failed:)|Runtime command queue unavailable|Unknown command:)/.test(String(snapshot.bridge.error||''))){drafts={};stopPending=false;}indexGroups();mount();acknowledge('snapshot');var groups=state.enclosures||[];if(stopPending&&!groups.some(function(e){return e.rule&&e.rule.enabled;}))stopPending=false;groups.forEach(function(e){var d=drafts[key(e)];if(d&&d.pending&&sameRule(d,normalizedRule(e)))delete drafts[key(e)];});if(panel.style.display!=='none')render();}catch(error){state.status='Invalid bridge snapshot';if(panel.style.display!=='none')render();}}
function receiveDelta(payload){try{
 var delta=typeof payload==='string'?JSON.parse(payload):payload;
 if(!delta||typeof delta!=='object')return;if(!freshPublication(delta))return;acceptSession(delta);
 var changed=false,redraw=false;
 ['supported','eligible','sessionEpoch','phase','loading','sessionId','worldKind','unsupportedReason','mode','status','proposals','eventLog','diagnostics','persistence','messages','error','capacity','exhibitCapacity'].forEach(function(field){if(delta[field]!==undefined){if(field==='diagnostics'){if((state.diagnostics||{}).lastError!==(delta.diagnostics||{}).lastError)redraw=true;}else if(field!=='status'||detailsOpen){if(JSON.stringify(state[field])!==JSON.stringify(delta[field]))redraw=true;}state[field]=delta[field];changed=true;}});
 (delta.animals||[]).forEach(function(row){
  if(!row.kind||row.id==null)return;
  var identity=animalKey(row.kind,row.id),previous=animalIndex.get(identity),target=groupIndex.get(key({kind:row.kind,id:row.enclosure,species:row.species})),updated=row;
  if(previous){
   updated={};for(var field in previous.animal)updated[field]=previous.animal[field];for(var keyName in row)updated[keyName]=row[keyName];
   var oldAnimals=previous.group.animals||[],position=oldAnimals.indexOf(previous.animal);if(position!==-1)oldAnimals.splice(position,1);
   animalIndex.delete(identity);
  }
  if(target){if(!target.animals)target.animals=[];target.animals.push(updated);animalIndex.set(identity,{group:target,animal:updated});}
  if(!detailsOpen&&((previous&&previous.group.kind===listKind)||(target&&target.kind===listKind)))redraw=true;
  changed=true;
 });
 if(changed){lastPayload='';mount();acknowledge('delta');if(redraw&&panel.style.display!=='none')render();}
}catch(error){state.status='Invalid bridge update';if(panel.style.display!=='none')render();}}
function connect(){if(!window.engine||typeof window.engine.on!=='function')return;engineReady=true;window.engine.on('BKSnapshot',receive);window.engine.on('BKDelta',receiveDelta);window.engine.trigger('BKReady');}
render();connect();window.setInterval(mount,2000);
window.BreederKeeperUI={receive:receive,close:function(){panel.style.display='none';},inspect:function(){return {sessionId:currentSession,sessionEpoch:currentEpoch,sequence:lastPublication,supported:supported(),worldKind:state.worldKind,phase:state.phase,loading:state.loading,panelOpen:panel.style.display!=='none',launcherAttached:launch.parentNode===document.body,enclosures:(state.enclosures||[]).map(function(e){return {id:e.id,kind:e.kind,species:e.species,population:population(e)};})};},open:function(){if(!supported())return;panel.style.display='flex';render();}};
}());























