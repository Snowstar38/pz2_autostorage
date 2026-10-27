-- Optional lifecycle component; not wired into the runtime by this module.
-- Call Attach from park manager Init and Detach before manager Shutdown.
-- capture() returns {rules=runtime.rules, policy=runtime.policy}.
-- restore(state) receives remapped config plus transfersEnabled (legacy false).
local global=_G
local type,pairs,ipairs=global.type,global.pairs,global.ipairs
local tostring,tonumber,pcall=global.tostring,global.tonumber,global.pcall
local table,math=global.table,global.math
local api=global.api
local Persistence=global.module and global.module(...) or {}
local methods={}
local VERSION=1
local function valid(v) return type(v)=='string' and v~='' end
local function numberId(v)
    local n=tonumber(v)
    return n and n>0 and n<math.huge and n%1==0 and n or nil
end
local function groupKey(kind,enclosure,species)
    return kind..':'..enclosure..':'..species
end
function Persistence.new(options)
    local self={options=options or {},events={},attached=false,version=VERSION,
        name='BreederKeeperState',messages={}}
    for k,v in pairs(methods) do self[k]=v end
    return self
end
function methods:_Report(text)
    if #self.messages<20 then self.messages[#self.messages+1]=text end
end
function methods:Save(destination)
    if type(destination)~='table' or not self.serializer then return end
    local ok,state=pcall(self.options.capture or function() return {} end)
    if not ok or type(state)~='table' then self:_Report('Configuration capture failed'); return end
    local saved={schema=VERSION,rules={},transfersEnabled=state.transfersEnabled==true}
    local rules=type(state.rules)=='table' and state.rules or {}
    for _,rule in pairs(rules) do
        if #saved.rules>=1000 then self:_Report('Rule persistence limit reached'); break end
        if type(rule)=='table' and (rule.kind=='habitat' or rule.kind=='exhibit') and valid(rule.species) then
            local entity=numberId(rule.enclosure)
            if entity then
                local success,token=pcall(self.serializer.SaveEntityID,self.serializer,entity)
                if success and token~=nil then
                    local entry={kind=rule.kind,species=rule.species,enclosure=token,
                        enabled=rule.enabled==true,removeJuveniles=rule.removeJuveniles==true,
                        breeders={},juvenileIds={}}
                    if type(rule.breeders)=='table' and valid(rule.breeders[1]) and valid(rule.breeders[2]) and rule.breeders[1]~=rule.breeders[2] then
                        entry.breeders={rule.breeders[1],rule.breeders[2]}
                    end
                    local memory=type(state.policy)=='table' and type(state.policy.rules)=='table' and state.policy.rules[rule.id]
                    local observations=type(state.observations)=='table' and state.observations[rule.id]
                    local seen=observations or (memory and memory.seen) or {}
                    if type(seen)=='table' then
                        for id,stage in pairs(seen) do
                            if valid(id) and stage=='juvenile' and #entry.juvenileIds<50000 then
                                entry.juvenileIds[#entry.juvenileIds+1]=id
                            end
                        end
                    end
                    table.sort(entry.juvenileIds)
                    saved.rules[#saved.rules+1]=entry
                else self:_Report('Could not save enclosure '..tostring(rule.enclosure)) end
            else self:_Report('Invalid enclosure identity '..tostring(rule.enclosure)) end
        end
    end
    -- Only this whitelisted payload is exposed to the game's serializer.
    destination.configuration=saved
    if type(self.options.onSaved)=='function' then pcall(self.options.onSaved) end
end
function methods:Load(source,version)
    local restored={rules={},observations={},mode='preview',transfersEnabled=false,pending={},messages={}}
    local data=type(source)=='table' and source.configuration
    if not self.serializer or version~=VERSION or type(data)~='table' or data.schema~=VERSION or type(data.rules)~='table' then
        self:_Report('No compatible saved Autostorage configuration; preview defaults restored')
    else
        restored.transfersEnabled=data.transfersEnabled==true
        local duplicates={}
        for index,entry in ipairs(data.rules) do
            if index>1000 then break end
            if type(entry)=='table' and (entry.kind=='habitat' or entry.kind=='exhibit') and valid(entry.species) and entry.enclosure~=nil then
                local ok,entity=pcall(self.serializer.LoadEntityID,self.serializer,entry.enclosure)
                entity=ok and numberId(entity) or nil
                if entity then
                    local enclosure=tostring(entity)
                    local id=groupKey(entry.kind,enclosure,entry.species)
                    if restored.rules[id] or duplicates[id] then
                        restored.rules[id]=nil; restored.observations[id]=nil; duplicates[id]=true
                        self:_Report('Ignored duplicate saved enclosure/species rule')
                    else
                        local rule={id=id,kind=entry.kind,enclosure=enclosure,species=entry.species,
                            enabled=entry.enabled==true,removeJuveniles=entry.removeJuveniles==true,breeders={}}
                        if type(entry.breeders)=='table' and valid(entry.breeders[1]) and valid(entry.breeders[2]) and entry.breeders[1]~=entry.breeders[2] then
                            rule.breeders={entry.breeders[1],entry.breeders[2]}
                        end
                        restored.rules[id]=rule
                        local seen={}
                        if type(entry.juvenileIds)=='table' then
                            for count,animal in ipairs(entry.juvenileIds) do
                                if count>50000 then break end
                                if valid(animal) then seen[animal]='juvenile' end
                            end
                        end
                        restored.observations[id]=seen
                    end
                else self:_Report('Saved enclosure no longer exists; rule ignored') end
            else self:_Report('Malformed saved rule ignored') end
        end
    end
    self.restored=restored
    if type(self.options.restore)=='function' then
        local ok=pcall(self.options.restore,restored)
        if not ok then self:_Report('Restored configuration callback failed') end
    end
    -- Never let optional mod configuration prevent the park itself from loading.
    return true
end
function methods:_Queue(kind,messages,field)
    if not self.attached or type(messages)~='table' then return end
    for _,message in pairs(messages) do
        if type(message)=='table' and (type(message[field])=='number' or type(message[field])=='string') and #self.events<2000 then
            self.events[#self.events+1]={kind=kind,nativeId=message[field]}
        end
    end
    self.dirty=true
end
function methods:DrainEvents()
    local events,dirty=self.events,self.dirty==true
    self.events={}; self.dirty=false
    return events,dirty
end
function methods:Attach(worldAPIs,messaging)
    if self.attached then return true end
    local serializer=worldAPIs and worldAPIs.worldserialisation
    if not serializer or type(serializer.RegisterWorldSerialisationClient)~='function' or
        type(serializer.UnregisterWorldSerialisationClient)~='function' or
        type(serializer.SaveEntityID)~='function' or type(serializer.LoadEntityID)~='function' then
        return false,'World serializer unavailable'
    end
    self.serializer=serializer
    local ok,err=pcall(serializer.RegisterWorldSerialisationClient,serializer,self.name,VERSION,
        function(t)
            local saved=pcall(self.Save,self,t)
            if not saved then self:_Report('Optional configuration save failed') end
        end,
        function(t,v)
            local loaded=pcall(self.Load,self,t,v)
            if not loaded then self:_Report('Optional configuration load failed') end
            return true
        end,function() return true end)
    if not ok or err==false then self.serializer=nil; return false,tostring(err) end
    self.attached=true; self.messaging=self.options.events~=false and (messaging or (api and api.messaging)) or nil; self.receivers={}
    local bus=self.messaging
    if bus and type(bus.RegisterReceiver)=='function' and type(bus.UnregisterReceiver)=='function' then
        local types={
            {name='MsgType_ExhibitAnimalBornMessage',kind='exhibit_birth',field='nAnimalID'},
            {name='MsgType_AnimalAgedFromJuvenileToAdultMessage',kind='maturation',field='nAnimalEntityID'}}
        for _,spec in ipairs(types) do
            local messageType=bus[spec.name]
            if messageType~=nil then
                local fn=function(messages) self:_Queue(spec.kind,messages,spec.field) end
                local registered=pcall(bus.RegisterReceiver,messageType,fn)
                if registered then self.receivers[#self.receivers+1]={type=messageType,fn=fn}
                else self:_Report('Could not register '..spec.name) end
            end
        end
    end
    return true
end
function methods:Detach()
    self.attached=false
    if self.messaging then
        for _,receiver in ipairs(self.receivers or {}) do
            pcall(self.messaging.UnregisterReceiver,receiver.type,receiver.fn)
        end
    end
    if self.serializer then pcall(self.serializer.UnregisterWorldSerialisationClient,self.serializer,self.name) end
    self.serializer=nil; self.messaging=nil; self.receivers={}; self.events={}; self.dirty=false
end
return Persistence
