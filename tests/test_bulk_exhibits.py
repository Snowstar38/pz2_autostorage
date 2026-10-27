"""Exhibit All/None uses cached groups; native baseline remains bounded and separate."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
command({action='bulk_habitats_on'})
local habitat=R.rules['habitat:3:Warthog']
local cached=R.catalog[1]
for _,a in ipairs(R.catalog) do if a.kind=='exhibit' then cached=a; break end end
R.catalog[#R.catalog+1]=cached
counts={}
assert(R:Command({action='bulk_exhibits_on'}) and #R.queue==1)
local before=R.ruleRevision
R:_Commands()
assert(next(counts)==nil,'command only uses cached catalog, no native enumeration')
assert(R.rules['exhibit:99:Axolotl'].enabled and R.ruleRevision==before+1,'duplicate animals form one exhibit rule')
assert(R.rules['habitat:3:Warthog']==habitat and habitat.enabled and R.mode=='preview','exhibit All preserves habitats and global mode')
assert(R.baselines['exhibit:99'],'fresh one-time baseline protects preactivation adults')
finish()
assert(R.watch.e3 and not R.watch.e1 and not R.watch.e2,'baseline watches only current juveniles')
command({type='enable_transfers'})
counts={}; R:Command({action='bulk_exhibits_off'}); R:_Commands()
assert(next(counts)==nil and not R.rules['exhibit:99:Axolotl'].enabled)
assert(habitat.enabled and R.mode=='active','None preserves habitats/global active state')
for i=1,200 do R.catalog[#R.catalog+1]={kind='exhibit',enclosure=tostring(2000+i),species='ListedExhibit'} end
counts={}; assert(R:Command({action='bulk_exhibits_on'}) and #R.queue==1); R:_Commands()
assert(R.rules['exhibit:2200:ListedExhibit'].enabled and next(counts)==nil,'all cached pages use single native-free command')
assert(R.rules['exhibit:9999:Unlisted']==nil and R.persistenceStatus.dirty,'unlisted groups excluded and save marked dirty')
print('Bulk exhibit toggles passed: cached scope, deduplication, habitat isolation, bounded baseline, one queue entry')
''')
