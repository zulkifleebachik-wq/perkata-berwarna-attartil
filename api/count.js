// GET /api/count — {total, today} for the home-page badge. Edge-cached 20 s to keep Redis calls low.
import { redis, sgDay, isPublic } from './_lib.js';

export default async function handler(req, res) {
  if (req.method !== 'GET' && req.method !== 'HEAD') { res.setHeader('Allow', 'GET'); return res.status(405).json({}); }
  res.setHeader('Cache-Control', 'public, max-age=0, s-maxage=20, stale-while-revalidate=40');
  if (!isPublic()) return res.status(200).json({ public: false });
  try {
    const [total, today] = await redis().mget('pv:total', `pv:day:${sgDay()}`);
    return res.status(200).json({ public: true, total: Number(total) || 0, today: Number(today) || 0 });
  } catch (e) {
    console.error('count', e && e.message);
    res.setHeader('Cache-Control', 'no-store');
    return res.status(503).json({ public: false });
  }
}
