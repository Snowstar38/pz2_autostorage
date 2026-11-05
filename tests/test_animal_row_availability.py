"""A new zoo can enumerate habitat entities before UI records become available."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true,malesOnly=true,contraception=true})
command({type='enable_transfers'})
local oldReceiver=receivers[1]
local oldSerializer=serialization.load
local previous=manager
-- Distinct next-zoo population, including a stale ID and a delayed valid UI row.
animals={[201]={sSpecies='Nyala',sName='New zoo',nGender=1,bAlive=true,nAgeGroup=2,enclosure=8}}
local nativeRows=apis.animals.GetUIAnimalListDataForIDs
local reads=0; local readTimes={}
apis.animals.GetUIAnimalListDataForIDs=function(self,ids)
 if ids[1]==201 then reads=reads+1; readTimes[#readTimes+1]=R.clock; if reads<3 then return {} end end
 return nativeRows(self,ids)
end
apis.habitat.GetAnimalsInHabitat=function(self,h) return h==8 and {201,999} or {} end
manager={tWorldAPIs=apis}; environment={}; R:_Reset(manager,environment)
assert(R:_ConfirmCurrentWorld(environment,apis)); finish()
assert(R.phase=='ready' and not R.loading and R.status.error==nil,'missing rows do not poison next-zoo discovery')
assert(#R.catalog==4 and R.catalogById.g201 and not R.catalogById.g12,'delayed row recovered; old zoo cache absent')
assert(reads==3 and readTimes[2]-readTimes[1]>=.25 and readTimes[3]-readTimes[2]>=.25,'delayed record retries bounded over actual time')
assert(#R.status.messages==1 and R.status.messages[1]:find('omitted'),'persistent omissions reported')
assert(R.diagnostics.unavailableAnimalRows==1,'stale enumeration diagnosed and omitted')
assert(next(R.rules)==nil and #transfers==0 and #contraceptions==0,'new zoo never inherits permissions or targets')
oldReceiver({{nAnimalEntityID=201}}); oldSerializer({},1); step()
assert(next(R.rules)==nil and #transfers==0 and #contraceptions==0,'old-world callbacks stay inert')
''')

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
animals[12].nAgeGroup=2
local original=apis.animals.GetUIAnimalListDataForIDs
local reads=0
apis.animals.GetUIAnimalListDataForIDs=function(self,ids)
 if ids[1]==12 then reads=reads+1;return {} end
 return original(self,ids)
end
emit(1,{{nAnimalEntityID=12}}); finish()
assert(reads==3 and #transfers==0 and #R.candidates==0,'permanently missing target is bounded and never acted on')
assert(R.mode=='active' and not R.status.error,'unavailable target cannot pause unrelated groups')
''')
lua = runtime()
lua.execute(r'''
-- Empty partial catalog is safe and ready; an omitted row is never a native target.
apis.animals.GetUIAnimalListDataForIDs=function() return {} end
manager={tWorldAPIs=apis}; environment={}; R:_Reset(manager,environment)
R:_ConfirmCurrentWorld(environment,apis); finish()
assert(R.phase=='ready' and not R.loading and #R.catalog==3,'all habitat rows unavailable still finishes discovery')
assert(not R.native.g11 and not R.native.g12 and not R.native.g81 and #transfers==0 and #contraceptions==0)
assert(R.diagnostics.unavailableAnimalRows==3 and #R.status.messages==1,'all omissions counted and surfaced')
-- Missing records are recoverable, malformed native responses remain hard failures.
apis.animals.GetUIAnimalListDataForIDs=function() return false end
R.discover=true; R:_BeginScan(apis,true)
local ok,err=pcall(function() while R.job do R:_ScanStep(apis) end end)
assert(not ok and tostring(err):find('Animal records unavailable'),'malformed API response fails closed')
''')
print('Zoo row availability passed: delayed/stale records, new population, bounded retries, old callbacks, no unsafe actions')
