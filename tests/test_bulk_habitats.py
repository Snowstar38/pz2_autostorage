"""Bulk toggles apply cached habitat groups only, with one queued command."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
command({type='refresh'})
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true}})
local exhibit=R.rules['exhibit:99:Axolotl']
counts={}; command({action='bulk_habitats_on'})
assert(R.rules['habitat:3:Warthog'].enabled and R.rules['habitat:8:Nyala'].enabled)
assert(R.rules['exhibit:99:Axolotl']==exhibit and exhibit.enabled,'bulk excludes exhibits')
assert(R.mode=='preview' and next(counts)==nil,'bulk is native-free and does not enable transfers')
command({type='enable_transfers'}); command({action='bulk_habitats_off'})
assert(not R.rules['habitat:3:Warthog'].enabled and not R.rules['habitat:8:Nyala'].enabled)
assert(exhibit.enabled and R.mode=='active','bulk disabling habitats preserves other scopes/global mode')
for i=1,200 do R.catalog[#R.catalog+1]={kind='habitat',enclosure=tostring(1000+i),species='ListedSpecies'} end
assert(R:Command({action='bulk_habitats_on'}) and #R.queue==1,'large bulk uses one queue entry')
step()
assert(R.rules['habitat:1200:ListedSpecies'].enabled and R.persistenceStatus.dirty)
print('Bulk habitat toggles passed: cached scope only, exhibits excluded, native-free, no 50-command limit')
''')
