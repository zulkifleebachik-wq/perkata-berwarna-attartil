// POST /api/hit  {path, v?, did?}
//  - page view: once per visitor per page per Singapore day;
//  - visit (v=1): a new sitting after 30 min away, at most one per device per 30 min;
//  - did: anonymous random device ID from the browser, stored only as an HMAC (engagement figures).
import { redis, sgDay, isBot, visitorId, ipId, sameOrigin, deviceKey } from './_lib.js';
import { ROUTES } from './_routes.js';

const ROUTE_SET = new Set(ROUTES);
const RATE_MAX = 300;         // hits per IP per minute (a full class on one mosque/school Wi-Fi still fits)
const IP_DAY_MAX = 3000;      // counted views per IP per Singapore day
const DAY_TTL = 400 * 86400;  // daily totals kept ~13 months
const DEV_TTL = 40 * 86400;   // per-device daily visit counts kept 40 days (for the 7- and 30-day figures)

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') { res.setHeader('Allow', 'POST'); return res.status(405).json({ ok: false }); }
  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch { body = null; } }
  const path = body && typeof body.path === 'string' ? body.path : '';
  if (!ROUTE_SET.has(path)) return res.status(400).json({ ok: false, error: 'unknown path' });
  if (!sameOrigin(req)) return res.status(403).json({ ok: false, counted: false });
  if (isBot(String(req.headers['user-agent'] || ''))) return res.status(202).json({ ok: true, counted: false });

  try {
    const r = redis();
    const day = sgDay();
    const vid = visitorId(req, day), iid = ipId(req, day);
    const minute = Math.floor(Date.now() / 60000);
    const rl = `rl:${iid}:${minute}`;
    const [n] = await r.pipeline().incr(rl).expire(rl, 90).exec();
    if (n > RATE_MAX) return res.status(429).json({ ok: false, counted: false });
    const dev = deviceKey(body.did, vid);
    // Server-side checks (back up the browser's flags): page once per day, visit once per 30 min per device.
    const seenKey = `seen:${day}:${vid}:${path}`;
    const visKey = `vs:${dev}`;
    const p1 = r.pipeline().set(seenKey, 1, { nx: true, ex: 2 * 86400 });
    if (body.v === 1) p1.set(visKey, 1, { nx: true, ex: 30 * 60 });
    const [pvFresh, visFresh] = await p1.exec();
    if (!pvFresh && !visFresh) return res.status(200).json({ ok: true, counted: false, visit: false });
    const ipDay = `ipd:${day}:${iid}`;
    const [m] = await r.pipeline().incr(ipDay).expire(ipDay, 2 * 86400).exec();
    if (m > IP_DAY_MAX) {
      const undo = r.pipeline(); if (pvFresh) undo.del(seenKey); if (visFresh) undo.del(visKey); await undo.exec();
      return res.status(429).json({ ok: false, counted: false });
    }
    const w = r.pipeline();
    if (pvFresh) w.incr('pv:total').incr(`pv:day:${day}`).expire(`pv:day:${day}`, DAY_TTL).incr(`pv:path:${path}`);
    if (visFresh) w.incr('vis:total').incr(`vis:day:${day}`).expire(`vis:day:${day}`, DAY_TTL)
      .hincrby(`dv:${day}`, dev, 1).expire(`dv:${day}`, DEV_TTL);
    await w.exec();
    return res.status(200).json({ ok: true, counted: !!pvFresh, visit: !!visFresh });
  } catch (e) {
    console.error('hit', e && e.message);
    return res.status(503).json({ ok: false });
  }
}
