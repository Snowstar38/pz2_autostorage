"""Exact live regression: zoo/save/menu/reserve/menu/same zoo with stale destination flag."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
local native,hudNative={},{}
function native.Init(self,p,environment) self.tWorldAPIs=apis; self.bStartedShutdown=false end
function native.Advance(self) end
function native.Shutdown(self) self.bStartedShutdown=true end
function hudNative.Init(self,environment) self.tWorldAPIs=apis end
function hudNative.OnActivate(self) end
R:Init({UI=R.Core.UI,AddModulePatch=function(self,name,fn)
 fn(name=='Managers.HeatMapManager' and native or hudNative)
end})
local function loaded(manager,environment,flag)
 currentWildArea=flag; hudNative.Init({},environment)
 for i=1,100 do native.Advance(manager,.01); if not R.loading then return end end
 error('catalog failed to load')
end
local zoo,envZoo={},{}
native.Init(zoo,nil,envZoo); loaded(zoo,envZoo,false)
R:Command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
R:Command({type='enable_transfers'}); native.Advance(zoo,.016)
local saved={}; serialization.save(saved)
assert(R.rules['habitat:3:Warthog'].enabled)
native.Shutdown(zoo) -- main menu
wildArea=true; currentWildArea=false -- reserve destination; territory not configured during Init
local reserve,envReserve={},{}; native.Init(reserve,nil,envReserve)
assert(not R.supported and R.phase=='loading' and next(receivers)==nil)
serialization.load(saved,1) -- even a payload present here must never apply to a reserve
assert(next(R.rules)==nil and R.pendingSaved)
loaded(reserve,envReserve,true)
assert(not R.supported and R.worldKind=='reserve' and R.mode=='preview' and not R.pendingSaved and not R.persistence)
assert(next(R.rules)==nil and #transfers==0)
native.Shutdown(reserve) -- main menu again
-- Stock load path can retain NextWorldDataManager true from previous reserve.
wildArea=true; currentWildArea=false
local returning,envReturn={},{}; native.Init(returning,nil,envReturn)
assert(not R.supported and R.phase=='loading' and next(receivers)==nil)
assert(serialization.load(saved,1))
assert(R.pendingSaved and next(R.rules)==nil,'normal saved config buffered while world unconfirmed')
loaded(returning,envReturn,false)
assert(wildArea==true and R.supported and R.worldKind=='zoo','current zoo overrides stale reserve destination')
assert(R.rules['habitat:3:Warthog'].enabled and R.mode=='active','saved global enabled config restored only in confirmed zoo')
assert(R.phase=='ready' and #R.catalog==6,'automatic catalog and ready publication require no Refresh')
animals[12].nAgeGroup=2; emit(1,{{nAnimalEntityID=12}}); native.Advance(returning,.016)
assert(#transfers==1 and transfers[1].id==12,'fresh maturation works after exact sequential return')
print('Sequential readiness regression passed: stale reserve metadata, passive config buffer, same zoo restore, automatic ready')
''')
