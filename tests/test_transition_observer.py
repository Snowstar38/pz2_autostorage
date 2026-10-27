"""Global lifecycle listener observes every transition without changing gameplay."""
from runtime_fixture import runtime

lua = runtime()
lua.execute(r'''
local globals,registered={},0
api.messaging.MsgType_WorldTransitionMessage=10
function api.messaging.RegisterGlobalReceiver(kind,fn) globals[kind]=fn; registered=registered+1 end
local activeWorld,reads='sandbox',0
api.world={GetActive=function() reads=reads+1; return activeWorld end,
 GetWorldAPIs=function() error('observer must not read park APIs') end}
local core={UI=R.Core.UI,AddModulePatch=function() end}
R:Init(core)
assert(globals[10] and R:GetStatus().diagnostics.transitionListener and registered==1)
local observer=globals[10]
local managerBefore,modeBefore,supportedBefore=R.manager,R.mode,R.supported
counts={}
observer({{Event='started'},{Event='fadeincompleted'},{Event='fadeoutstarted'},{Event='completed'}})
assert(reads==4 and next(counts)==nil,'only safe global active-world metadata read')
assert(R.manager==managerBefore and R.mode==modeBefore and R.supported==supportedBefore,'listener cannot change runtime lifecycle')
assert(R.transitionState.counts.completed==1 and R.transitionState.activeWorld=='sandbox')
local nextManager,nextEnvironment={tWorldAPIs=apis},{}
R:_Reset(nextManager,nextEnvironment)
assert(globals[10]==observer,'park reset cannot detach global observer')
R:_CloseManager(nextManager)
activeWorld='mainmenu'
for i=1,100 do observer({{Event='completed'}}) end
assert(globals[10]==observer and R.transitionState.counts.completed==101)
assert(R.manager==nil and not R.supported and #R.hookDiagnostics.history==32,'post-close events stay read-only and bounded')
R:Init(core)
assert(registered==1,'observer registered once per runtime process')
print('Global transition observer passed: exact Event payload, independent park lifetime, read-only metadata, bounded history')
''')
