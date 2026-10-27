"""Lua 5.3 boot harness with Frontier-style isolated module environments."""
from pathlib import Path
from lupa.lua53 import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)
main = Path(__file__).resolve().parents[1] / 'src/Autostorage/Main'
sources = lua.table()
for path in main.glob('*.lua'):
    sources[path.stem.lower()] = path.read_text(encoding='utf-8')
lua.globals().sources = sources
lua.execute(r'''
local globals=_G
local registered={}
api={debug={Trace=function() end},ui2={
 LoadOverlay=function() end,IsOverlayLoaded=function() return true end,
 MapResources=function() end,UnmapResources=function() end,
 AreResourcesUnmapped=function() return true end,UnloadOverlay=function() end},
 time={GetDeltaTimeUnscaled=function() return .02 end}}
-- module() replaces the caller chunk's _ENV with a table without global fallback.
function module(name)
 local key=string.lower(name)
 local scope=registered[key] or {}; registered[key]=scope; package.loaded[key]=scope
 local fn=debug.getinfo(2,'f').func
 for index=1,100 do
  local upvalue=debug.getupvalue(fn,index)
  if not upvalue then break end
  if upvalue=='_ENV' then
   local captured=scope
   local function holder() return captured end
   debug.upvaluejoin(fn,index,holder,1)
   break
  end
 end
 return scope
end
local function loadModule(name)
 local key=string.lower(name)
 if registered[key] then return registered[key] end
 local source=assert(sources[key],name)
 -- Each loaded chunk owns its _ENV; changing it cannot alter this harness.
 local fn=assert(load(source,name,'t',globals))
 local result=fn(name)
 return registered[key] or result
end
require=loadModule; tryrequire=loadModule
local entry=require('Database.AutostorageLuaDatabase')
local core=registered['breederkeeper.core']
assert(core and core.bBooted,'core boot')
assert(core.Runtime and core.UI,'both feature modules initialize')
assert(core.Runtime.policy==nil,'no park access during boot')
entry.AddContentToCall({})
assert(core.UI.bMapped,'overlay loads on startup coroutine')
local listeners={}
local view={AddEventListener=function(self,name,count,fn,arg)
 listeners[name]={fn=fn,arg=arg}
end,TriggerEventAtNextAdvance=function() end}
core.UI:Attach(view)
assert(listeners.BKReady and listeners.BKCommand,'UI event registration')
listeners.BKReady.fn(listeners.BKReady.arg)
local command=listeners.BKCommand
command.fn(command.arg,'refresh','','','','',false)
assert(#core.Runtime.queue==0,'commands rejected before supported park eligibility')
assert(core.UI.Encode({ok=true,items={1,2}}):find('true'),'JSON encoder under module scope')
local policy=require('BreederKeeper.Policy')
local s=policy.new({zooId='z',sessionId='s'})
local result=policy.evaluate(s,{zooId='z',sessionId='s',complete=true,animals={},capacity={}}, {},0)
assert(not result.error and #result.actions==0,'policy runs under isolated scope')
core.Runtime:_Reset({})
core.Runtime:Command({type='stop'})
core.Runtime:_Commands()
assert(core.Runtime.mode=='preview','runtime globals captured')
print('Lua 5.3 isolated module boot checks passed')
''')
