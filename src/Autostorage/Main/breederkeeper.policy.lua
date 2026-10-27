-- Independent, game-API-free policy. Identities are nonempty stable strings.
local global = _G
local type, ipairs, pairs = global.type, global.ipairs, global.pairs
local table, math = global.table, global.math
local tostring = global.tostring
local P = global.module and global.module(...) or {}
local function valid(v) return type(v) == 'string' and v ~= '' end
local function group(a, r)
    return a.kind == r.kind and a.enclosure == r.enclosure and a.species == r.species
end
function P.new(context)
    return {zooId=context.zooId, sessionId=context.sessionId, rules={}, pending={}}
end
function P.ack(state, id, success, now)
    local p = state.pending[id]
    if p then
        -- Accepted requests stay claimed until a later snapshot shows arrival.
        p.accepted = success == true
        p.retryAt = (now or 0) + (success and 30 or 5)
    end
end
function P.evaluate(state, snapshot, rules, now)
    now = now or 0
    local result = {actions={}, pauses={}}
    local function pause(r, why)
        result.pauses[#result.pauses+1] = {ruleId=r.id, reason=why}
    end
    if not valid(state.zooId) or not valid(state.sessionId) or
       snapshot.zooId ~= state.zooId or snapshot.sessionId ~= state.sessionId or
       snapshot.complete ~= true or type(snapshot.animals) ~= 'table' then
        result.error = 'incomplete snapshot or context mismatch'
        return result
    end
    local byId = {}
    for index, a in ipairs(snapshot.animals) do
        local field
        if type(a) ~= 'table' then
            result.error = 'animal row is not a table'; result.diagnostic={index=index}; return result
        elseif not valid(a.id) then field='id'
        elseif byId[a.id] then field='duplicate id'
        elseif not valid(a.species) then field='species'
        elseif not valid(a.enclosure) then field='enclosure'
        elseif a.kind ~= 'habitat' and a.kind ~= 'exhibit' then field='kind'
        else
            for _,name in ipairs({'juvenile','alive','inStorage','inTransit'}) do
                if type(a[name]) ~= 'boolean' then field=name; break end
            end
        end
        if field then
            result.error = 'invalid '..field..' for animal '..tostring(a.id or index)
            result.diagnostic={index=index,id=a.id,kind=a.kind,species=a.species,field=field}
            return result
        end
        byId[a.id] = a
    end
    local capacity = {}
    for _, kind in ipairs({'habitat','exhibit'}) do
        local n = snapshot.capacity and snapshot.capacity[kind]
        capacity[kind] = type(n) == 'number' and n >= 0 and math.floor(n) or 0
    end
    for id, pending in pairs(state.pending) do
        local a = byId[id]
        if not a or not a.alive or a.inStorage then state.pending[id] = nil
        elseif a.inTransit or pending.accepted or pending.retryAt > now then
            capacity[a.kind] = math.max(0, capacity[a.kind] - 1)
        end
    end
    local active, groupCounts = {}, {}
    for _, r in ipairs(rules or {}) do
        if r.enabled == true and valid(r.id) then
            local key = table.concat({r.kind or '',r.enclosure or '',r.species or ''}, '\31')
            groupCounts[key] = (groupCounts[key] or 0) + 1
        end
    end
    for _, r in ipairs(rules or {}) do
        if r.enabled == true and valid(r.id) then
            active[r.id] = true
            local signature = table.concat({r.kind or '',r.enclosure or '',r.species or ''}, '\31')
            local memory = state.rules[r.id]
            if not memory or memory.signature ~= signature then
                memory = {signature=signature, seen={}}
                state.rules[r.id] = memory
            end
            local candidates, allowed = {}, true
            if groupCounts[signature] > 1 then
                pause(r, 'conflicting rules for the same group'); allowed = false
            elseif not valid(r.enclosure) or not valid(r.species) or
               (r.kind ~= 'habitat' and r.kind ~= 'exhibit') then
                pause(r, 'invalid rule'); allowed = false
            end
            for _, a in ipairs(snapshot.animals) do
                if group(a,r) then
                    if a.alive and not a.inStorage and not a.inTransit then
                        local remove = false
                        if allowed then
                            -- Unknown adult on enable/reload is baseline, never a target.
                            if memory.seen[a.id] == 'juvenile' and not a.juvenile then
                                memory.seen[a.id] = 'matured'
                            end
                            remove = memory.seen[a.id] == 'matured'
                        end
                        if remove then candidates[#candidates+1] = a end
                    end
                    if not memory.seen[a.id] then
                        memory.seen[a.id] = a.juvenile and 'juvenile' or 'baseline'
                    end
                end
            end
            if allowed then
                table.sort(candidates,function(a,b) return a.id < b.id end)
                for _, a in ipairs(candidates) do
                    local p = state.pending[a.id]
                    if not p or (not p.accepted and p.retryAt <= now) then
                        if capacity[a.kind] > 0 then
                            capacity[a.kind] = capacity[a.kind] - 1
                            state.pending[a.id] = {retryAt=now+5,accepted=false}
                            result.actions[#result.actions+1] = {id=a.id,kind=a.kind,
                                enclosure=a.enclosure,species=a.species,ruleId=r.id}
                        else pause(r, 'storage capacity unavailable') end
                    end
                end
            end
        end
    end
    -- Disabling a rule discards its baseline. Re-enabling starts safely anew.
    for id in pairs(state.rules) do if not active[id] then state.rules[id] = nil end end
    return result
end
-- Targeted event path: observing one animal never prunes other rules or claims.
function P.observe(state, animal, rule, context)
    if type(context)~='table' or context.zooId~=state.zooId or context.sessionId~=state.sessionId then
        return false,'context mismatch'
    end
    if type(rule)~='table' or rule.enabled~=true or not valid(rule.id) or
        type(animal)~='table' or not valid(animal.id) or not group(animal,rule) then
        return false,'no matching enabled rule'
    end
    for _,field in ipairs({'juvenile','alive','inStorage','inTransit'}) do
        if type(animal[field])~='boolean' then return false,'invalid '..field end
    end
    local signature=table.concat({rule.kind,rule.enclosure,rule.species},'\31')
    local memory=state.rules[rule.id]
    if not memory or memory.signature~=signature then
        memory={signature=signature,seen={}}; state.rules[rule.id]=memory
    end
    local previous=memory.seen[animal.id]
    if previous==nil then memory.seen[animal.id]=animal.juvenile and 'juvenile' or 'baseline'
    elseif previous=='juvenile' and not animal.juvenile then memory.seen[animal.id]='matured' end
    return memory.seen[animal.id]=='matured' and animal.alive and not animal.juvenile and
        not animal.inStorage and not animal.inTransit, memory.seen[animal.id]
end
return P
