"""Pre-rename saved config remains readable under the Autostorage package identity."""
from pathlib import Path
import xml.etree.ElementTree as ET
from runtime_fixture import runtime

root = Path(__file__).resolve().parents[1]
pack = root / 'src/Autostorage'
manifest = ET.parse(pack / 'Manifest.xml').getroot()
assert manifest.findtext('Name') == 'Autostorage'
assert manifest.findtext('ID') == '32cd874b-145a-40bb-8cb8-27de1f2b515d'
assert manifest.findtext('Version') == '1'
assert (pack / 'Main/database.autostorageluadatabase.lua').is_file()
assert not (pack / 'Main/database.breederkeeperluadatabase.lua').exists()

lua = runtime()
lua.execute(r'''
-- Literal legacy schema: saved by BreederKeeper pack, no package-folder path inside.
local oldSave={configuration={schema=1,transfersEnabled=true,rules={
 {kind='habitat',species='Warthog',enclosure=1003,enabled=true,breeders={},juvenileIds={}},
 {kind='exhibit',species='Axolotl',enclosure=1099,enabled=false,breeders={},juvenileIds={}}
}}}
assert(serialization.name=='BreederKeeperState' and serialization.version==1,
 'renamed pack must register the exact previous native serializer identity')
manager={tWorldAPIs=apis}; environment={}; R:_Reset(manager,environment)
remap[3]=30; remap[99]=199
assert(serialization.load(oldSave,1))
assert(not R.supported and R.mode=='preview','renaming must not bypass current-world readiness')
assert(R:_ConfirmCurrentWorld(environment,apis)); finish()
assert(R.mode=='active' and R.rules['habitat:30:Warthog'].enabled,
 'old global enabled flag and habitat rules restore after enclosure remap')
assert(R.rules['exhibit:199:Axolotl'].enabled==false,'old disabled exhibit rule preserved')
assert(#R.candidates==0 and #R.hints==0 and next(R.claimed)==nil,'no pending transfers introduced by migration')
local resaved={}; serialization.save(resaved)
assert(resaved.configuration.schema==1 and resaved.configuration.transfersEnabled==true)
assert(#resaved.configuration.rules==2,'new normal save preserves both migrated rules')
oldSave.configuration.transfersEnabled=false
manager={tWorldAPIs=apis}; environment={}; R:_Reset(manager,environment)
assert(serialization.load(oldSave,1)); R:_ConfirmCurrentWorld(environment,apis); finish()
assert(R.mode=='preview','old paused preference also survives rename')
print('Rename compatibility passed: preserved UUID/client/schema, legacy active+paused config, rules/remap, no queued requests')
''')
