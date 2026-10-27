-- Event adapter. Per-zoo configuration uses the native park serializer.
local global = _G
local require, type, pairs, ipairs = global.require, global.type, global.pairs, global.ipairs
local tostring, tonumber, pcall, error = global.tostring, global.tonumber, global.pcall, global.error
local table, math = global.table, global.math
local next = global.next
local setmetatable = global.setmetatable
local api = global.api
local Policy = require('BreederKeeper.Policy')
local Runtime = global.module and global.module(...) or {}
Runtime.queue,Runtime.rules={},{}
Runtime.clock,Runtime.nextScan,Runtime.interval,Runtime.mode=0,0,5,'preview'
Runtime.rowsPerFrame=3
local function copy(t)
    if type(t) ~= 'table' then return t end
    local r = {}; for k,v in pairs(t) do r[k]=copy(v) end; return r
end
local function call(o,n,...)
    if o == nil or type(o[n]) ~= 'function' then error('Unavailable API: '..n) end
    return o[n](o,...)
end
local function key(kind,enclosure,species)
    return kind..':'..enclosure..':'..species
end
local function exhibitAge(apis,entity,uid)
    local age=call(apis.exhibits,'GetExhibitAnimalAgeQuadrant',entity)
    if type(age)~='number' or age<0 or age>3 or age%1~=0 then
        error('Unsupported exhibit age for '..tostring(uid)..': '..tostring(age))
    end
    return age
end
local function displayName(entity)
    if api and api.ui2 and type(api.ui2.GetEntityName)=='function' then
        local ok,name=pcall(api.ui2.GetEntityName,entity)
        if ok and type(name)=='string' and name~='' then return name end
    end
    return tostring(entity)
end
function Runtime:_Observe(stage,manager,environment,detail)
    local hooks=self.hookDiagnostics or {counts={},history={}}
    self.hookDiagnostics=hooks
    hooks.counts[stage]=(hooks.counts[stage] or 0)+1
    if stage=='managerAdvance' then hooks.lastAdvanceManager=tostring(manager); return end
    hooks.history[#hooks.history+1]={stage=stage,manager=tostring(manager),
        environment=tostring(environment),activeManager=tostring(self.manager),
        session=self.context and self.context.sessionId or 'none',phase=self.phase or 'none',
        supported=self.supported==true,detail=tostring(detail or '')}
    while #hooks.history>32 do table.remove(hooks.history,1) end
end
function Runtime:_AttachTransitionObserver()
    if self.transitionObserver then return end
    local bus=api and api.messaging
    if not bus or bus.MsgType_WorldTransitionMessage==nil or type(bus.RegisterGlobalReceiver)~='function' then return end
    local observer=function(messages)
        if type(messages)~='table' then return end
        for _,message in ipairs(messages) do
            if type(message)=='table' and type(message.Event)=='string' then
                local active='unavailable'
                if api.world and type(api.world.GetActive)=='function' then
                    local ok,value=pcall(api.world.GetActive)
                    if ok then active=tostring(value) end
                end
                self.transitionState=self.transitionState or {counts={}}
                local state=self.transitionState
                state.counts[message.Event]=(state.counts[message.Event] or 0)+1
                state.lastEvent=message.Event; state.activeWorld=active
                self:_Observe('worldTransition',self.manager,self.managerEnvironment,
                    message.Event..' active='..active)
            end
        end
    end
    local ok,result=pcall(bus.RegisterGlobalReceiver,bus.MsgType_WorldTransitionMessage,observer)
    if ok and result~=false then
        -- Intentionally process-wide: park Reset/Shutdown must not detach this
        -- read-only observer. It never adopts a manager or changes eligibility.
        self.transitionObserver=observer
        self:_Observe('transitionListener',nil,nil,'registered')
    end
end
function Runtime:Command(c)
    if self.supported~=true or self.loading then return false end
    if type(c) ~= 'table' or #self.queue >= 50 then return false end
    self.diagnostics=self.diagnostics or {received=0,processed=0,ticks=0}
    self.diagnostics.received=self.diagnostics.received+1
    self.diagnostics.lastQueued=tostring(c.type or c.action)
    self.queue[#self.queue+1]=copy(c); return true
end
Runtime.QueueUICommand=Runtime.Command
function Runtime:GetStatus()
    local status=self.status or {mode='preview',status='Waiting for a park',animals={},rules={},proposals={},messages={}}
    status.diagnostics=self.diagnostics or {received=0,processed=0,ticks=0}
    status.diagnostics.pendingEvents=#(self.hints or {})+#(self.candidates or {})
    status.diagnostics.hooks=self.hookDiagnostics or {counts={},history={}}
    status.diagnostics.activeManager=tostring(self.manager)
    status.diagnostics.activeEnvironment=tostring(self.managerEnvironment)
    status.diagnostics.eventsAttached=self.eventsAttached==true
    status.diagnostics.transitions=self.transitionState or {counts={}}
    status.diagnostics.transitionListener=self.transitionObserver~=nil
    status.persistence=self.persistenceStatus or {available=false,dirty=false}
    status.supported=self.supported==true; status.eligible=status.supported
    status.worldKind=self.worldKind or 'unknown'; status.unsupportedReason=self.unsupportedReason
    status.sessionId=self.context and self.context.sessionId or 'no-park'
    status.sessionEpoch=self.sessionEpoch or 0
    status.loading=self.loading==true; status.phase=self.phase or 'closed'
    return status
end
function Runtime:_Publish()
    if self.Core and self.Core.UI and type(self.Core.UI.Publish)=='function' then
        self.Core.UI:Publish(nil,self:GetStatus())
    end
end
function Runtime:_Reset(manager,environment)
    self.retiredManagers=self.retiredManagers or setmetatable({},{__mode='k'})
    if self.manager and self.manager~=manager then self.retiredManagers[self.manager]=true end
    self.retiredManagers[manager]=nil
    self:_DetachLifecycle()
    self.manager=manager; self.managerEnvironment=environment; self.queue={}; self.rules={}; self.mode='preview'
    self.sessionEpoch=self.lifecycleEpoch
    self.clock=0; self.nextScan=0; self.job=nil; self.lastSnapshot=nil
    self.catalog={}; self.catalogNames={}; self.discover=false; self.lastStatusSignature=nil
    self.diagnostics={received=0,processed=0,ticks=0}
    self.context={zooId=tostring(manager),sessionId=tostring(manager)..':park:'..tostring(self.lifecycleEpoch)}
    self.policy=Policy.new(self.context)
    self.hints={}; self.hintKeys={}; self.candidates={}; self.candidateKeys={}; self.claimed={}
    self.watch={}; self.baselines={}; self.receivers={}; self.nextTransfer=0
    self.hasRules=false; self.hasExhibitAgeEvent=false; self.exhibit_birth=false; self.exhibit_age=false
    self.eventSequence=0; self.permissionEpoch=0
    self.ruleRevision=0; self.nextExhibitSignal=0; self.nextExhibitBirth=0
    self.native={}; self.catalogById={}
    self.diagnostics.eventMode='events'; self.diagnostics.eventsReceived=0
    self.diagnostics.eventsProcessed=0; self.diagnostics.scansStarted=0
    self.eventLog={}; self.persistenceStatus={available=false,dirty=false}
    self.status={mode='preview',status='Loading your zoo...',animals={},rules={},proposals={},messages={}}
    self.supported=false; self.worldKind='loading'; self.loading=true; self.phase='loading'
    self.unsupportedReason=nil; self.pendingSaved=nil; self.eventsAttached=false
    self:_AttachPersistence(manager.tWorldAPIs)
    self:_Observe('reset',manager,environment,'passive loading')
    self:_Publish()
end
function Runtime:_CloseManager(manager)
    self.retiredManagers=self.retiredManagers or setmetatable({},{__mode='k'})
    self.retiredManagers[manager]=true
    -- Old world teardown may finish after a new park manager initialized.
    if self.manager~=manager then return false end
    self:_DetachLifecycle()
    self.mode='preview'; self.queue={}; self.rules={}; self.job=nil; self.manager=nil
    self.hasRules=false; self.hints={}; self.hintKeys={}; self.candidates={}; self.candidateKeys={}; self.watch={}
    self.supported=false; self.worldKind='unknown'; self.unsupportedReason='No zoo is active.'
    self.loading=false; self.phase='closed'; self.pendingSaved=nil; self.managerEnvironment=nil
    self.status={mode='preview',status='Park closed',animals={},rules={},proposals={},messages={}}
    self:_Publish()
    return true
end
function Runtime:_ConfirmCurrentWorld(environment,worldAPIs)
    -- MainHUD.Init runs after current-world territory and serializer loading.
    -- Destination metadata can retain a previous reserve flag, so it is never
    -- authoritative here. An old HUD must not classify a newer manager.
    self:_Observe('confirm',self.manager,environment,tostring(worldAPIs))
    if not self.manager or not environment or environment~=self.managerEnvironment then
        self:_Observe('confirmRejected',self.manager,environment,'missing manager or environment mismatch')
        return false
    end
    local ok,isWild=pcall(function()
        local territory=worldAPIs and worldAPIs.wildterritory
        if not territory or type(territory.IsWildTerritoryCreationEnabled)~='function' then return nil end
        return territory:IsWildTerritoryCreationEnabled()
    end)
    if not ok or type(isWild)~='boolean' then
        self.supported=false; self.worldKind='unknown'; self.phase='unsupported'; self.loading=false
        self.unsupportedReason='World type could not be verified; Autostorage is disabled.'
        self.status.status=self.unsupportedReason
        self:_Observe('confirmUnknown',self.manager,environment,tostring(isWild))
        self:_Publish()
        return false
    end
    if isWild then
        self.supported=false; self.worldKind='reserve'; self.phase='unsupported'; self.loading=false
        self.unsupportedReason='Autostorage is disabled in wildlife reserves.'
        self.mode='preview'; self.pendingSaved=nil; self.rules={}; self.queue={}; self.hints={}; self.candidates={}
        if self.persistence then self.persistence:Detach(); self.persistence=nil end
        self.persistenceStatus={available=false,dirty=false}; self.hasRules=false
        self.status.status=self.unsupportedReason
        self:_Observe('confirmReserve',self.manager,environment,'current-world flag true')
        self:_Publish()
        return false
    end
    if self.supported and self.worldKind=='zoo' then return true end
    self.supported=true; self.worldKind='zoo'; self.unsupportedReason=nil
    self:_Observe('confirmZoo',self.manager,environment,'current-world flag false')
    if self.pendingSaved then self:_ApplySavedConfig(self.pendingSaved); self.pendingSaved=nil end
    self:_AttachLifecycle(self.manager.tWorldAPIs)
    self.discover=true; self.loading=true; self.phase='loading'; self.status.status='Loading your zoo...'
    self:_Publish()
    return true
end
function Runtime:_DetachLifecycle()
    self.lifecycleEpoch=(self.lifecycleEpoch or 0)+1
    if self.persistence then self.persistence:Detach(); self.persistence=nil end
    if api and api.messaging then
        for _,r in ipairs(self.receivers or {}) do pcall(api.messaging.UnregisterReceiver,r.type,r.fn) end
    end
    self.receivers={}
end
function Runtime:_ApplySavedConfig(saved)
    self.rules=saved.rules or {}; self.mode=saved.transfersEnabled==true and 'active' or 'preview'
    self.policy=Policy.new(self.context)
    self.claimed={}; self.candidates={}; self.candidateKeys={}; self.hints={}; self.hintKeys={}
    for _,r in pairs(self.rules) do r.sinceEvent=self.eventSequence; r.revision=0 end
    self.hasRules=false
    for _,r in pairs(self.rules) do if r.enabled then self.hasRules=true; break end end
    self.status.mode=self.mode; self.status.status=self.mode=='active' and 'Saved automation enabled' or 'Saved rules restored; paused'
    self.persistenceStatus.dirty=false
end
function Runtime:_AttachPersistence(apis)
    local lifecycleEpoch=self.lifecycleEpoch
    if not self.persistence and apis and apis.worldserialisation then
        local Persistence=require('BreederKeeper.Persistence')
        self.persistence=Persistence.new({events=false,
            capture=function()
                if lifecycleEpoch~=self.lifecycleEpoch then return {} end
                if self.pendingSaved then return {rules=self.pendingSaved.rules,
                    transfersEnabled=self.pendingSaved.transfersEnabled==true} end
                return {rules=self.rules,transfersEnabled=self.mode=='active'}
            end,
            onSaved=function() if lifecycleEpoch==self.lifecycleEpoch then self.persistenceStatus.dirty=false end end,
            restore=function(saved)
                if lifecycleEpoch~=self.lifecycleEpoch or self.worldKind=='reserve' then return end
                if self.supported then self:_ApplySavedConfig(saved)
                else self.pendingSaved={rules=saved.rules or {},transfersEnabled=saved.transfersEnabled==true} end
            end})
        local ok,err=self.persistence:Attach(apis)
        self.persistenceStatus={available=ok==true,error=err,dirty=false}
    end
end
function Runtime:_AttachLifecycle(apis)
    if self.eventsAttached or self.supported~=true then return end
    self:_AttachPersistence(apis)
    local lifecycleEpoch=self.lifecycleEpoch
    local bus=api and api.messaging
    if not bus or type(bus.RegisterReceiver)~='function' or type(bus.UnregisterReceiver)~='function' then return end
    self.eventsAttached=true
    local specs={
        {name='MsgType_AnimalAgedFromJuvenileToAdultMessage',kind='habitat',field='nAnimalEntityID',event='maturity'},
        {name='MsgType_ExhibitAnimalBornMessage',signal='exhibit_birth'},
        {name='MsgType_ExhibitAnimalAgeChangedMessage',signal='exhibit_age'}}
    for _,spec in ipairs(specs) do
        local messageType=bus[spec.name]
        if messageType~=nil then
            local fn=function(messages)
                if lifecycleEpoch~=self.lifecycleEpoch or self.supported~=true or not self.hasRules then return end
                self.diagnostics.eventsReceived=self.diagnostics.eventsReceived+1
                if spec.signal then self[spec.signal]=true
                elseif type(messages)=='table' then
                    for _,m in pairs(messages) do
                        if type(m)=='table' and type(m[spec.field])=='number' then
                            self:_QueueHint({kind=spec.kind,entity=m[spec.field],event=spec.event})
                        end
                    end
                end
            end
            local ok=pcall(bus.RegisterReceiver,messageType,fn)
            if ok then self.receivers[#self.receivers+1]={type=messageType,fn=fn} end
            if spec.signal=='exhibit_age' then self.hasExhibitAgeEvent=ok end
        end
    end
end
function Runtime:_QueueHint(hint)
    local id=hint.kind..':'..tostring(hint.uid or hint.entity)
    local existing=self.hintKeys[id]
    if existing then
        if hint.event=='birth' then existing.born=true end
        if hint.event=='maturity' then existing.event='maturity' end
        return
    end
    if #self.hints>=2000 then self.diagnostics.backlogOverflow=true; return end
    self.eventSequence=self.eventSequence+1
    hint.key=id; hint.born=hint.event=='birth'; hint.sequence=self.eventSequence
    hint.epoch=self.permissionEpoch; hint.permission=self.mode; self.hintKeys[id]=hint
    self.hints[#self.hints+1]=hint
end
function Runtime:_QueueCandidate(action)
    local id=action.kind..':'..action.id
    if not self.claimed[id] and not self.candidateKeys[id] and #self.candidates<2000 then
        self.candidateKeys[id]=true; self.candidates[#self.candidates+1]=action
    end
end
function Runtime:_Log(animal,result)
    self.eventLog[#self.eventLog+1]={id=animal.id,name=animal.name or animal.id,species=animal.species,
        enclosure=self.catalogNames[animal.enclosure] or animal.enclosure,result=result}
    while #self.eventLog>10 do table.remove(self.eventLog,1) end
end
function Runtime:_Delta(animal)
    self.status.mode=self.mode; self.status.eventLog=self.eventLog
    self.status.diagnostics=self.diagnostics; self.status.persistence=self.persistenceStatus
    self.diagnostics.pendingEvents=#self.hints+#self.candidates
    if self.Core and self.Core.UI and type(self.Core.UI.PublishDelta)=='function' then
        self.Core.UI:PublishDelta({animals=animal and {animal} or {},mode=self.mode,
            status=self.status.status,proposals=self.status.proposals or {},eventLog=self.eventLog,
            diagnostics=self.diagnostics,persistence=self.persistenceStatus,
            sessionId=self.context.sessionId,sessionEpoch=self.sessionEpoch,
            supported=self.supported,eligible=self.supported,worldKind=self.worldKind,
            loading=self.loading==true,phase=self.phase})
    end
end
function Runtime:_Commands()
    local q=self.queue; self.queue={}
    if #q>0 then self.job=nil end
    for _,c in ipairs(q) do
        local action=c.type or c.action
        self.diagnostics=self.diagnostics or {received=0,processed=0,ticks=0}
        self.diagnostics.processed=self.diagnostics.processed+1
        self.diagnostics.lastProcessed=tostring(action)
        if action=='stop' or action=='stop_all' then
            self.mode='preview'; self.rules={}; self.policy=Policy.new(self.context)
            self.hints={}; self.hintKeys={}; self.candidates={}; self.candidateKeys={}; self.watch={}; self.baselines={}
            self.permissionEpoch=self.permissionEpoch+1
            self.persistenceStatus.dirty=true
        elseif action=='refresh' then self.discover=true; self.nextScan=0
        elseif action=='preview' then self.nextScan=0
        elseif action=='enable_transfers' or (action=='set_mode' and c.mode=='APPLY') then
            -- Permission changes invalidate queued preview events through the epoch.
            self.mode='active'; self.nextScan=0
            self.permissionEpoch=self.permissionEpoch+1; self.hints={}; self.hintKeys={}; self.candidates={}; self.candidateKeys={}
            self.exhibit_birth=false; self.exhibit_age=false
            self.persistenceStatus.dirty=true
        elseif action=='set_mode' then
            self.mode='preview'; self.nextScan=0; self.permissionEpoch=self.permissionEpoch+1
            self.hints={}; self.hintKeys={}; self.candidates={}; self.candidateKeys={}
            self.exhibit_birth=false; self.exhibit_age=false
            self.persistenceStatus.dirty=true
        elseif action=='bulk_habitats_on' or action=='bulk_habitats_off' or
               action=='bulk_exhibits_on' or action=='bulk_exhibits_off' then
            local kind=(action=='bulk_exhibits_on' or action=='bulk_exhibits_off') and 'exhibit' or 'habitat'
            local enabled=action=='bulk_habitats_on' or action=='bulk_exhibits_on'
            local applied={}
            for _,a in ipairs(self.catalog or {}) do
                if a.kind==kind then
                    local id=key(kind,a.enclosure,a.species)
                    if not applied[id] then
                        applied[id]=true; self.ruleRevision=self.ruleRevision+1
                        self.rules[id]={id=id,kind=kind,enclosure=a.enclosure,species=a.species,
                            enabled=enabled,sinceEvent=self.eventSequence,revision=self.ruleRevision}
                        if enabled and kind=='exhibit' then
                            self.baselines[kind..':'..a.enclosure]={kind=kind,enclosure=a.enclosure}
                        end
                        if not enabled then self.policy.rules[id]=nil end
                    end
                end
            end
            self.persistenceStatus.dirty=true
        elseif action=='set_exhibit_breeders' or action=='enable_habitat' or action=='set_rule' then
            local enclosure=tostring(c.enclosure or c.enclosureId or '')
            local species=c.species
            local kind=c.kind or (action=='enable_habitat' and 'habitat' or 'exhibit')
            if action=='set_rule' then
                for _,a in ipairs(self.catalog or {}) do
                    if a.enclosure==enclosure and a.species==species then kind=a.kind; break end
                end
            end
            local rule=c.rule or c
            if enclosure~='' and type(species)=='string' and species~='' then
                local id=key(kind,enclosure,species)
                self.ruleRevision=self.ruleRevision+1
                self.rules[id]={id=id,kind=kind,enclosure=enclosure,species=species,
                    enabled=rule.enabled~=false,sinceEvent=self.eventSequence,revision=self.ruleRevision}
                if rule.enabled~=false and kind=='exhibit' then self.baselines[kind..':'..enclosure]={kind=kind,enclosure=enclosure}
                else self.policy.rules[id]=nil end
                self.nextScan=0
                self.persistenceStatus.dirty=true
            end
        end
    end
    self.hasRules=false
    for _,rule in pairs(self.rules) do if rule.enabled then self.hasRules=true; break end end
    if #q>0 and self.status then
        self.lastStatusSignature=nil
        self.status.mode=self.mode; self.status.rules=self:_RuleList(); self.status.proposals={}
        self.status.status=self.mode=='active' and 'Monitoring selected enclosures' or 'Paused'
        for _,group in ipairs(self.status.enclosures or {}) do
            group.rule=self.rules[key(group.kind,group.id,group.species)]
        end
        self:_Publish()
    end
end
function Runtime:_RuleList()
    local r={}; for _,v in pairs(self.rules) do r[#r+1]=v end
    table.sort(r,function(a,b) return a.id<b.id end); return r
end
function Runtime:_Fail(message)
    self.mode='preview'; self.job=nil; self.discover=false
    self.status=self.status or {}
    self.status.mode='preview'; self.status.status='Paused'; self.status.error=tostring(message)
    self.status.messages={tostring(message)}
    self.loading=false; self.phase=self.supported and 'ready' or 'unsupported'
    self.permissionEpoch=(self.permissionEpoch or 0)+1
    self.hints={}; self.hintKeys={}; self.candidates={}; self.candidateKeys={}
    if self.diagnostics then self.diagnostics.lastError=tostring(message) end
    self.nextScan=self.clock+self.interval
    self:_Publish()
end
-- _BeginScan and _ScanStep use only APIs evidenced in the installed game's scripts.
function Runtime:_BeginScan(apis,full)
    local job={animals={},native={},tasks={},index=1,names={},scope={},full=full==true}
    if full then
        local habitats=call(apis.habitat,'GetHabitats')
        if type(habitats)~='table' then error('Habitat list unavailable') end
        for _,h in pairs(habitats) do
            if type(h)~='number' then error('Unexpected habitat identity') end
            job.tasks[#job.tasks+1]={entity=h,kind='habitat_list'}
        end
        local exhibitIds=call(apis.exhibits,'GetAllAnimalIDs')
        if type(exhibitIds)~='table' then error('Exhibit list unavailable') end
        for _,uid in pairs(exhibitIds) do job.tasks[#job.tasks+1]={uid=uid,kind='exhibit'} end
    else
        for scope,rule in pairs(self.baselines) do
            if not job.scope[scope] then
                local entity=tonumber(rule.enclosure)
                if not entity then error('Invalid opted enclosure identity') end
                job.scope[scope]=true
                job.tasks[#job.tasks+1]={entity=entity,
                    kind=rule.kind=='habitat' and 'habitat_list' or 'exhibit_list'}
            end
        end
    end
    self.diagnostics.scansStarted=self.diagnostics.scansStarted+1
    self.job=job
end
function Runtime:_ScanStep(apis)
    local job=self.job
    local stop=math.min(#job.tasks,job.index+self.rowsPerFrame-1)
    for i=job.index,stop do
        local task=job.tasks[i]
        if task.kind=='habitat_list' then
            local ids=call(apis.habitat,'GetAnimalsInHabitat',task.entity)
            if type(ids)~='table' then error('Habitat animals unavailable') end
            local enclosure=tostring(task.entity)
            job.names[enclosure]=self.catalogNames[enclosure] or displayName(task.entity)
            for _,id in pairs(ids) do
                job.tasks[#job.tasks+1]={entity=id,enclosure=enclosure,kind='habitat'}
            end
        elseif task.kind=='exhibit_list' then
            local rows=call(apis.exhibits,'GetAnimalsInExhibit',task.entity)
            if type(rows)~='table' then error('Exhibit animals unavailable') end
            for _,row in pairs(rows) do
                if type(row)~='table' or type(row.nEntityID)~='number' then error('Exhibit member identity unavailable') end
                job.tasks[#job.tasks+1]={entity=row.nEntityID,kind='exhibit'}
            end
        elseif task.kind=='exhibit' then
            local uid=task.uid or call(apis.exhibits,'ExhibitAnimalEntityIDToUID',task.entity)
            local entity=task.entity or call(apis.exhibits,'ExhibitAnimalUIDToEntityID',uid)
            if entity~=nil and entity~=0 then
                local enclosure=call(apis.exhibits,'GetAnimalParentExhibit',entity)
                if enclosure~=nil and enclosure~=0 then
                    job.names[tostring(enclosure)]=self.catalogNames[tostring(enclosure)] or job.names[tostring(enclosure)] or displayName(enclosure)
                    local rows=call(apis.exhibits,'GetUIAnimalListDataForIDs',{uid})
                    local row=type(rows)=='table' and rows[uid]
                    if type(row)~='table' then error('Exhibit record unavailable') end
                    local age=exhibitAge(apis,entity,uid)
                    local stable=tostring(uid)
                    local a={id=stable,species=row.sSpecies,enclosure=tostring(enclosure),kind='exhibit',
                        juvenile=age==0,alive=row.bAlive,
                        inStorage=false,inTransit=false,name=row.sName or stable,
                        sex=row.nGender==0 and 'male' or (row.nGender==1 and 'female' or 'unknown'),
                        mature=age~=0}
                    job.animals[#job.animals+1]=a
                    job.native[a.id]={entity=entity,uid=uid,kind='exhibit',enclosure=a.enclosure}
                end
            end
        else
        local id=task.entity
        local rows=call(apis.animals,'GetUIAnimalListDataForIDs',{id})
        local row=type(rows)=='table' and rows[id]
        if type(row)~='table' then error('Animal record unavailable') end
        local guid=call(apis.animals,'EntityIDToAnimalGUID',id)
        if guid==nil or tostring(guid)=='' or guid==0 then error('Animal GUID unavailable') end
        if apis.animals.Juvenile==nil or type(row.nAgeGroup)~='number' then error('Age classification unavailable') end
        local a={id=tostring(guid),species=row.sSpecies,enclosure=task.enclosure,kind=task.kind,
            juvenile=row.nAgeGroup==apis.animals.Juvenile,alive=row.bAlive,
            inStorage=false,inTransit=false,name=row.sName or tostring(guid),
            sex=row.nGender==0 and 'male' or (row.nGender==1 and 'female' or 'unknown'),
            mature=row.nAgeGroup~=apis.animals.Juvenile}
        -- Presence in a habitat list is not enough: reject an existing transport job.
        local transport=call(apis.animals,'GetAnimalTransportData',id)
        if type(transport)~='table' then error('Transport state unavailable') end
        a.inTransit=transport.bHasTransportJob==true
        job.animals[#job.animals+1]=a
        job.native[a.id]={entity=id,kind='habitat',enclosure=task.enclosure}
        end
    end
    job.index=stop+1
    if job.index>#job.tasks then self:_FinishScan(apis,job); self.job=nil end
end
function Runtime:_FinishScan(apis,job)
    if job.targeted then return self:_FinishTarget(apis,job) end
    local max=call(apis.park,'GetTradeCentreMaxCapacity')
    local used=call(apis.park,'GetNumberOfAnimalsInTradeCentre')
    local exhibitMax=call(apis.park,'GetExhibitTradeCentreMaxCapacity')
    local exhibitUsed=call(apis.park,'GetNumberOfAnimalsInExhibitTradeCentre')
    if type(max)~='number' or type(used)~='number' then error('Capacity unavailable') end
    local snapshot={zooId=self.context.zooId,sessionId=self.context.sessionId,complete=true,
        animals=job.animals,capacity={habitat=math.max(0,max-used),
            exhibit=math.max(0,exhibitMax-exhibitUsed)}}
    local rules=self:_RuleList()
    -- Baselines only initialize exhibit observations; habitat transitions come
    -- directly from native messages. Never cross-product all rules and zoo rows.
    local decision={actions={},pauses={}}
    for _,a in ipairs(job.animals) do
        if a.kind=='exhibit' then
            local rule=self.rules[key(a.kind,a.enclosure,a.species)]
            if rule and rule.enabled then Policy.observe(self.policy,a,rule,self.context) end
        end
    end
    self.lastSnapshot=snapshot; self.native=self.native or {}
    for id,record in pairs(job.native) do self.native[id]=record end
    for scope in pairs(job.scope) do self.baselines[scope]=nil end
    for _,a in ipairs(job.animals) do
        local r=self.rules[key(a.kind,a.enclosure,a.species)]
        if a.kind=='exhibit' and a.juvenile and r and r.enabled then
            local record=job.native[a.id]
            self.watch[a.id]={kind='exhibit',uid=record.uid,event='exhibit_check'}
        end
    end
    if job.full then self.discover=false; self.loading=false; self.phase='ready' end
    local signature={self.mode,tostring(max),tostring(used),tostring(exhibitMax),tostring(exhibitUsed)}
    for _,a in ipairs(job.animals) do
        signature[#signature+1]=table.concat({a.id,a.kind,a.enclosure,a.species,
            tostring(a.juvenile),tostring(a.alive),tostring(a.inTransit),a.name,a.sex},'|')
    end
    for _,r in ipairs(rules) do signature[#signature+1]=r.id..':'..tostring(r.enabled)..':'..table.concat(r.breeders or {},',') end
    for _,a in ipairs(decision.actions) do signature[#signature+1]='action:'..a.id end
    for _,p in ipairs(decision.pauses) do signature[#signature+1]='pause:'..p.ruleId..':'..p.reason end
    table.sort(signature)
    local fingerprint=table.concat(signature,'\30')
    self.nextScan=self.clock+self.interval
    if fingerprint==self.lastStatusSignature and not job.full then return end
    self.lastStatusSignature=fingerprint
    -- Keep unmonitored rows cached; only explicit discovery refreshes the whole zoo.
    local catalog={}
    if not job.full then
        for _,a in ipairs(self.catalog) do
            if not job.scope[a.kind..':'..a.enclosure] then catalog[#catalog+1]=a end
        end
    end
    for _,a in ipairs(job.animals) do catalog[#catalog+1]=a end
    self.catalog=catalog
    self.catalogById={}
    for _,a in ipairs(catalog) do self.catalogById[a.id]=a end
    for enclosure,name in pairs(job.names) do self.catalogNames[enclosure]=name end
    self.status={mode=self.mode,status=self.mode=='active' and 'Monitoring' or 'Paused',
        animals=catalog,rules=rules,proposals=decision.actions,pauses=decision.pauses,
        capacity={used=used,total=max},exhibitCapacity={used=exhibitUsed,total=exhibitMax},messages={},enclosures={}}
    local groups={}
    for _,a in ipairs(catalog) do
        local k=key(a.kind,a.enclosure,a.species)
        if not groups[k] then
            groups[k]={id=a.enclosure,name=self.catalogNames[a.enclosure] or a.enclosure,kind=a.kind,species=a.species,animals={},rule=self.rules[k]}
            self.status.enclosures[#self.status.enclosures+1]=groups[k]
        end
        groups[k].animals[#groups[k].animals+1]=a
    end
    -- Discovery and rule baselines never transfer animals. Only fresh lifecycle hints do.
    self.status.proposals={}
    self.nextScan=self.clock+self.interval
    self:_Publish()
end
function Runtime:_Signals()
    if self.exhibit_birth and self.clock>=self.nextExhibitBirth then
        self.exhibit_birth=false
        self.nextExhibitBirth=self.clock+10
        for _,r in pairs(self.rules) do
            if r.enabled and r.kind=='exhibit' then self.baselines['exhibit:'..r.enclosure]={kind='exhibit',enclosure=r.enclosure} end
        end
    end
    if self.exhibit_age and self.clock>=self.nextExhibitSignal then
        self.exhibit_age=false
        self.nextExhibitSignal=self.clock+5
        for id,hint in pairs(self.watch) do
            local row=self.catalogById and self.catalogById[id]
            local r=row and self.rules[key('exhibit',row.enclosure,row.species)]
            if r and r.enabled then self:_QueueHint(copy(hint)) else self.watch[id]=nil end
        end
    end
end
function Runtime:_ProcessHint(apis)
    local hint=table.remove(self.hints,1)
    if not hint then return end
    self.hintKeys[hint.key]=nil
    self.diagnostics.eventsProcessed=self.diagnostics.eventsProcessed+1
    if hint.epoch~=self.permissionEpoch then return end
    if hint.kind=='habitat' then
        if call(apis.animals,'DoesAnimalExist',hint.entity)~=true then return end
        local enclosure=call(apis.animals,'GetAssignedHabitatEntityID',hint.entity)
        if type(enclosure)~='number' or enclosure==0 then return end
        hint.enclosure=tostring(enclosure)
    end
    self.job={animals={},native={},tasks={hint},index=1,names={},scope={},targeted=hint}
    self:_ScanStep(apis)
end
function Runtime:_FinishTarget(apis,job)
    local hint=job.targeted
    local a=job.animals[1]
    if not a then
        if hint.uid then self.watch[tostring(hint.uid)]=nil end
        return
    end
    local rule=self.rules[key(a.kind,a.enclosure,a.species)]
    if not rule or not rule.enabled or hint.sequence<=(rule.sinceEvent or 0) then return end
    self.catalogNames[a.enclosure]=self.catalogNames[a.enclosure] or displayName(tonumber(a.enclosure))
    self.native=self.native or {}; self.native[a.id]=job.native[a.id]
    local eligible,stage=Policy.observe(self.policy,a,rule,self.context)
    if a.kind=='habitat' then
        -- This exact native event proves the juvenile -> adult transition.
        eligible=hint.event=='maturity' and a.alive==true and not a.juvenile and not a.inTransit
    end
    if a.kind=='exhibit' then
        if a.juvenile then self.watch[a.id]={kind='exhibit',uid=job.native[a.id].uid,event='exhibit_check'}
        else self.watch[a.id]=nil end
    end
    if self.catalogById and self.catalogById[a.id] then
        local old=self.catalogById[a.id]
        for k,v in pairs(a) do old[k]=v end
    end
    if eligible and not self.claimed[a.kind..':'..a.id] then
        local action={id=a.id,kind=a.kind,enclosure=a.enclosure,species=a.species,ruleId=rule.id,
            epoch=hint.epoch,name=a.name,ruleRevision=rule.revision}
        if self.mode=='active' and hint.permission=='active' then self:_QueueCandidate(action)
        else self.status.proposals={action} end
        self:_Log(a,self.mode=='active' and 'maturity event received' or 'paused: matured')
        self:_Delta(a)
    end
end
function Runtime:_TryTransfer(apis)
    if self.mode~='active' or self.clock<self.nextTransfer or #self.candidates==0 then return end
    local action=table.remove(self.candidates,1)
    local id=action.kind..':'..action.id
    self.candidateKeys[id]=nil
    local rule=self.rules[action.ruleId]
    if action.epoch~=self.permissionEpoch or not rule or not rule.enabled or
        rule.revision~=action.ruleRevision or self.claimed[id] then return end
    self.nextTransfer=self.clock+self.interval
    self:_Transfer(apis,action)
    self.claimed[id]=true
    local animal=(self.catalogById or {})[action.id] or action
    self:_Log(animal,'storage request accepted')
    self.status.status='Watching maturity events'
    self.status.messages={'Storage requested: '..(action.name or action.id)..' ('..action.species..')'}
    self:_Delta(animal)
end
function Runtime:_Transfer(apis,action)
    local record=self.native[action.id]
    if not record then error('Animal identity unavailable') end
    if record.kind=='exhibit' then
        local rule=self.rules[action.ruleId]
        if not rule or not rule.enabled then error('Exhibit rule changed') end
        local uid=record.uid
        local entity=call(apis.exhibits,'ExhibitAnimalUIDToEntityID',uid)
        if entity~=record.entity or tostring(call(apis.exhibits,'GetAnimalParentExhibit',entity))~=action.enclosure then
            error('Exhibit animal identity or enclosure changed')
        end
        local rows=call(apis.exhibits,'GetUIAnimalListDataForIDs',{uid})
        local row=type(rows)=='table' and rows[uid]
        local age=exhibitAge(apis,entity,uid)
        if type(row)~='table' or row.bAlive~=true or row.sSpecies~=action.species or
           type(age)~='number' or age==0 then
            error('Exhibit candidate changed')
        end
        -- Hybrid species need a destructive RemoveAnimal follow-up in the game's UI.
        -- This adapter deliberately pauses those until independently validated.
        local counterpart=call(apis.animals,'AnimalGUIDToEntityID',uid)
        if counterpart~=nil and counterpart~=0 then error('Hybrid exhibit transfer requires manual game action') end
        if call(apis.exhibits,'CanSendAnimalToTradeCentreUID',uid)~=true then error('Game refused exhibit transfer eligibility') end
        if call(apis.park,'GetNumberOfAnimalsInExhibitTradeCentre')>=call(apis.park,'GetExhibitTradeCentreMaxCapacity') then error('Exhibit storage full') end
        local accepted=call(apis.exhibits,'AttemptToSendToTradeCentre',uid)==true
        Policy.ack(self.policy,action.id,accepted,self.clock)
        if not accepted then error('Game rejected exhibit transfer; automation stopped') end
        self.status.messages={'Requested exhibit storage for '..action.id}
        return
    end
    local id=record.entity
    if tostring(call(apis.animals,'EntityIDToAnimalGUID',id))~=action.id then error('Animal identity changed') end
    if tostring(call(apis.animals,'GetAssignedHabitatEntityID',id))~=action.enclosure then error('Animal enclosure changed') end
    if call(apis.animals,'GetSpecies',id)~=action.species then error('Animal species changed') end
    if call(apis.animals,'IsAlive',id)~=true then error('Animal no longer alive') end
    local current=call(apis.animals,'GetUIAnimalListDataForIDs',{id})
    local row=type(current)=='table' and current[id]
    if type(row)~='table' or type(row.nAgeGroup)~='number' or row.nAgeGroup==apis.animals.Juvenile then
        error('Animal maturation state changed')
    end
    if call(apis.animals,'CanSendAnimalToTradeCentre',id)~=true then error('Game refused transfer eligibility') end
    if call(apis.park,'GetNumberOfAnimalsInTradeCentre')>=call(apis.park,'GetTradeCentreMaxCapacity') then error('Storage full') end
    local accepted=call(apis.animals,'AttemptToSendToTradeCentre',id)==true
    Policy.ack(self.policy,action.id,accepted,self.clock)
    if not accepted then error('Game rejected transfer; automation stopped') end
    self.status.messages={'Requested storage for '..action.id}
end
function Runtime:_Tick(manager,dt)
    if manager.bStartedShutdown==true then return end
    if self.manager~=manager then
        if self.retiredManagers and self.retiredManagers[manager] then return end
        self:_Reset(manager)
    end
    self.diagnostics.ticks=self.diagnostics.ticks+1
    if self.supported~=true then return end
    self:_Commands()
    -- No repeated enclosure polls. A configured rule only listens for game messages.
    if not self.job and not self.discover and not next(self.baselines) and not self.hasRules and
        #self.hints==0 and #self.candidates==0 then return end
    -- UI update counters use this exact unscaled, no-argument engine API.
    if type(dt)~='number' then
        if api and api.time and type(api.time.GetDeltaTimeUnscaled)=='function' then
            dt=api.time.GetDeltaTimeUnscaled()
        end
    end
    if type(dt)~='number' or dt<0 then error('Unscaled timer unavailable') end
    self.clock=self.clock+math.max(0,math.min(dt,1))
    local apis=manager.tWorldAPIs
    if type(apis)~='table' then error('Park manager world APIs unavailable') end
    if not self.hasExhibitAgeEvent and self.clock>=self.nextExhibitSignal then self.exhibit_age=true end
    self:_Signals()
    if not self.job then
        if self.discover then self:_BeginScan(apis,true)
        elseif next(self.baselines) then self:_BeginScan(apis,false) end
    end
    if self.job then self:_ScanStep(apis) else self:_ProcessHint(apis) end
    self:_TryTransfer(apis)
end
function Runtime:Init(Core)
    self.Core=Core; Core.Runtime=self
    self:_AttachTransitionObserver()
    Core:AddModulePatch('Managers.HeatMapManager',function(m)
        self:_Observe('managerModule',nil,nil,tostring(m))
        local originalInit=m.Init
        if type(originalInit)=='function' then
            m.Init=function(manager,...)
                local properties,environment=...
                self:_Observe('managerInit',manager,environment,'before original')
                local results=table.pack(originalInit(manager,...))
                local ok,err=pcall(self._Reset,self,manager,environment)
                if not ok then self:_Fail(err) end
                return table.unpack(results,1,results.n)
            end
        end
        local originalShutdown=m.Shutdown
        if type(originalShutdown)=='function' then
            m.Shutdown=function(manager,...)
                self:_Observe('managerShutdown',manager,nil,self.manager==manager and 'active' or 'stale')
                pcall(self._CloseManager,self,manager)
                return originalShutdown(manager,...)
            end
        end
        local original=m.Advance
        if type(original)~='function' then self:_Fail('Park tick unavailable'); return end
        m.Advance=function(manager,...)
            self:_Observe('managerAdvance',manager,nil)
            local results=table.pack(original(manager,...))
            local ok,err=pcall(self._Tick,self,manager,...)
            if not ok then self:_Fail(err) end
            return table.unpack(results,1,results.n)
        end
    end)
    self.hudEnvironments=self.hudEnvironments or setmetatable({},{__mode='k'})
    Core:AddModulePatch('Windows.MainHUD',function(m)
        self:_Observe('hudModule',nil,nil,tostring(m))
        local originalInit=m.Init
        if type(originalInit)=='function' then
            m.Init=function(hud,environment,...)
                self:_Observe('hudInit',self.manager,environment,'before original')
                local results=table.pack(originalInit(hud,environment,...))
                self:_Observe('hudReady',self.manager,environment,'after original')
                self.hudEnvironments[hud]=environment
                local ok,err=pcall(self._ConfirmCurrentWorld,self,environment,hud.tWorldAPIs)
                if not ok then self:_Fail(err) end
                return table.unpack(results,1,results.n)
            end
        end
        local originalActivate=m.OnActivate
        if type(originalActivate)=='function' then
            m.OnActivate=function(hud,...)
                self:_Observe('hudActivate',self.manager,self.hudEnvironments[hud],'before original')
                local results=table.pack(originalActivate(hud,...))
                local ok,err=pcall(self._ConfirmCurrentWorld,self,self.hudEnvironments[hud],hud.tWorldAPIs)
                if not ok then self:_Fail(err) end
                return table.unpack(results,1,results.n)
            end
        end
    end)
end
return Runtime
