"""Native-free Lua 5.3 fixture shared by event/runtime performance checks."""
from pathlib import Path
from lupa.lua53 import LuaRuntime


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    main = Path(__file__).resolve().parents[1] / 'src/Autostorage/Main'
    for name in ('policy', 'persistence'):
        lua.globals().source = (main / f'breederkeeper.{name}.lua').read_text()
        lua.execute(f"local s=source; package.preload['BreederKeeper.{name.title()}']=function() return assert(load(s))() end")
    lua.execute(r'''
counts={}; transfers={}; receivers={}; serialization={}; fullPublishes=0; deltaPublishes=0
function hit(k) counts[k]=(counts[k] or 0)+1 end
api={messaging={MsgType_AnimalAgedFromJuvenileToAdultMessage=1,
 MsgType_ExhibitAnimalBornMessage=2,MsgType_ExhibitAnimalAgeChangedMessage=3},
 time={GetDeltaTimeUnscaled=function() hit('timer'); return .016 end}}
wildArea=false
api.game={GetEnvironment=function() return {RequireInterface=function(self,name)
 assert(name=='Interfaces.INextWorldDataManager'); return {GetIsWildArea=function() return wildArea end}
end} end}
function api.messaging.RegisterReceiver(kind,fn) receivers[kind]=fn end
function api.messaging.UnregisterReceiver(kind,fn) if receivers[kind]==fn then receivers[kind]=nil end end
function emit(kind,messages) if receivers[kind] then receivers[kind](messages or {}) end end
animals={
 [11]={sSpecies='Warthog',sName='Parent',nGender=0,bAlive=true,nAgeGroup=2,enclosure=3},
 [12]={sSpecies='Warthog',sName='Baby',nGender=1,bAlive=true,nAgeGroup=0,enclosure=3},
 [81]={sSpecies='Nyala',sName='Other',nGender=1,bAlive=true,nAgeGroup=2,enclosure=8}}
exhibits={
 e1={entity=101,enclosure=99,sSpecies='Axolotl',sName='Adult1',nGender=0,bAlive=true,age=2},
 e2={entity=102,enclosure=99,sSpecies='Axolotl',sName='Adult2',nGender=1,bAlive=true,age=2},
 e3={entity=103,enclosure=99,sSpecies='Axolotl',sName='Young',nGender=1,bAlive=true,age=0}}
currentWildArea=false
apis={animals={Juvenile=0},habitat={},exhibits={},park={},worldserialisation={},
 wildterritory={IsWildTerritoryCreationEnabled=function() return currentWildArea end}}
function apis.habitat:GetHabitats() hit('allHabitats'); return {3,8} end
function apis.habitat:GetAnimalsInHabitat(h)
 hit('habitatList'); local out={} for id,a in pairs(animals) do if a.enclosure==h then out[#out+1]=id end end return out
end
function apis.animals:GetUIAnimalListDataForIDs(ids) hit('habitatRow'); local out={} for _,id in ipairs(ids) do out[id]=animals[id] end return out end
function apis.animals:EntityIDToAnimalGUID(id) hit('guid'); return animals[id] and ('g'..id) or '' end
function apis.animals:GetAssignedHabitatEntityID(id) hit('assignment'); return animals[id] and animals[id].enclosure or 0 end
function apis.animals:DoesAnimalExist(id) hit('exists'); return animals[id]~=nil end
function apis.animals:GetAnimalTransportData(id) hit('transport'); return {bHasTransportJob=animals[id].inTransit==true} end
function apis.animals:GetSpecies(id) hit('species'); return animals[id].sSpecies end
function apis.animals:IsAlive(id) hit('alive'); return animals[id] and animals[id].bAlive==true end
function apis.animals:CanSendAnimalToTradeCentre(id) hit('canSend'); return animals[id].canSend~=false end
function apis.animals:AttemptToSendToTradeCentre(id) hit('send'); transfers[#transfers+1]={kind='habitat',id=id,time=R.clock}; animals[id].inTransit=true; return true end
function apis.animals:AnimalGUIDToEntityID(uid) hit('hybrid'); return 0 end
function apis.exhibits:GetAllAnimalIDs() hit('allExhibits'); local ids={} for uid in pairs(exhibits) do ids[#ids+1]=uid end return ids end
function apis.exhibits:ExhibitAnimalUIDToEntityID(uid) hit('exhibitEntity'); return exhibits[uid] and exhibits[uid].entity or 0 end
function apis.exhibits:ExhibitAnimalEntityIDToUID(entity) hit('exhibitUid'); for uid,a in pairs(exhibits) do if a.entity==entity then return uid end end end
function apis.exhibits:GetAnimalParentExhibit(entity) hit('exhibitParent'); for _,a in pairs(exhibits) do if a.entity==entity then return a.enclosure end end return 0 end
function apis.exhibits:GetUIAnimalListDataForIDs(ids) hit('exhibitRow'); local out={} for _,id in ipairs(ids) do out[id]=exhibits[id] end return out end
function apis.exhibits:GetExhibitAnimalAgeQuadrant(entity) hit('exhibitAge'); for _,a in pairs(exhibits) do if a.entity==entity then return a.age end end return -1 end
function apis.exhibits:GetAnimalsInExhibit(entity) hit('exhibitList'); local out={} for _,a in pairs(exhibits) do if a.enclosure==entity then out[#out+1]={nEntityID=a.entity} end end return out end
function apis.exhibits:CanSendAnimalToTradeCentreUID(uid) hit('exhibitCanSend'); return true end
function apis.exhibits:AttemptToSendToTradeCentre(uid) hit('exhibitSend'); transfers[#transfers+1]={kind='exhibit',id=uid,time=R.clock}; return true end
capacity=100
function apis.park:GetTradeCentreMaxCapacity() hit('capacity'); return capacity end
function apis.park:GetNumberOfAnimalsInTradeCentre() hit('capacity'); return 0 end
function apis.park:GetExhibitTradeCentreMaxCapacity() hit('capacity'); return capacity end
function apis.park:GetNumberOfAnimalsInExhibitTradeCentre() hit('capacity'); return 0 end
function apis.worldserialisation:RegisterWorldSerialisationClient(name,version,save,load,old)
 hit('registerSerializer')
 serialization={name=name,version=version,save=save,load=load,old=old}
end
function apis.worldserialisation:UnregisterWorldSerialisationClient(name) hit('unregisterSerializer') end
function apis.worldserialisation:SaveEntityID(entity) return entity+1000 end
remap={}
function apis.worldserialisation:LoadEntityID(token) return remap[token-1000] or token-1000 end
''')
    lua.globals().R = lua.execute((main / 'breederkeeper.runtime.lua').read_text())
    lua.execute(r'''
R.Core={UI={Publish=function() fullPublishes=fullPublishes+1 end,
 PublishDelta=function(self,delta) deltaPublishes=deltaPublishes+1; lastDelta=delta end}}
manager={tWorldAPIs=apis}
environment={}
function step(dt) R:_Tick(manager,dt or .016) end
function finish()
 for i=1,1000 do step(.001); if not R.job and not next(R.baselines) and not R.discover then return end end
 error('scan did not finish')
end
function command(c) R:Command(c); step(); finish() end
R:_Reset(manager,environment)
assert(R:_ConfirmCurrentWorld(environment,apis))
finish()
counts={}
''')
    return lua
