"""Native per-world rule config remap; permissions and requests never survive load."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
local saved={}; serialization.save(saved)
assert(saved.configuration and #saved.configuration.rules==1,'rules saved through registered client')
local config=saved.configuration.rules[1]
assert(config.enclosure==1003 and config.kind=='habitat' and #config.juvenileIds==0,'habitat config has no juvenile-list dependency')
assert(saved.configuration.transfersEnabled==true,'per-zoo global enabled flag saved')
assert(saved.configuration.pending==nil and saved.configuration.mode==nil,'no in-flight request or permission saved')
assert(not R.persistenceStatus.dirty,'native save clears dirty config flag')
local oldLoad=serialization.load
manager={tWorldAPIs=apis}; step()
assert(R.mode=='preview' and next(R.rules)==nil,'separate new world starts with no rules')
oldLoad(saved,1)
assert(next(R.rules)==nil,'detached previous-world callback cannot restore rules into another park')
remap[3]=30
assert(serialization.load(saved,1))
assert(not R.supported and R.pendingSaved,'saved configuration buffered before current-world readiness')
environment={}; R.managerEnvironment=environment
assert(R:_ConfirmCurrentWorld(environment,apis)); finish()
local restored=R.rules['habitat:30:Warthog']
assert(restored and restored.enclosure=='30' and R.mode=='active','native enclosure remap + saved enabled restore after current-world proof')
assert(#R.candidates==0 and #R.hints==0 and next(R.claimed)==nil,'no restored accepted claims or queued events')
animals[12].enclosure=30; animals[12].nAgeGroup=2
emit(1,{{nAnimalEntityID=12}}); step()
assert(#transfers==1 and transfers[1].id==12,'restored habitat config acts on fresh native maturation event')
command({action='set_mode',mode='PREVIEW'})
local paused={}; serialization.save(paused)
assert(paused.configuration.transfersEnabled==false,'explicit paused state saved')
manager={tWorldAPIs=apis}; environment={}; R:_Reset(manager,environment)
serialization.load(paused,1); R:_ConfirmCurrentWorld(environment,apis); finish()
assert(R.mode=='preview','separate paused saved state restores paused')
animals[13]={sSpecies='Warthog',sName='Paused newborn grew',nGender=0,bAlive=true,nAgeGroup=2,enclosure=30}
emit(1,{{nAnimalEntityID=13}}); step()
assert(#transfers==1,'paused saved zoo never inherits another enabled permission')
print('Persistence integration passed: per-zoo enabled state, isolation, remap, readiness gate, fresh events')
''')
