// Original shared-registry loader. Each installed peer supplies its own scripts.
const imported = new Set();
let attempts = 0;
let complete = false;
let timer;

function receive(payload) {
    let message;
    try { message = typeof payload === 'string' ? JSON.parse(payload) : payload; }
    catch (_) { return; }
    if (!message || !Array.isArray(message.scripts)) return;
    for (const path of message.scripts) {
        if (typeof path !== 'string' || !path.startsWith('/') || path.startsWith('//') || imported.has(path)) continue;
        imported.add(path);
        import(path).catch(() => { });
    }
    if (message.pending !== true) {
        complete = true;
        window.clearInterval(timer);
    }
}

function request() {
    if (complete || attempts >= 30) { window.clearInterval(timer); return; }
    attempts++;
    if (window.engine && typeof window.engine.trigger === 'function') window.engine.trigger('BKHUDRequest');
}

if (window.engine && typeof window.engine.on === 'function') {
    window.engine.on('BKHUDScripts', receive);
    timer = window.setInterval(request, 1000);
    request();
}
