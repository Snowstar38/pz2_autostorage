"""Bulk advanced options use one command across all cached groups, preserving rules."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true,contraception=true})
command({type='set_rule',kind='exhibit',enclosure='99',species='Axolotl',rule={enabled=true,contraception=true}})
for i=1,120 do
 local enclosure=tostring(1000+i)
 R.catalog[#R.catalog+1]={id='extra'..i,kind='habitat',enclosure=enclosure,species='Warthog'}
end
-- Duplicate animals in a group must not produce duplicate rule writes.
R.catalog[#R.catalog+1]={id='duplicate',kind='habitat',enclosure='3',species='Warthog'}
local exhibit=R.rules['exhibit:99:Axolotl']; local revision=R.ruleRevision
counts={}
assert(R:Command({type='bulk_habitats_males_on'}) and #R.queue==1)
step()
assert(next(counts)==nil,'cached habitat bulk option performs no native scans')
assert(R.ruleRevision==revision+122,'one revision per distinct habitat/species group')
assert(R.rules['habitat:3:Warthog'].enabled and R.rules['habitat:3:Warthog'].contraception,'existing enabled+otheroption preserved')
assert(R.rules['exhibit:99:Axolotl']==exhibit,'other kind unchanged')
for i=1,120 do
 local r=R.rules['habitat:'..(1000+i)..':Warthog']
 assert(r and r.malesOnly and not r.enabled and not r.contraception,'unconfigured groups remain disabled')
end
assert(R.rules['habitat:8:Nyala'].malesOnly and not R.rules['habitat:8:Nyala'].enabled)
local stableRevision=R.ruleRevision
command({type='bulk_habitats_males_on'})
assert(R.ruleRevision==stableRevision,'unchanged aggregate options do not invalidate live events')
command({type='bulk_habitats_contraception_on'})
command({type='bulk_habitats_males_off'})
for id,r in pairs(R.rules) do
 if r.kind=='habitat' then assert(not r.malesOnly and r.contraception and (r.enabled==(r.enclosure=='3'))) end
end
command({type='bulk_exhibits_males_on'}); command({type='bulk_exhibits_contraception_off'})
assert(R.rules['exhibit:99:Axolotl'].enabled and R.rules['exhibit:99:Axolotl'].malesOnly and not R.rules['exhibit:99:Axolotl'].contraception)
assert(R.rules['habitat:3:Warthog'].contraception and not R.rules['habitat:3:Warthog'].malesOnly,'exhibit bulk does not modify habitats')
local saved={}; serialization.save(saved)
assert(#saved.configuration.rules==123,'all groups saved despite UI queue limit')
manager={tWorldAPIs=apis}; environment={}; R:_Reset(manager,environment)
serialization.load(saved,1); R:_ConfirmCurrentWorld(environment,apis); finish()
assert(R.rules['habitat:1120:Warthog'].contraception and not R.rules['habitat:1120:Warthog'].enabled)
assert(R.rules['exhibit:99:Axolotl'].malesOnly and not R.rules['exhibit:99:Axolotl'].contraception)
''')

lua = runtime()
lua.execute(r'''
command({type='enable_habitat',enclosure='3',species='Warthog',enabled=true})
command({type='enable_transfers'})
R.nextTransfer=R.clock+100
animals[12].nAgeGroup=2; emit(1,{{nAnimalEntityID=12}}); step()
assert(#R.candidates==1)
local oldRevision=R.rules['habitat:3:Warthog'].revision
command({type='bulk_habitats_contraception_on'})
assert(R.rules['habitat:3:Warthog'].revision>oldRevision and R.rules['habitat:3:Warthog'].enabled)
R.nextTransfer=0;step()
assert(#transfers==0 and #contraceptions==0,'changed option cannot execute queued old storage or reassign its action')
''')
print('Bulk advanced option checks passed: one queue entry, >50 groups, deduplication, isolation, disabled rules, saved flags and stale-action safety')
