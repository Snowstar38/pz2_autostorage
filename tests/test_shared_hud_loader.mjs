// Exercise the authored module in a VM with explicit dynamic-import instrumentation.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('../src/Autostorage/UI/UIGameface/autostorage.hudmods.js',import.meta.url),'utf8');
const listeners={},imports=[],requests=[];let tick,cleared=0;
const window={engine:{on:(name,fn)=>listeners[name]=fn,trigger:name=>requests.push(name)},setInterval:fn=>(tick=fn,1),clearInterval:()=>cleared++};
// Replace just the import expression so tests run on ordinary Node without VM module flags.
const instrumented=source.replace('import(path)', 'loadPeer(path)');
assert.notEqual(instrumented,source);
vm.runInNewContext(instrumented,{window,Set,JSON,loadPeer:path=>{imports.push(path);return path==='/bad.js'?Promise.reject(new Error('missing')):Promise.resolve();}});
assert.deepEqual(requests,['BKHUDRequest']);
const receive=listeners.BKHUDScripts;
receive('invalid json');receive('{}');tick();assert.equal(requests.length,2);
receive(JSON.stringify({scripts:['/good.js','/good.js','https://outside','//outside',12,'/bad.js'],pending:true}));
await Promise.resolve();assert.deepEqual(imports,['/good.js','/bad.js']);
tick();assert.equal(requests.length,3,'pending mapping keeps handshake polling');
receive({scripts:['/good.js','/late.js'],pending:false});assert.deepEqual(imports,['/good.js','/bad.js','/late.js']);
assert.ok(cleared);tick();assert.equal(requests.length,3,'complete response stops requests');
let limitTick;let count=0;
vm.runInNewContext(instrumented,{window:{engine:{on:()=>{},trigger:()=>count++},setInterval:fn=>(limitTick=fn,1),clearInterval:()=>{}},Set,JSON,loadPeer:()=>Promise.resolve()});
for(let i=0;i<50;i++) limitTick();assert.equal(count,30,'missing response has bounded retries');
vm.runInNewContext(instrumented,{window:{},Set,JSON,loadPeer:()=>Promise.resolve()});
console.log('Shared HUD loader: handshake, late scripts, deduplication, invalid paths/payloads, rejected import and bounded polling passed');
