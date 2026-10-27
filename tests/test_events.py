"""Message dispatch, permissions, coalescing, bounded work and global rate cap."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
assert(R.persistenceStatus.available and receivers[1] and receivers[2] and receivers[3])
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
assert(not counts.habitatList,'habitat rule needs no baseline animal scan')
command({type='enable_transfers'})
local before=counts.habitatRow or 0
animals[12].nAgeGroup=2
emit(1,{{nAnimalEntityID=12}})
assert((counts.habitatRow or 0)==before and #transfers==0,'callback does no native reads or mutation')
step()
assert(#transfers==1 and transfers[1].id==12,'authoritative native maturity event moves matching animal')
assert(R.eventLog[#R.eventLog].name=='Baby' and R.eventLog[#R.eventLog].result=='storage request accepted')
assert(not counts.habitatList and not counts.allExhibits,'no whole-enclosure polling')
-- A newborn need not appear in a saved juvenile cohort: native maturity proves transition.
animals[13]={sSpecies='Warthog',sName='Newborn grew',nGender=1,bAlive=true,nAgeGroup=2,enclosure=3}
for i=1,100 do emit(1,{{nAnimalEntityID=13}}) end
assert(#R.hints==1,'burst deduplicated')
step()
assert(#transfers==1 and #R.candidates==1,'global cooldown covers separate native events')
for i=1,6 do step(1) end
assert(#transfers==2 and transfers[2].time-transfers[1].time>=5,'global five-second request cap')
local total=#transfers
emit(1,{{nAnimalEntityID=13},{nAnimalEntityID=81},{nAnimalEntityID=9999}})
for i=1,10 do step(1) end
assert(#transfers==total,'accepted duplicates, unrelated rules and destroyed entities ignored')
-- Preview and mode changes cannot sweep queued adults on later activation.
command({action='set_mode',mode='PREVIEW'})
animals[14]={sSpecies='Warthog',sName='Preview adult',nGender=0,bAlive=true,nAgeGroup=2,enclosure=3}
emit(1,{{nAnimalEntityID=14}})
command({type='enable_transfers'})
for i=1,10 do step(1) end
assert(#transfers==total and #R.hints==0 and #R.candidates==0,'preactivation hints cleared')
-- Existing adults with no fresh native transition are never swept.
command({type='refresh'})
for i=1,10 do step(1) end
assert(#transfers==total,'explicit catalog refresh never moves baseline adults')
-- Exhibits have the same maturation behavior with no pair selection.
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true}})
assert(R.watch.e3 and not R.watch.e1 and not R.watch.e2,'only opted juvenile exhibits watched')
exhibits.e3.age=2
before=counts.exhibitRow or 0
for i=1,1000 do emit(3,{{completelyUnknownPayload='ignored'}}) end
assert((counts.exhibitRow or 0)==before,'unknown exhibit event payload never passed to native API')
step()
assert(#transfers==total+1 and transfers[#transfers].id=='e3','exhibit juvenile matures without breeder pair')
assert(not R.watch.e3,'adult removed from juvenile watch list')
-- New exhibit births trigger one bounded, coalesced opted-exhibit discovery.
exhibits.e4={entity=104,enclosure=99,sSpecies='Axolotl',sName='New exhibit baby',nGender=0,bAlive=true,age=0}
local lists=counts.exhibitList or 0
for i=1,100 do emit(2,{}) end
finish()
assert((counts.exhibitList or 0)==lists+1 and R.watch.e4,'birth storm coalesces into one discovery')
-- Stop discards backlog. Old park receivers must never inject IDs into a new park.
local oldReceiver=receivers[1]
command({type='stop'})
assert(#R.hints==0 and #R.candidates==0 and next(R.watch)==nil)
manager={tWorldAPIs=apis}; step()
oldReceiver({{nAnimalEntityID=12}})
assert(#R.hints==0 and R.mode=='preview' and next(R.rules)==nil,'lifecycle epoch rejects stale park callbacks')
print('Event checks passed: targeted transfers, no callback native calls, burst cap, preview safety, exhibit coalescing')
''')
