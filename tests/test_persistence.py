"""Optional park serializer lifecycle, without touching any real park/save."""
from pathlib import Path
from lupa.lua53 import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)
source = Path(__file__).resolve().parents[1] / 'src/Autostorage/Main/breederkeeper.persistence.lua'
lua.globals().P = lua.execute(source.read_text(encoding='utf-8'))
lua.execute(r'''
local registered,unregistered,receivers,removed={}, {}, {}, {}
local calls=0
local serial={}
function serial:RegisterWorldSerialisationClient(name,version,save,load,canLoad)
 registered={name=name,version=version,save=save,load=load,canLoad=canLoad}
end
function serial:UnregisterWorldSerialisationClient(name) unregistered[#unregistered+1]=name end
function serial:SaveEntityID(entity) calls=calls+1; return entity+1000 end
function serial:LoadEntityID(token) calls=calls+1; return token==1099 and 199 or 0 end
local bus={MsgType_ExhibitAnimalBornMessage=10,MsgType_AnimalAgedFromJuvenileToAdultMessage=20}
function bus.RegisterReceiver(kind,fn) receivers[kind]=fn end
function bus.UnregisterReceiver(kind,fn) assert(receivers[kind]==fn); removed[#removed+1]=kind end
local state={mode='active',transfersEnabled=true,pending={child={accepted=true}},
 rules={r={id='r',kind='exhibit',enclosure='99',species='Axolotl',enabled=true,
   breeders={'male-guid','female-guid'},removeJuveniles=true}},
 policy={rules={r={seen={child='juvenile',old='baseline',ready='matured'}}},
   pending={ready={accepted=true}}}}
local restored
local p=P.new({capture=function() return state end,restore=function(value) restored=value end})
assert(p:Attach({worldserialisation=serial},bus))
assert(p:Attach({worldserialisation=serial},bus),'idempotent attach')
assert(registered.name=='BreederKeeperState' and registered.version==1)
local saved={}; registered.save(saved)
local row=saved.configuration.rules[1]
assert(row.enclosure==1099 and row.breeders[1]=='male-guid','entity mapping/stable breeder identity')
assert(#row.juvenileIds==1 and row.juvenileIds[1]=='child','persist juveniles only')
assert(saved.mode==nil and saved.pending==nil and saved.configuration.pending==nil,'no authority/requests persisted')
assert(registered.load(saved,1)==true)
local rule=restored.rules['exhibit:199:Axolotl']
assert(rule and rule.enclosure=='199' and rule.breeders[2]=='female-guid','remapped enclosure')
assert(restored.transfersEnabled==true and next(restored.pending)==nil,'enabled config parsed without restoring pending requests')
assert(restored.observations[rule.id].child=='juvenile','juvenile observation restored')
local before=calls
receivers[10]({{nAnimalID='newborn'},{bad=true}})
receivers[20]({{nAnimalEntityID=123}})
assert(calls==before,'event callbacks never call native animal/serializer APIs')
local events,dirty=p:DrainEvents()
assert(dirty and #events==2 and events[1].kind=='exhibit_birth' and events[2].kind=='maturation')
local none,isDirty=p:DrainEvents(); assert(#none==0 and not isDirty)
assert(registered.load({configuration={schema=55,rules={}}},55))
assert(next(restored.rules)==nil and restored.mode=='preview','unknown versions ignored safely')
assert(restored.transfersEnabled==false,'unknown config defaults paused')
assert(registered.load({configuration={schema=1,rules={}}},1) and restored.transfersEnabled==false,'legacy defaults paused')
assert(registered.load({configuration={schema=1,rules={},transfersEnabled='true'}},1) and restored.transfersEnabled==false,'only explicit boolean true restores enabled')
local obsolete={configuration={schema=1,rules={{kind='habitat',species='s',enclosure=333}}}}
assert(registered.load(obsolete,1)); assert(next(restored.rules)==nil,'deleted enclosure ignored')
saved.configuration.rules[2]=saved.configuration.rules[1]
assert(registered.load(saved,1)); assert(next(restored.rules)==nil,'conflicting duplicates discarded')
p:Detach(); assert(#removed==2 and #unregistered==1)
receivers[10]({{nAnimalID='late'}})
local late,lateDirty=p:DrainEvents(); assert(#late==0 and not lateDirty,'late callback ignored')
-- Missing APIs are a capability failure, never an invented persistence path.
assert(not P.new({}):Attach({}))
-- Callbacks are protected so optional malformed configuration cannot block park saves.
local faulty=P.new({capture=function() error('capture broke') end})
assert(faulty:Attach({worldserialisation=serial},bus))
assert(pcall(registered.save,{})); assert(registered.load({},1))
faulty:Detach()
print('Persistence component lifecycle checks passed')
''')
