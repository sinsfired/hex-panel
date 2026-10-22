// Hex panel controller: serves the control page and relays colors to a WLED device.
// Run: node server.js   then open http://localhost:8080
// No npm packages needed.
const http = require('http');
const dgram = require('dgram');
const fs = require('fs');
const path = require('path');

const PORT = Number(process.env.PORT) || 8080;
const CONFIG_FILE = path.join(__dirname, 'config.json');
const TILES = 47;
const WLED_UDP_PORT = 21324;

const DEFAULTS = {
  wledIp: '',          // empty = dry run (nothing is sent, packets are logged)
  ledsPerHex: 1,       // LEDs inside each hex
  ledOffset: 0,        // LEDs before the first hex on the strip
  map: null,           // map[tile-1] = chain position (0-based); null = tile # order
  groups: {}           // saved selections: { name: [tile numbers] }
};

function loadConfig() {
  try { return { ...DEFAULTS, ...JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8')) }; }
  catch { return { ...DEFAULTS }; }
}
let config = loadConfig();
const saveConfig = () => fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));

const udp = dgram.createSocket('udp4');
const chainPos = tile => (config.map && config.map[tile - 1] != null) ? config.map[tile - 1] : tile - 1;
const hexToRgb = h => [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) || 0);

// colors: array of 47 "RRGGBB" strings, index = tile # - 1
// raw: index = chain position instead (used while mapping tiles)
function toStrip(colors, raw) {
  const n = config.ledOffset + TILES * config.ledsPerHex;
  const strip = Array(n).fill('000000');
  colors.forEach((c, i) => {
    const start = config.ledOffset + (raw ? i : chainPos(i + 1)) * config.ledsPerHex;
    for (let k = 0; k < config.ledsPerHex; k++) strip[start + k] = c || '000000';
  });
  return strip;
}

// Live frames go over UDP (WLED realtime DNRGB), fast enough for animation.
// WLED drops back to its normal state 2 s after the last frame.
function sendUdp(colors, bri = 255) {
  const strip = toStrip(colors);
  if (!config.wledIp) return log('udp', strip.length + ' LEDs (dry run)');
  for (let start = 0; start < strip.length; start += 489) {
    const chunk = strip.slice(start, start + 489);
    const buf = Buffer.alloc(4 + chunk.length * 3);
    buf[0] = 4; buf[1] = 2; buf.writeUInt16BE(start, 2);
    chunk.forEach((h, i) => hexToRgb(h).forEach((v, j) => { buf[4 + i * 3 + j] = Math.round(v * bri / 255); }));
    udp.send(buf, WLED_UDP_PORT, config.wledIp);
  }
}

// Static colors go over the JSON API so they stay after the page closes.
async function sendJson(colors, bri = 255, raw = false) {
  const strip = toStrip(colors, raw);
  // Segment LED indexes are relative to the segment start; collapse runs into [start, stop, color]
  const runs = (from, to) => {
    const i = [];
    for (let s = from; s < to;) {
      let e = s; while (e < to && strip[e] === strip[s]) e++;
      i.push(s - from, e - from, strip[s]); s = e;
    }
    return i;
  };
  if (!config.wledIp) { log('json', JSON.stringify(runs(0, strip.length)).slice(0, 160) + '... (dry run)'); return { dryRun: true }; }
  // Overlapping segments draw on top of each other, so every segment gets its own slice of the colors
  const state = await (await fetch(`http://${config.wledIp}/json/state`, { signal: AbortSignal.timeout(3000) })).json();
  const segs = (state.seg || []).filter(s => s.stop > s.start);
  const seg = (segs.length ? segs : [{ id: 0, start: 0, stop: strip.length }]).map(s => ({
    id: s.id, on: true, bri: 255, fx: 0, i: runs(s.start, Math.min(s.stop, strip.length))
  }));
  const body = { on: true, bri, live: false, seg };
  const r = await fetch(`http://${config.wledIp}/json/state`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    signal: AbortSignal.timeout(3000)
  });
  if (!r.ok) throw new Error('WLED answered ' + r.status);
  return { ok: true };
}

let lastLog = 0;
function log(kind, msg) { if (kind !== 'udp' || Date.now() - lastLog > 2000) { console.log(`[${kind}] ${msg}`); lastLog = Date.now(); } }

function readBody(req) {
  return new Promise((res, rej) => {
    let d = ''; req.on('data', c => { d += c; if (d.length > 1e6) req.destroy(); });
    req.on('end', () => { try { res(d ? JSON.parse(d) : {}); } catch (e) { rej(e); } });
  });
}
const send = (res, code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); };

http.createServer(async (req, res) => {
  try {
    if (req.method === 'GET' && (req.url === '/' || req.url === '/index.html')) {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      return fs.createReadStream(path.join(__dirname, 'index.html')).pipe(res);
    }
    if (req.url === '/api/config' && req.method === 'GET') return send(res, 200, config);
    if (req.url === '/api/config' && req.method === 'POST') {
      const b = await readBody(req);
      for (const k of Object.keys(DEFAULTS)) if (k in b) config[k] = b[k];
      config.ledsPerHex = Math.max(1, Number(config.ledsPerHex) || 1);
      config.ledOffset = Math.max(0, Number(config.ledOffset) || 0);
      saveConfig(); return send(res, 200, config);
    }
    if (req.url === '/api/frame' && req.method === 'POST') {
      const b = await readBody(req); sendUdp(b.colors, b.bri); return send(res, 200, { ok: true });
    }
    if (req.url === '/api/apply' && req.method === 'POST') {
      const b = await readBody(req); return send(res, 200, await sendJson(b.colors, b.bri, b.raw));
    }
    if (req.url === '/api/ping' && req.method === 'GET') {
      if (!config.wledIp) return send(res, 200, { dryRun: true });
      const r = await fetch(`http://${config.wledIp}/json/info`, { signal: AbortSignal.timeout(2500) });
      const info = await r.json();
      return send(res, 200, { ok: true, name: info.name, leds: info.leds && info.leds.count, ver: info.ver });
    }
    send(res, 404, { error: 'Not found' });
  } catch (e) { send(res, 502, { error: e.message }); }
}).listen(PORT, () => console.log(`Hex controller on http://localhost:${PORT}  (WLED: ${config.wledIp || 'not set, dry run'})`));

