"""Shared-registry HUD joining through native Init -> Load -> ready ordering."""
from pathlib import Path
from lupa.lua53 import LuaRuntime
source=(Path(__file__).resolve().parents[1]/'src/Autostorage/Main/autostorage.ui.lua').read_text()
for order in ('autostorage-first','peer-first'):
 lua=LuaRuntime(unpack_returned_tuples=True);lua.globals().ui_source=source;lua.globals().order=order
 lua.execute(r'''
api={ui2={}};local UI={};module=function() return UI end;assert(load(ui_source))()
local patches={};UI:Init({AddModulePatch=function(_,name,fn) patches[name]=fn end,Runtime={GetStatus=function() return {} end}});UI.bMapped=true
local nativeReady,peerReady,created,unloaded=0,0,0,0
local peerMapped=false;local joined={};local finalAddress
local View={Init=function(hud,settings)
 hud.sViewAddress=settings.sViewAddress;hud.tInitSettings=settings;hud:Load();created=created+1;finalAddress=hud.sViewAddress
 if settings.fnOnReadyCallback then settings.fnOnReadyCallback() end
 return 'native',nil,42
end}
local HUD={Init=function(hud,settings) return View.Init(hud,settings) end,Load=function() end}
local function peer()
 local R=rawget(_G,'PZ2HUDMods')
 if not R then R={nVersion=2,tMods={},tPages={},tWrapped={},tUIs={}};rawset(_G,'PZ2HUDMods',R) end
 R.tMods.Peer={tScripts={HUD={'/js/mods/peer/main.js'}},IsReady=function() return peerMapped end,
 OnReady=function(kind,hud) assert(kind=='HUD' and joined[hud]);peerReady=peerReady+1 end}
 local load=HUD.Load;HUD.Load=function(hud,...)
  local registry=rawget(_G,'PZ2HUDMods')
  if registry.tPages[hud.sViewAddress]=='HUD' and registry.tWrapped[hud] then joined[hud]=true end
  return load(hud,...)
 end
end
if order=='peer-first' then peer() end
patches['UI2.ViewWrapper'](View);patches['UI.Controllers.HUDUI'](HUD)
if order=='autostorage-first' then peer() end
local listeners,events={},{}
local hud=setmetatable({AddEventListener=function(_,name,n,fn,arg) assert(not listeners[name]);listeners[name]={n=n,fn=fn,arg=arg};return name end,
 TriggerEventAtNextAdvance=function(_,name,payload) events[name]=payload end},{__index=HUD})
local settings={sViewAddress='coui://UIGameface/HUD.html',fnOnReadyCallback=function() nativeReady=nativeReady+1 end,fnOnUnloadedCallback=function() unloaded=unloaded+1 end}
local a,b,c=hud:Init(settings)
assert(a=='native' and b==nil and c==42 and created==1 and nativeReady==1)
assert(finalAddress=='coui://UIGameface/AutostorageHUD.html' and joined[hud])
assert(UI.bAttached and peerReady==0,'unmapped peer deferred')
assert(listeners.BKHUDRequest and listeners.BKHUDRequest.n==0,'loader bridge')
local request=listeners.BKHUDRequest
request.fn(request.arg);assert(not events.BKHUDScripts:find('/js/mods/peer/main.js',1,true),'unready script excluded')
peerMapped=true;request.fn(request.arg)
assert(peerReady==1 and events.BKHUDScripts:find('/js/mods/peer/main.js',1,true),'late mapping enables bridge and script')
request.fn(request.arg);assert(peerReady==1,'ready callback once per entry and view')
settings.fnOnUnloadedCallback();assert(unloaded==1 and UI.oUI==nil)
local unknown=setmetatable({AddEventListener=function() return {} end,TriggerEventAtNextAdvance=function() end},{__index=HUD})
unknown:Init({sViewAddress='coui://UIGameface/UnknownModHUD.html'})
assert(finalAddress=='coui://UIGameface/UnknownModHUD.html' and not joined[unknown],'unknown view preserved')
listeners={};hud:Init({sViewAddress='coui://UIGameface/HUD.html'})
assert(peerReady==2,'same wrapper reload reattaches peer lifecycle')
local again=listeners.BKHUDRequest;again.fn(again.arg);assert(peerReady==2,'reloaded wrapper still dispatches once')
''')
# Malformed or older registries are replaced; peer failures remain isolated.
lua=LuaRuntime(unpack_returned_tuples=True);lua.globals().ui_source=source
lua.execute(r'''
api={};PZ2HUDMods={nVersion=1,tMods={old=true}};local UI={};module=function() return UI end;assert(load(ui_source))()
local R=UI:_SharedRegistry();assert(R.nVersion==2 and R.tMods.old==nil)
UI.bMapped=true;local hud={};R.tWrapped[hud]=true;UI.tSharedHUDs={[hud]=true}
local failReady=true;local failAttach=true;local good=0
R.tMods.BadReady={IsReady=function() if failReady then error('not available') end;return true end,tScripts={HUD={'/ready.js'}}}
R.tMods.BadAttach={OnReady=function() if failAttach then error('not attached') end end,tScripts={HUD={'/attach.js'}}}
R.tMods.Good={OnReady=function() good=good+1 end,tScripts={HUD={'/good.js','/good.js','https://outside','//outside',false}}}
local scripts,pending=UI:_SharedScripts(hud);assert(pending and #scripts==1 and scripts[1]=='/good.js' and good==1)
failReady=false;failAttach=false;scripts,pending=UI:_SharedScripts(hud)
assert(not pending and #scripts==3 and good==1,'failed peers retry independently; scripts deduplicated and local only')
local other={};R.tWrapped[other]=true;scripts=UI:_SharedScripts(other);assert(#scripts==0,'other shared host retains its own ready lifecycle')
''')
print('Shared HUD registry: both load orders, native Load joining, delayed mapping, scripts and idempotent ready passed')
