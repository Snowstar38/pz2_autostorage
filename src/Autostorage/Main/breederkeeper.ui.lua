-- BreederKeeper's original HUD bridge. Commands only enter the runtime queue.
local global = _G
local api = global.api
local type, pairs, pcall = global.type, global.pairs, global.pcall
local math, string, table = global.math, global.string, global.table
local tostring, coroutine = global.tostring, global.coroutine
local UI = module(...)
local function json(value, seen)
    local t = type(value)
    if t == 'nil' then return 'null' end
    if t == 'boolean' then return value and 'true' or 'false' end
    if t == 'number' then if value ~= value or value == math.huge or value == -math.huge then return 'null' end return tostring(value) end
    if t == 'string' then
        return '"' .. value:gsub('[%z\1-\31\\"]', function(c)
            local escapes = {['"']='\\"',['\\']='\\\\',['\n']='\\n',['\r']='\\r',['\t']='\\t'}
            return escapes[c] or string.format('\\u%04x',string.byte(c))
        end) .. '"'
    end
    if t ~= 'table' then return 'null' end
    seen = seen or {}; if seen[value] then return 'null' end; seen[value] = true
    local count, max, array = 0, 0, true
    for k in pairs(value) do count=count+1; if type(k)~='number' or k<1 or k%1~=0 then array=false else max=math.max(max,k) end end
    array=array and max==count
    local parts={}
    if array then for i=1,count do parts[#parts+1]=json(value[i],seen) end
    else for k,v in pairs(value) do if type(k)=='string' or type(k)=='number' then parts[#parts+1]=json(tostring(k),seen)..':'..json(v,seen) end end end
    seen[value]=nil
    return (array and '[' or '{')..table.concat(parts,',')..(array and ']' or '}')
end
UI.Encode = json
UI.GetDiagnostics = function(self)
    return {attached=self.bAttached==true,hasView=self.oUI~=nil,
        sequence=self.nPublicationSequence or 0,clientAcks=self.nClientAcks or 0,
        clientSession=self.sClientSession,clientSupported=self.bClientSupported,
        clientSource=self.sClientSource,lastPublishOK=self.bLastPublishOK,
        lastPublishError=self.sLastPublishError,lastRuntime=self.tLastRuntimeState}
end
UI._PublishEvent = function(self,oUI,event,snapshot)
    local outgoing={}
    for k,v in pairs(snapshot or {}) do outgoing[k]=v end
    self.nPublicationSequence=(self.nPublicationSequence or 0)+1
    outgoing.uiSequence=self.nPublicationSequence
    self.tLastRuntimeState=self.tLastRuntimeState or {}
    local fields={'sessionId','sessionEpoch','supported','worldKind','phase','loading'}
    for i=1,#fields do local field=fields[i];if outgoing[field]~=nil then self.tLastRuntimeState[field]=outgoing[field] end end
    if event=='BKSnapshot' then
        outgoing.bridge={received=self.nCommandsReceived or 0,lastCommand=self.sLastCommand,
            error=self.sBridgeError,attached=self.bAttached==true,view=self:GetDiagnostics()}
    end
    oUI=oUI or self.oUI
    if not oUI or type(oUI.TriggerEventAtNextAdvance)~='function' then
        self.bLastPublishOK=false;self.sLastPublishError='No ready HUD view';return false
    end
    local ok,err=pcall(oUI.TriggerEventAtNextAdvance,oUI,event,json(outgoing))
    self.bLastPublishOK=ok;self.sLastPublishError=not ok and tostring(err) or nil
    return ok,err
end
UI.Publish = function(self,oUI,snapshot)
    return self:_PublishEvent(oUI,'BKSnapshot',snapshot)
end
UI.PublishDelta = function(self,delta)
    return self:_PublishEvent(nil,'BKDelta',delta)
end
UI.Refresh = function(self)
    local runtime=self.Core and self.Core.Runtime
    if runtime and type(runtime.GetStatus)=='function' then self:Publish(self.oUI,runtime:GetStatus()) end
end
UI.Attach = function(self,oUI)
    if not oUI then return end
    if self.oUI==oUI and self.bAttached and self.boundView==oUI.view then self:Refresh();return end
    self.oUI=oUI
    self.bAttached=false
    local handles={}
    local bound,bindError=pcall(function()
    handles[#handles+1]=oUI:AddEventListener('BKReady',0,function() self:Refresh() end,self)
    handles[#handles+1]=oUI:AddEventListener('BKCommand',5,function(_,action,enclosure,species,male,female)
        local enabled=action=='set_rule_on' or action=='set_mode_apply'
        if action=='set_rule_on' or action=='set_rule_off' then action='set_rule' end
        if action=='set_mode_apply' or action=='set_mode_preview' then action='set_mode' end
        self.nCommandsReceived=(self.nCommandsReceived or 0)+1
        self.sLastCommand=tostring(action)..' / '..tostring(enclosure)..' / '..tostring(species)..' / enabled='..tostring(enabled)
        local runtime=self.Core.Runtime
        if not runtime or type(runtime.QueueUICommand)~='function' then self.sBridgeError='Runtime command queue unavailable';self:Refresh();return end
        local allowed={refresh=true,preview=true,set_rule=true,set_mode=true,stop_all=true,bulk_habitats_on=true,bulk_habitats_off=true,bulk_exhibits_on=true,bulk_exhibits_off=true}
        if not allowed[action] then self.sBridgeError='Unknown command: '..tostring(action);self:Refresh();return end
        local command={action=action,enclosureId=enclosure,species=species,mode=enabled and 'APPLY' or 'PREVIEW',rule={enabled=enabled==true,maleId=male,femaleId=female,storeOffspring=true,storeAtMaturity=true}}
        local ok,err=pcall(runtime.QueueUICommand,runtime,command)
        if not ok then self.sBridgeError='Command failed: '..tostring(err) elseif err==false then self.sBridgeError='Command queue rejected' else self.sBridgeError=nil end
        self:Refresh()
    end,self)
    handles[#handles+1]=oUI:AddEventListener('BKViewState',3,function(_,session,supported,source)
        self.nClientAcks=(self.nClientAcks or 0)+1;self.sClientSession=tostring(session)
        self.bClientSupported=supported==1;self.sClientSource=tostring(source)
    end,self)
    end)
    self.bAttached=bound
    if not bound then
        self.sBridgeError='Event binding failed: '..tostring(bindError)
        if type(oUI.RemoveEventListener)=='function' then for i=1,#handles do pcall(oUI.RemoveEventListener,oUI,handles[i]) end end
    else self.sBridgeError=nil;self.tListenerHandles=handles;self.boundView=oUI.view end
    self:Refresh()
end
UI.LoadOverlay = function(self)
    if self.bMapped then return end
    if not api.ui2 or type(api.ui2.LoadOverlay)~='function' then return end
    api.ui2.LoadOverlay('Autostorage','Autostorage/UI/AutostorageUI')
    while not api.ui2.IsOverlayLoaded('Autostorage') do coroutine.yield() end
    api.ui2.MapResources('Autostorage')
    self.bMapped=true
end
UI.UnloadOverlay = function(self)
    if not self.bMapped then return end
    api.ui2.UnmapResources('Autostorage')
    while not api.ui2.AreResourcesUnmapped('Autostorage') do coroutine.yield() end
    api.ui2.UnloadOverlay('Autostorage')
    self.bMapped=false;self.oUI=nil;self.bAttached=false;self.boundView=nil
end
UI.Init = function(self,Core)
    self.Core=Core;Core.UI=self
    Core:AddModulePatch('UI.Controllers.HUDUI',function(HUD)
        local original=HUD.Init
        if type(original)~='function' then return end
        HUD.Init=function(hud,settings,...)
            if self.bMapped and type(settings)=='table' then
                settings.sViewAddress='coui://UIGameface/BreederKeeperHUD.html'
                local ready=settings.fnOnReadyCallback
                settings.fnOnReadyCallback=function(...)
                    pcall(self.Attach,self,hud)
                    if ready then return ready(...) end
                end
                local unloaded=settings.fnOnUnloadedCallback
                settings.fnOnUnloadedCallback=function(...)
                    if self.oUI==hud then self.oUI=nil;self.bAttached=false;self.boundView=nil end
                    if unloaded then return unloaded(...) end
                end
            end
            return original(hud,settings,...)
        end
    end)
    Core:AddModulePatch('Game.GameScript',function(Game)
        local original=Game.OnPrepareToShutdown
        if type(original)~='function' then return end
        Game.OnPrepareToShutdown=function(...)
            local ok,err=pcall(self.UnloadOverlay,self)
            if not ok then Core:Trace('UI overlay unload failed: '..tostring(err)) end
            return original(...)
        end
    end)
end











