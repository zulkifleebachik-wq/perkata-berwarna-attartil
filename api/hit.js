// POST /api/hit  {path}  — counts one view of a page (once per visitor per page per Singapore day).
import { redis, sgDay, isBot, visitorId, ipId, sameOrigin } from './_lib.js';
import { ROUTES } from './_routes.js';

const ROUTE_SET = new Set(ROUTES);
const RATE_MAX = 60;          // hits per IP per minute (all browsers on that IP together)
const IP_DAY_MAX = 600;       // counted views per IP per Singapore day (a whole school/office behind one IP still fits)
const DAY_TTL = 400 * 86400;  // daily totals kept ~13 months

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
    // Server-side once-per-day check (backs up the browser's localStorage flag).
    const fresh = await r.set(`seen:${day}:${vid}:${path}`, 1, { nx: true, ex: 2 * 86400 });
    if (!fresh) return res.status(200).json({ ok: true, counted: false });
    const ipDay = `ipd:${day}:${iid}`;
    const [m] = await r.pipeline().incr(ipDay).expire(ipDay, 2 * 86400).exec();
    if (m > IP_DAY_MAX) return res.status(429).json({ ok: false, counted: false });
    await r.pipeline()
      .incr('pv:total')
      .incr(`pv:day:${day}`).expire(`pv:day:${day}`, DAY_TTL)
      .incr(`pv:path:${path}`)
      .exec();
    return res.status(200).json({ ok: true, counted: true });
  } catch (e) {
    console.error('hit', e && e.message);
    return res.status(503).json({ ok: false });
  }
}
