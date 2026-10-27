"""Many enabled habitat rules must not cause recurring native zoo scans."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
counts={}
for i=1,1000 do step(.016) end
assert(next(counts)==nil,'idle unconfigured runtime makes zero native calls')
command({type='refresh'})
local catalogSize=#R.catalog
assert(catalogSize==6 and counts.allHabitats==1,'explicit discovery catalog')
for i=1,200 do command({type='enable_habitat',enclosure=tostring(i),species='Warthog',enabled=true}) end
command({type='enable_transfers'})
counts={}; local full=fullPublishes; local delta=deltaPublishes
for i=1,2000 do step(.016) end
assert(next(counts)==nil,'200 enabled habitat rules generate no recurring animal/capacity/list calls')
assert(fullPublishes==full and deltaPublishes==delta,'idle rules publish nothing')
assert(#R.catalog==catalogSize,'cached catalog retained')
R:Command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true}); step()
animals[12].nAgeGroup=2; counts={}
emit(1,{{nAnimalEntityID=12}}); step()
assert(#transfers==1 and not counts.habitatList and not counts.allHabitats and not counts.allExhibits,'one target only')
assert((counts.habitatRow or 0)<=2,'one target read plus immediate transfer revalidation')
assert(fullPublishes==full+1,'target event uses delta, not full catalog publication')
command({type='stop'})
counts={}; for i=1,1000 do step(.016) end
assert(next(counts)==nil,'stop returns to inert runtime')
print('Performance checks passed: 200 enabled rules/2000 ticks=0 native animal scans; one event checks one target')
''')
