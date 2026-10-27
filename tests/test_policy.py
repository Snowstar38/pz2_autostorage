"""Behavior checks via lupa, without loading the game or game files."""
from pathlib import Path
from lupa import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)
policy = Path(__file__).resolve().parents[1] / 'src/Autostorage/Main/breederkeeper.policy.lua'
lua.globals().P = lua.execute(policy.read_text(encoding='utf-8'))
lua.execute(r'''
local function animal(id, juvenile, kind)
    return {id=id, juvenile=juvenile,kind=kind or 'habitat',species='s',
        enclosure='h',alive=true,inStorage=false,inTransit=false}
end
local function snapshot(animals)
    return {zooId='z',sessionId='session',complete=true,animals=animals,
        capacity={habitat=5,exhibit=5}}
end
local function state() return P.new({zooId='z',sessionId='session'}) end
local habitat={id='h',kind='habitat',species='s',enclosure='h',enabled=true}
local s=state()
local a,b=animal('parent',false),animal('child',true)
assert(#P.evaluate(s,snapshot({a,b}),{habitat},0).actions==0)
b.juvenile=false
local r=P.evaluate(s,snapshot({a,b}),{habitat},1)
assert(#r.actions==1 and r.actions[1].id=='child','maturation must preserve baseline parent')
assert(#P.evaluate(s,snapshot({a,b}),{habitat},2).actions==0,'pending duplicate')
P.ack(s,'child',false,2)
assert(#P.evaluate(s,snapshot({a,b}),{habitat},6).actions==0,'retry backoff')
assert(#P.evaluate(s,snapshot({a,b}),{habitat},7).actions==1,'failed request retries')
P.ack(s,'child',true,7)
assert(#P.evaluate(s,snapshot({a,b}),{habitat},100).actions==0,'accepted request must not duplicate')
assert(#P.evaluate(state(),snapshot({a,b}),{habitat},0).actions==0,'reload must baseline adults')
P.evaluate(s,snapshot({a,b}),{},101)
assert(#P.evaluate(s,snapshot({a,b}),{habitat},102).actions==0,'reenable must baseline adults')
local x,y,z=animal('male',false,'exhibit'),animal('female',false,'exhibit'),animal('extra',true,'exhibit')
local rule={id='e',kind='exhibit',species='s',enclosure='h',enabled=true}
local exhibits=state()
assert(#P.evaluate(exhibits,snapshot({x,y,z}),{rule},0).actions==0,'exhibits baseline adults and keep juveniles')
z.juvenile=false
r=P.evaluate(exhibits,snapshot({x,y,z}),{rule},1)
assert(#r.actions==1 and r.actions[1].id=='extra','exhibit maturation needs no breeder pair')
assert(#P.evaluate(state(),snapshot({x,z}),{rule},0).actions==0,'existing exhibit adults protected')
local snap=snapshot({x,y,z}); snap.capacity.exhibit=0
assert(#P.evaluate(state(),snap,{rule},0).actions==0,'full storage')
snap=snapshot({x,y,z}); snap.sessionId='other'
assert(P.evaluate(state(),snap,{rule},0).error,'wrong session')
snap=snapshot({x,y,z}); snap.complete=false
assert(P.evaluate(state(),snap,{rule},0).error,'partial snapshot')
snap=snapshot({x,y,z}); z.id='male'
assert(P.evaluate(state(),snap,{rule},0).error,'duplicate identity')
z.id='extra'; z.alive=nil
local invalid=P.evaluate(state(),snapshot({x,y,z}),{rule},0)
assert(invalid.diagnostic.field=='alive' and invalid.diagnostic.id=='extra','field diagnostic')
print('Policy behavior checks passed')
''')
