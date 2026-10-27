"""Real patched manager and HUD hooks, including overlapping old worlds."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
local native,hudNative={},{}
function native.Init(self,properties,environment) self.tWorldAPIs=apis; self.bStartedShutdown=false end
function native.Advance(self) self.nativeTicks=(self.nativeTicks or 0)+1; return 'native-advance' end
function native.Shutdown(self) self.bStartedShutdown=true end
function hudNative.Init(self,environment) self.tWorldAPIs=apis end
function hudNative.OnActivate(self) return 'native-activate' end
local ui=R.Core.UI
R:Init({UI=ui,AddModulePatch=function(self,name,fn)
 if name=='Managers.HeatMapManager' then fn(native)
 elseif name=='Windows.MainHUD' then fn(hudNative) else error(name) end
end})
local function ready(manager,environment,isWild)
 currentWildArea=isWild; hudNative.Init({},environment)
 for i=1,100 do native.Advance(manager,.01); if not R.loading then return end end
 error('loading did not complete')
end
local zooA,envA={},{}; native.Init(zooA,nil,envA)
assert(not R.supported and next(receivers)==nil,'Init is passive')
ready(zooA,envA,false); assert(R.supported)
local reserveB,envB={},{}; native.Init(reserveB,nil,envB)
ready(reserveB,envB,true); assert(not R.supported and R.worldKind=='reserve')
local zooC,envC={},{}; native.Init(zooC,nil,envC); ready(zooC,envC,false)
local session=R:GetStatus().sessionId
local unregister=counts.unregisterSerializer or 0
native.Advance(zooA,.016); native.Advance(reserveB,.016)
native.Shutdown(zooA); native.Shutdown(reserveB)
assert(R.manager==zooC and R.supported and R:GetStatus().sessionId==session)
assert((counts.unregisterSerializer or 0)==unregister and receivers[1],'old teardown cannot detach new park')
currentWildArea=true; hudNative.Init({},envA)
assert(R.supported,'late old HUD cannot classify new world')
currentWildArea=false
assert(R:Command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true}))
assert(R:Command({type='enable_transfers'})); native.Advance(zooC,.016)
animals[12].nAgeGroup=2; emit(1,{{nAnimalEntityID=12}}); native.Advance(zooC,.016)
assert(#transfers==1,'commands and event transfers work after overlapping transitions')
native.Shutdown(zooC); native.Advance(zooA,.016); native.Advance(zooC,.016)
assert(R.manager==nil and not R.supported)
native.Init(zooC,nil,envC); ready(zooC,envC,false)
assert(R.supported and R:GetStatus().sessionId~=session,'same-instance Init becomes a fresh legitimate session')
local diagnostics=R:GetStatus().diagnostics
assert(diagnostics.hooks.counts.managerInit==4 and diagnostics.hooks.counts.hudReady==5)
assert(diagnostics.hooks.counts.confirmRejected>=1 and diagnostics.hooks.counts.managerShutdown==3)
assert(diagnostics.activeManager==tostring(zooC) and diagnostics.activeEnvironment==tostring(envC))
local status=R.mode; local publishes=fullPublishes; counts={}
for i=1,100 do R:_Observe('testProbe',zooC,envC,'diagnostic only') end
assert(#diagnostics.hooks.history==32 and next(counts)==nil and R.mode==status and fullPublishes==publishes,'bounded read-only observation')
print('Patched manager/HUD lifecycle passed: passive Init, current env proof, late old teardown, same-instance reuse')
''')
