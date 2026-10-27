local global = _G
local api = global.api
local Entry = module(...)
local ok, err = global.pcall(function()
    global.require("BreederKeeper.Core"):Boot()
end)
if not ok then global.pcall(function() api.debug.Trace("[Autostorage] " .. global.tostring(err)) end) end
Entry.AddContentToCall = function(content)
    local UI = global.require("BreederKeeper.UI")
    if UI.LoadOverlay then UI:LoadOverlay() end
end
