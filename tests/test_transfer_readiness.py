"""Finite readiness retries preserve fresh-event permission and transfer identity."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
animals[12].nAgeGroup=2; animals[12].canSend=false
emit(1,{{nAnimalEntityID=12}}); step()
assert(#transfers==0 and #R.candidates==1 and R.mode=='active')
assert(R.candidates[1].readinessAttempts==1,'first explicit readiness refusal queued')
animals[12].canSend=true
for i=1,6 do step(1) end
assert(#transfers==1 and R.claimed['habitat:g12'] and #R.candidates==0,'aging animation clears and same animal succeeds')
for i=1,20 do step(1) end
assert(#transfers==1,'accepted transfer never retried')
''')

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
animals[12].nAgeGroup=2; animals[12].canSend=false
emit(1,{{nAnimalEntityID=12}}); step()
local ok,err=true,nil
for i=1,20 do ok,err=pcall(step,1); if not ok then R:_Fail(err); break end end
assert(not ok and tostring(err):find('after 4 attempts') and R.mode=='preview' and #R.candidates==0,'persistent explicit false stops after four attempts')
assert(#transfers==0 and counts.canSend==4)
''')

lua = runtime()
lua.execute(r'''
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true}})
command({type='enable_transfers'})
local tries=0
function apis.exhibits:AttemptToSendToTradeCentre(uid)
 tries=tries+1
 if tries==1 then return false end
 transfers[#transfers+1]={kind='exhibit',id=uid}; return true
end
emit(2,{{nAnimalID=101}}); finish()
assert(tries==1 and #R.candidates==1 and not R.claimed['exhibit:e3'])
for i=1,6 do step(1) end
assert(tries==2 and #transfers==1 and R.claimed['exhibit:e3'],'explicit send refusal then success')
''')

lua = runtime()
lua.execute(r'''
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true}})
command({type='enable_transfers'})
local tries=0
function apis.exhibits:CanSendAnimalToTradeCentreUID(uid) tries=tries+1; return false end
emit(2,{{nAnimalID=101}}); finish()
assert(tries==1 and #R.candidates==1)
exhibits.e2.bAlive=false
for i=1,6 do step(1) end
assert(tries==1 and #transfers==0 and #R.candidates==0,'retry revalidates keeper and cancels daughter after mother dies')
''')

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
animals[12].nAgeGroup=2; animals[12].canSend=false; capacity=0
emit(1,{{nAnimalEntityID=12}})
local ok,err=pcall(step)
assert(not ok and tostring(err):find('Storage full') and not counts.canSend and #R.candidates==0,'capacity failure is permanent before readiness retry')
''')

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
animals[12].nAgeGroup=2
function apis.animals:AttemptToSendToTradeCentre(id) error('uncertain native outcome') end
emit(1,{{nAnimalEntityID=12}})
local ok,err=pcall(step)
assert(not ok and tostring(err):find('uncertain native outcome') and #R.candidates==0,'exception after send never retried')
print('Readiness retries passed: habitat aging delay, exhibit refusal, four-attempt limit, keeper revalidation, capacity and uncertain-send safety')
''')

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
animals[12].nAgeGroup=2; animals[12].canSend=false
emit(1,{{nAnimalEntityID=12}}); step()
animals[13]={sSpecies='Warthog',nGender=0,bAlive=true,nAgeGroup=2,enclosure=3}
emit(1,{{nAnimalEntityID=13}}); step()
for i=1,12 do step(1) end
assert(#transfers==1 and transfers[1].id==13 and #R.candidates==1,'refused candidate tail requeue allows ready animals through')
animals[12].canSend=true; R.clock=R.clock+30; step()
assert(#transfers==2 and transfers[2].id==12,'ready animal succeeds after queue delay exceeds readiness window')
''')

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
animals[12].nAgeGroup=2; animals[12].canSend=false
emit(1,{{nAnimalEntityID=12}}); step()
animals[12].inTransit=true; animals[12].canSend=true
for i=1,6 do step(1) end
assert(#transfers==0 and #R.candidates==0,'manual transport during retry cancels duplicate request')
''')

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
animals[12].nAgeGroup=2
local tries=0
function apis.animals:AttemptToSendToTradeCentre(id)
 tries=tries+1
 if tries==1 then return false end
 transfers[#transfers+1]={kind='habitat',id=id}; animals[id].inTransit=true; return true
end
emit(1,{{nAnimalEntityID=12}}); step()
assert(tries==1 and #R.candidates==1 and not R.claimed['habitat:g12'])
for i=1,6 do step(1) end
assert(tries==2 and #transfers==1 and R.claimed['habitat:g12'],'habitat explicit request refusal then success')
''')
