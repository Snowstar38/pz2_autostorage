"""Immediate native revalidation remains in place with event dispatch."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
command({type='refresh'})
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
animals[12].nAgeGroup=2
local action={id='g12',kind='habitat',enclosure='3',species='Warthog',ruleId='habitat:3:Warthog'}
local original=apis.animals.EntityIDToAnimalGUID
apis.animals.EntityIDToAnimalGUID=function() return 'changed-guid' end
assert(not pcall(R._Transfer,R,apis,action) and #transfers==0,'identity swap rejected')
apis.animals.EntityIDToAnimalGUID=original
animals[12].enclosure=8
assert(not pcall(R._Transfer,R,apis,action) and #transfers==0,'enclosure change rejected')
animals[12].enclosure=3; animals[12].bAlive=false
assert(not pcall(R._Transfer,R,apis,action) and #transfers==0,'dead animal rejected')
animals[12].bAlive=true; animals[12].nAgeGroup=0
assert(not pcall(R._Transfer,R,apis,action) and #transfers==0,'juvenile rejected')
animals[12].nAgeGroup=2; capacity=0
assert(not pcall(R._Transfer,R,apis,action) and #transfers==0,'full capacity rejected')
capacity=100; animals[12].canSend=false
assert(not pcall(R._Transfer,R,apis,action) and #transfers==0,'normal game eligibility enforced')
animals[12].canSend=true
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true}})
local exhibit={id='e3',kind='exhibit',enclosure='99',species='Axolotl',ruleId='exhibit:99:Axolotl'}
for _,age in ipairs({-1,.5,4}) do
 exhibits.e3.age=age
 assert(not pcall(R._Transfer,R,apis,exhibit) and #transfers==0,'unknown exhibit age rejected')
end
exhibits.e3.age=2
local hybrid=apis.animals.AnimalGUIDToEntityID
apis.animals.AnimalGUIDToEntityID=function() return 100 end
assert(not pcall(R._Transfer,R,apis,exhibit) and #transfers==0,'unsupported hybrid paused safely')
apis.animals.AnimalGUIDToEntityID=hybrid
local oldReceiver=receivers[1]
manager={tWorldAPIs=apis}; step()
oldReceiver({{nAnimalEntityID=12}})
assert(R.mode=='preview' and next(R.rules)==nil and #R.hints==0,'new park resets permission and stale callbacks')
print('Runtime safety checks passed')
''')
