"""Eligibility waits for current-world proof, not destination metadata."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
assert(R.supported and R.worldKind=='zoo')
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
local oldReceiver=receivers[1]; local oldLoad=serialization.load
local saved={}; serialization.save(saved)
local oldSession=R:GetStatus().sessionId
wildArea=true; currentWildArea=false
manager={tWorldAPIs=apis}; environment={}; counts={}; R:_Reset(manager,environment)
assert(not R.supported and R.phase=='loading' and R.loading and next(receivers)==nil)
assert(counts.registerSerializer==1,'passive config receiver must exist before normal load callback')
assert(not R:Command({type='refresh'}) and not R:Command({type='enable_transfers'}))
for i=1,1000 do step() end
assert(not counts.allHabitats and not counts.allExhibits and not counts.habitatRow and not counts.send,'no gameplay before proof')
assert(R:GetStatus().sessionId~=oldSession)
-- Even false territory during Init cannot temporarily enable a loading reserve.
currentWildArea=true
R:_ConfirmCurrentWorld(environment,apis)
assert(not R.supported and R.worldKind=='reserve' and not R.loading)
assert(not R.persistence and next(receivers)==nil and next(R.rules)==nil)
oldReceiver({{nAnimalEntityID=12}}); oldLoad(saved,1)
assert(next(R.rules)==nil and #R.hints==0 and #transfers==0)
-- A fresh ordinary zoo is supported only after its own post-load proof.
manager={tWorldAPIs=apis}; environment={}; R:_Reset(manager,environment)
currentWildArea=false; assert(R:_ConfirmCurrentWorld(environment,apis)); finish()
assert(R.supported and R.worldKind=='zoo' and next(R.rules)==nil)
assert(#R.catalog==6 and R.phase=='ready','new zoo auto-populates without Refresh')
-- Unknown current-world type is a capability failure, never an early false default.
manager={tWorldAPIs=apis}; environment={}; R:_Reset(manager,environment)
currentWildArea=nil; R:_ConfirmCurrentWorld(environment,apis)
assert(not R.supported and R.worldKind=='unknown' and not R:Command({type='refresh'}))
currentWildArea=false; assert(R:_ConfirmCurrentWorld(environment,apis)); finish()
assert(R.supported and R.phase=='ready')
print('World eligibility passed: passive loading, reserve exclusion, current-world proof, automatic zoo catalog')
''')
