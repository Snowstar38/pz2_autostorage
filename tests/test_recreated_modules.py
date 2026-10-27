"""Recreated private-loader manager modules must be patched before Init/phase caching."""
from pathlib import Path
from runtime_fixture import runtime

lua = runtime()
main = Path(__file__).resolve().parents[1] / 'src/Autostorage/Main'
lua.globals().core_source = (main / 'breederkeeper.core.lua').read_text()
lua.execute(r'''
local core
module=function() core={}; return core end
assert(load(core_source))('BreederKeeper.Core')
module=nil
local modules={}
require=function(name) return assert(modules[string.lower(name)],name) end
package.loaded={}
core:_InstallRequireHook()
core:AddModulePatch('Environment.Environment',function(m) core:_PatchEnvironment(m) end)
core.UI=R.Core.UI
R:Init(core)
local function freshManager()
 local m={}
 function m:Init(properties,env) self.tWorldAPIs=apis; self.bStartedShutdown=false end
 function m:Advance(dt) return 'native' end
 function m:Shutdown() self.bStartedShutdown=true end
 function m:new() return setmetatable({},{__index=self}) end
 return m
end
local function freshEnvironment(managerModule)
 local e={}
 -- Captured private loader bypasses the hooked global require, as in stock.
 function e:_LoadManagerModule(name) assert(name=='Managers.HeatMapManager'); return managerModule end
 function e:Create()
  local prototype=self:_LoadManagerModule('Managers.HeatMapManager')
  self.manager=prototype:new()
  -- Stock caches the method before/around Init; patch must precede both.
  self.advance=self.manager.Advance
  self.manager:Init({},self)
 end
 return e
end
local hud={Init=function(self,env) self.tWorldAPIs=apis end,OnActivate=function() end}
modules['windows.mainhud']=hud
require('Windows.MainHUD')
local saved
for world=1,3 do
 local mm=freshManager(); local env=freshEnvironment(mm)
 modules['environment.environment']=env
 require('Environment.Environment')
 env:Create()
 assert(R.manager==env.manager and R.managerEnvironment==env,
  'world '..world..': recreated Environment/HeatMap modules must deliver Init before save deserialization')
 assert(R.persistence and R.persistenceStatus.available,'serializer registered before stock world-load callbacks')
 if saved then
  assert(serialization.load(saved,1))
  assert(R.pendingSaved and not R.supported,'passive saved config captured before HUD readiness')
 end
 currentWildArea=world==2
 hud.Init({},env)
 for i=1,100 do env.advance(env.manager,.016) end
 if world==2 then
  assert(not R.supported and R.worldKind=='reserve' and R.mode=='preview')
 else
  assert(R.supported and not R.loading,'cached wrapped Advance completes automatic zoo discovery')
  if world==1 then
   assert(R:Command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true}))
   assert(R:Command({type='enable_transfers'})); env.advance(env.manager,.016)
   saved={}; serialization.save(saved)
  else
   assert(R.rules['habitat:3:Warthog'] and R.mode=='active','same zoo restores config after reserve')
   animals[12].nAgeGroup=2; emit(1,{{nAnimalEntityID=12}}); env.advance(env.manager,.016)
   assert(#transfers==1,'new world cached Advance executes native maturation work')
  end
 end
 local before=R:GetStatus().diagnostics.hooks.counts.managerInit
 core:_ApplyPatches('managers.heatmapmanager',mm)
 core:_ApplyPatches('environment.environment',env)
 assert(R:GetStatus().diagnostics.hooks.counts.managerInit==before,'repeat sweep has no lifecycle side effects')
 local advances=R:GetStatus().diagnostics.hooks.counts.managerAdvance
 mm.Advance(env.manager,.016)
 assert(R:GetStatus().diagnostics.hooks.counts.managerAdvance==advances+1,'same-table sweep must not double-wrap tick')
 env.manager:Shutdown()
 assert(not R.manager)
end
assert(R:GetStatus().diagnostics.hooks.counts.managerInit==3)
assert(R:GetStatus().diagnostics.hooks.counts.managerModule==3)
local extraCount=0
core:AddModulePatch('Managers.HeatMapManager',function(m) extraCount=extraCount+1 end)
local extra=freshManager()
core:_ApplyPatches('managers.heatmapmanager',extra)
core:_ApplyPatches('managers.heatmapmanager',extra)
local another=freshManager()
core:_ApplyPatches('managers.heatmapmanager',another)
assert(extraCount==2,'new patch index runs once for each module identity')
print('Recreated module lifecycle passed: early private-load patch, serializer timing, cached tick, reserve return')
''')
