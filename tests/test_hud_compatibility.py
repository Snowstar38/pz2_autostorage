"""HUD document composition preserves another mod's URL detection in both orders.

The synthetic peer models the observed URL/ready contract, without shipping
or executing third-party implementation or assets.
"""
from pathlib import Path
import re
from lupa.lua53 import LuaRuntime

root = Path(__file__).resolve().parents[1]
source = (root / 'src/Autostorage/Main/autostorage.ui.lua').read_text()
for order in ('autostorage-first', 'peer-first'):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ui_source = source
    lua.globals().order = order
    lua.execute(r"""
api={ui2={}}
local UI={}
module=function() return UI end
assert(load(ui_source))()
local patches={}
UI:Init({AddModulePatch=function(_,name,fn) patches[name]=fn end,
 Runtime={GetStatus=function() return {} end}})
UI.bMapped=true
local address,created= nil,0
local View={Init=function(_,settings)
 address=settings.sViewAddress;created=created+1
 if settings.fnOnReadyCallback then settings.fnOnReadyCallback() end
 return 'native',nil,42
end}
patches['UI2.ViewWrapper'](View)
local HUD={Init=function(hud,settings) return View.Init(hud,settings) end}
local detected,peerReady,ready,unloaded=0,0,0,0
local function peer()
 local original=HUD.Init
 HUD.Init=function(hud,settings)
  if settings.sViewAddress=='coui://UIGameface/HUD.html' then
   detected=detected+1
   settings.sViewAddress='coui://UIGameface/PZ2QoLHUD.html'
   local previous=settings.fnOnReadyCallback
   settings.fnOnReadyCallback=function(...)
    peerReady=peerReady+1
    if previous then return previous(...) end
   end
  end
  return original(hud,settings)
 end
end
if order=='autostorage-first' then patches['UI.Controllers.HUDUI'](HUD);peer()
else peer();patches['UI.Controllers.HUDUI'](HUD) end
local hud={AddEventListener=function() return {} end,TriggerEventAtNextAdvance=function() end}
local settings={sViewAddress='coui://UIGameface/HUD.html',
 fnOnReadyCallback=function() ready=ready+1 end,
 fnOnUnloadedCallback=function() unloaded=unloaded+1 end}
local a,b,c=HUD.Init(hud,settings)
assert(a=='native' and b==nil and c==42,'native returns preserved')
assert(address=='coui://UIGameface/AutostoragePZ2QoLHUD.html')
assert(created==1 and detected==1 and peerReady==1 and ready==1)
assert(UI.bAttached and UI.oUI==hud,'Autostorage ready bridge')
settings.fnOnUnloadedCallback()
assert(unloaded==1 and UI.oUI==nil,'both lifecycle callbacks preserved')
View.Init({}, {sViewAddress='coui://UIGameface/OtherMod.html'})
assert(address=='coui://UIGameface/OtherMod.html','unknown mod views preserved')
View.Init({}, {sViewAddress='coui://UIGameface/HUD.html'})
assert(address=='coui://UIGameface/AutostorageHUD.html','standalone HUD')
UI.bMapped=false
View.Init({}, {sViewAddress='coui://UIGameface/PZ2QoLHUD.html'})
assert(address=='coui://UIGameface/PZ2QoLHUD.html','unavailable overlay preserves peer')
""")

ui = root / 'src/Autostorage/UI/UIGameface'
standalone = (ui / 'AutostorageHUD.html').read_text()
combined = (ui / 'AutostoragePZ2QoLHUD.html').read_text()
assert 'js/mods/pz2qol/main.js' not in standalone
composed_address = re.search(r"settings.sViewAddress='(coui://UIGameface/AutostoragePZ2QoLHUD.html)'", source).group(1)
assert re.search('PZ2QoLHUD', composed_address, re.IGNORECASE), 'Toolbox enables its HUD features by pathname'
assert (ui / composed_address.rsplit('/', 1)[1]).is_file()
assert combined.count('js/mods/pz2qol/main.js') == 1
assert combined.count('js/project/apps/HUDApp.js') == 1
for asset in ('autostorage.css', 'autostorage.species.js', 'autostorage.js'):
    assert asset in combined
print('HUD compatibility: both hook orders, native bridge, standalone/fallback and composed assets passed')
