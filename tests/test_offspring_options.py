"""Offspring sex filters and contraception share the existing event safety gates."""
from runtime_fixture import runtime

for males_only in (False, True):
    for contraception in (False, True):
        lua = runtime()
        lua.globals().male_only = males_only
        lua.globals().use_contraception = contraception
        lua.execute(r'''
command({type='set_rule',kind='habitat',enclosure='3',species='Warthog',rule={enabled=true,malesOnly=male_only,contraception=use_contraception}})
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true,malesOnly=male_only,contraception=use_contraception}})
command({type='enable_transfers'})
-- Existing adults and retained exhibit parents never become targets on enable.
assert(#transfers==0 and #contraceptions==0)
animals[13]={sSpecies='Warthog',sName='Son',nGender=0,bAlive=true,nAgeGroup=2,enclosure=3}
animals[12].nAgeGroup=2
if use_contraception then capacity=0 end -- No trade storage required for contraception.
emit(1,{{nAnimalEntityID=12},{nAnimalEntityID=13}})
for i=1,10 do step(1) end
local expected=male_only and 1 or 2
assert(#transfers==(use_contraception and 0 or expected))
assert(#contraceptions==(use_contraception and expected or 0))
assert(not animals[11].contraception and not animals[11].inTransit,'existing parent untouched')
assert(not male_only or (not animals[12].contraception and not animals[12].inTransit),'female filtered')
-- A birth message can carry the parent ID: selection must preserve both breeders.
exhibits.e3.age=2; exhibits.e3.years=.1
exhibits.e4={entity=104,enclosure=99,sSpecies='Axolotl',sName='Son',nGender=0,bAlive=true,age=2,years=.1}
emit(2,{{nAnimalID=101}})
for i=1,30 do step(1) end
assert(#transfers==(use_contraception and 0 or expected*2))
assert(#contraceptions==(use_contraception and expected*2 or 0))
assert(not exhibits.e1.contraception and not exhibits.e2.contraception,'retained pair untouched')
for _,a in ipairs(transfers) do assert(a.id~=11 and a.id~='e1' and a.id~='e2') end
assert(not male_only or not exhibits.e3.contraception,'female exhibit filtered')
emit(2,{{nAnimalID=102}})
for i=1,20 do step(1) end
assert(#transfers==(use_contraception and 0 or expected*2) and #contraceptions==(use_contraception and expected*2 or 0),'repeated birth reconciliation does not repeat claimed actions')
-- Strict booleans round trip through native save; bulk switches retain settings.
local saved={}; serialization.save(saved)
for _,r in ipairs(saved.configuration.rules) do assert(r.malesOnly==male_only and r.contraception==use_contraception) end
command({type='bulk_habitats_off'}); command({type='bulk_habitats_on'})
assert(R.rules['habitat:3:Warthog'].malesOnly==male_only and R.rules['habitat:3:Warthog'].contraception==use_contraception)
manager={tWorldAPIs=apis}; environment={}; R:_Reset(manager,environment)
serialization.load(saved,1); R:_ConfirmCurrentWorld(environment,apis); finish()
for _,r in pairs(R.rules) do assert(r.malesOnly==male_only and r.contraception==use_contraception) end
assert(#R.candidates==0,'load does not replay actions')
''')

# Old save files have the original behavior and explicit false values on resave.
lua = runtime()
lua.execute(r'''
serialization.load({configuration={schema=1,rules={{kind='habitat',species='Warthog',enclosure=1003,enabled=true}},transfersEnabled=true}},1)
local r=R.rules['habitat:3:Warthog']
assert(r.malesOnly==false and r.contraception==false)
animals[12].nAgeGroup=2; emit(1,{{nAnimalEntityID=12}}); step()
assert(#transfers==1 and #contraceptions==0,'legacy female offspring still sent to trade centre')
''')
# Recheck sex at execution time and fail closed when the game does not apply contraception.
lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true,malesOnly=true,contraception=true})
animals[12].nAgeGroup=2
local a={id='g12',kind='habitat',enclosure='3',species='Warthog',ruleId='habitat:3:Warthog'}
assert(R:_Transfer(apis,a)==false and #contraceptions==0,'current native sex excludes females')
animals[12].nGender=0
apis.animals.SetUsingContraceptive=function() end
assert(not pcall(R._Transfer,R,apis,a) and #transfers==0,'unconfirmed contraception never falls back to storage')
''')
# An edited rule invalidates actions waiting in the bounded execution queue.
lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
R.nextTransfer=R.clock+100
animals[12].nAgeGroup=2; emit(1,{{nAnimalEntityID=12}}); step()
assert(#R.candidates==1)
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true,contraception=true})
step(101)
assert(#transfers==0 and #contraceptions==0,'option edits discard queued actions from the old revision')
''')
print('Offspring option checks passed: all sex/action combinations, parents, persistence, legacy defaults')
