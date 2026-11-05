"""Adult-born exhibits retain oldest of each sex, with live queue revalidation."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true}})
command({type='enable_transfers'})
-- Father has presentation quadrant 0; actual age, never quadrant, selects parents.
exhibits.e1.age=0; exhibits.e1.years=10
exhibits.e2.years=9
exhibits.e3.age=2; exhibits.e3.years=.1
exhibits.e4={entity=104,enclosure=99,sSpecies='Axolotl',sName='Son',nGender=0,bAlive=true,age=2,years=.2}
local before=counts.exhibitRow or 0
for i=1,100 do emit(2,{{nAnimalID=101}}) end
assert((counts.exhibitRow or 0)==before and #transfers==0,'birth callback does no native reads and never targets parent ID')
finish()
for i=1,7 do step(1) end
assert(#transfers==2,'both younger extras stored')
local moved={}; for _,t in ipairs(transfers) do moved[t.id]=true end
assert(moved.e3 and moved.e4 and not moved.e1 and not moved.e2,'oldest male and female retained regardless of quadrant')
''')

lua = runtime()
lua.execute(r'''
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true}})
command({type='enable_transfers'})
R.nextTransfer=R.clock+20
exhibits.e3.years=.1
emit(2,{{nAnimalID=101}}); finish()
assert(#R.candidates==1,'birth discovers younger female')
exhibits.e2.bAlive=false
for i=1,25 do step(1) end
assert(#transfers==0 and not R.claimed['exhibit:e3'],'daughter becomes retained female when mother dies before request')
-- Discovery and activation never sweep existing extras.
command({type='refresh'}); for i=1,6 do step(1) end
assert(#transfers==0)
command({action='set_mode',mode='PREVIEW'})
exhibits.e2.bAlive=true; emit(2,{{nAnimalID=101}}); finish()
command({type='enable_transfers'}); for i=1,12 do step(1) end
assert(#transfers==0,'paused birth cannot transfer after activation')
print('Exhibit birth checks passed: adult-born extras, exact ages, parent payload, both sexes, revalidation, preview safety')
''')

# Interleave scanning and commands rather than completing each scan atomically.
lua = runtime()
lua.execute(r'''
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true}})
command({type='enable_transfers'})
R.rowsPerFrame=1; R.nextTransfer=R.clock+50
exhibits.e3.years=.1
emit(2,{{nAnimalID=101}}); step(); assert(R.job,'birth scan started')
R:Command({type='refresh'}); step(); finish()
assert(#R.candidates==1,'refresh cancellation preserves pending birth')
R.candidates={}; R.candidateKeys={}; R.nextExhibitBirth=0
R.baselines['exhibit:99']={kind='exhibit',enclosure='99'}
step(); assert(R.job)
emit(2,{{nAnimalID=101}}); finish(); step(); finish()
assert(#R.candidates==1,'birth arriving during baseline is processed after baseline completes')
-- Missing quadrant is harmless when exact age is available.
R.candidates={}; R.candidateKeys={}; R.nextExhibitBirth=0
function apis.exhibits:GetExhibitAnimalAgeQuadrant(entity) return nil end
emit(2,{{nAnimalID=101}}); finish(); R.nextTransfer=0; step()
assert(#transfers==1 and transfers[1].id=='e3','precise age works without presentation quadrant')
''')

lua = runtime()
lua.execute(r'''
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true}})
command({type='enable_transfers'})
exhibits.e3.years=.1
exhibits.x1={entity=201,enclosure=199,sSpecies='Axolotl',nGender=1,bAlive=true,age=2,years=10}
exhibits.x2={entity=202,enclosure=199,sSpecies='Axolotl',nGender=1,bAlive=true,age=2,years=1}
command({type='refresh'})
command({type='set_rule',kind='exhibit',enclosure='199',species='Axolotl',rule={enabled=true}})
emit(2,{{nAnimalID=101}}); finish(); step()
assert(#transfers==1 and transfers[1].id=='e3','birth only reconciles its exhibit/species')
R.nextExhibitBirth=0
emit(2,{{nAnimalID=99999}}); finish(); step()
assert(#transfers==1,'unresolved event never falls back to a global sweep')
-- A rule revision after callback cannot authorize an older birth.
R.nextExhibitBirth=0
emit(2,{{nAnimalID=201}})
command({type='set_rule',kind='exhibit',enclosure='199',species='Axolotl',rule={enabled=true}})
for i=1,10 do step(1) end
assert(#transfers==1,'rule revision captured at callback rejects later re-enable')
''')
