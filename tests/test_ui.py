"""Regression checks for UI module isolation and ready-only HUD bindings."""
from pathlib import Path
from lupa.lua53 import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)
source = Path(__file__).resolve().parents[1] / 'src/Autostorage/Main/autostorage.ui.lua'
lua.globals().ui_source = source.read_text(encoding='utf-8')
lua.execute(r'''
local globals = _G
local UI = {}
api = {ui2 = {}}
function module()
 local fn = debug.getinfo(2, 'f').func
 for i = 1, 100 do
  local name = debug.getupvalue(fn, i)
  if not name then break end
  if name == '_ENV' then
   local scope = UI
   local function holder() return scope end
   debug.upvaluejoin(fn, i, holder, 1)
   break
  end
 end
 return UI
end
assert(load(ui_source, 'Autostorage.UI', 't', globals))()
assert(UI.Encode({hello='world'}) == '{"hello":"world"}')
assert(UI.Encode('a\nb') == '"a\\nb"')
local patches, command, listeners = {}, nil, {}
local Core = {
 Runtime = {
  GetStatus = function() return {mode='PREVIEW', enclosures={}} end,
  QueueUICommand = function(_, queued) command=queued end
 },
 AddModulePatch = function(_, name, callback) patches[name]=callback end
}
UI:Init(Core)
assert(Core.UI == UI)
local settings, readyCalled, publications
publications = 0
local View = {Init=function(_, init) settings=init end}
patches['UI2.ViewWrapper'](View)
local HUD = {Init=function(hud, init) return View.Init(hud,init) end}
patches['UI.Controllers.HUDUI'](HUD)
local hud = {
 AddEventListener=function(_, name, count, callback, argument)
  assert(count <= 5, 'native bridge fixture rejects more than five event arguments')
  listeners[name]={count=count, callback=callback, argument=argument}
  return name
 end,
 TriggerEventAtNextAdvance=function(_, event, snapshot)
  assert(event == 'BKSnapshot' and snapshot:find('PREVIEW'))
  publications=publications+1
 end
}
-- Original HUD remains when the overlay failed to map.
HUD.Init(hud, {sViewAddress='original'})
assert(settings.sViewAddress == 'original')
UI.bMapped = true
HUD.Init(hud, {sViewAddress='coui://UIGameface/HUD.html',fnOnReadyCallback=function() readyCalled=true end})
assert(settings.sViewAddress == 'coui://UIGameface/AutostorageHUD.html')
assert(listeners.BKCommand == nil)
settings.fnOnReadyCallback()
assert(readyCalled and publications == 1)
assert(listeners.BKCommand.count == 5)
assert(listeners.BKViewState.count==3)
listeners.BKViewState.callback(listeners.BKViewState.argument,'zoo-session',1,'snapshot:1')
local viewDiagnostics=UI:GetDiagnostics()
assert(viewDiagnostics.clientAcks==1 and viewDiagnostics.clientSupported and viewDiagnostics.clientSession=='zoo-session')
local beforeRefresh=publications;UI:Attach(hud);assert(publications==beforeRefresh+1,'same ready HUD reattachment refreshes state')
hud.view='recreated-view';UI:Attach(hud);assert(UI.boundView=='recreated-view','recreated view on same wrapper rebinds')
local listener = listeners.BKCommand
local beforeCommands=publications
listener.callback(listener.argument, 'set_rule_on', '12', 'Buffalo', '34', '56')
assert(command.enclosureId == '12' and command.species == 'Buffalo')
assert(command.rule.maleId == '34' and command.rule.femaleId == '56')
assert(command.rule.enabled and command.mode == 'APPLY')
listener.callback(listener.argument,'set_rule_on','12','Buffalo','true','false')
assert(command.rule.malesOnly and command.rule.contraception==false)
assert(command.rule.maleId==nil and command.rule.femaleId==nil)
listener.callback(listener.argument,'set_rule_off','12','Buffalo','false','true')
assert(command.rule.enabled==false and command.rule.malesOnly==false and command.rule.contraception)
command=nil;listener.callback(listener.argument,'bulk_habitats_on','','','','')
assert(command.action=='bulk_habitats_on','bulk habitat action reaches runtime through five-arg bridge')
command=nil;listener.callback(listener.argument,'bulk_exhibits_on','','','','')
assert(command.action=='bulk_exhibits_on','bulk exhibit action reaches runtime through five-arg bridge')
for _,kind in ipairs({'habitats','exhibits'}) do
 for _,option in ipairs({'males','contraception'}) do
  for _,value in ipairs({'on','off'}) do
   local action='bulk_'..kind..'_'..option..'_'..value
   command=nil; listener.callback(listener.argument,action,'','','','')
   assert(command and command.action==action,'bulk advanced option reaches runtime as one native command')
  end
 end
end
assert(publications==beforeCommands,'accepted queued commands do not serialize stale full snapshots')
local originalQueue=Core.Runtime.QueueUICommand
Core.Runtime.QueueUICommand=function() return false end
listener.callback(listener.argument,'refresh','','','','')
assert(publications==beforeCommands+1 and UI.sBridgeError=='Command queue rejected','rejection publishes immediate feedback')
Core.Runtime.QueueUICommand=function() error('fixture failure') end
listener.callback(listener.argument,'refresh','','','','')
assert(publications==beforeCommands+2 and UI.sBridgeError:find('fixture failure'),'queue exceptions publish immediate feedback')
Core.Runtime.QueueUICommand=originalQueue
command=nil
listener.callback(listener.argument, 'unknown_action', '', '', '', '')
assert(command == nil, 'unknown actions must not reach runtime')
settings.fnOnUnloadedCallback()
assert(UI.oUI == nil and UI.bAttached==false, 'unload discards stale view and attachment state')
assert(UI:Publish(nil,{mode='PREVIEW'})==false)
assert(UI:GetDiagnostics().lastPublishError=='No ready HUD view')
local reject,removed=true,0
local retryView={
 AddEventListener=function(_,name,count)
  assert(count<=5,'six-argument event rejected')
  if name=='BKCommand' and reject then error('binding temporarily rejected') end
  return name
 end,
 RemoveEventListener=function() removed=removed+1 end,
 TriggerEventAtNextAdvance=function() end
}
local oldRegistrationWorks=pcall(retryView.AddEventListener,retryView,'BKCommand',6)
assert(not oldRegistrationWorks,'fixture reproduces old six-argument registration failure')
UI:Attach(retryView)
assert(not UI.bAttached and UI.sBridgeError:find('binding temporarily rejected'),'failed binding remains visible')
assert(removed==1,'failed partial binding must roll back ready listener')
reject=false;UI:Attach(retryView)
assert(UI.bAttached and UI.sBridgeError==nil,'Attach retries same view after failure')
''')
print('UI isolation, JSON, HUD redirect, ready binding, command queue and unload passed')





ui_source = source.read_text(encoding='utf-8')
assert "LoadOverlay('Autostorage','Autostorage/UI/AutostorageUI')" in ui_source
assert "UnmapResources('Autostorage')" in ui_source
assert "UnloadOverlay('Autostorage')" in ui_source

