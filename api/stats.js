// GET /api/stats?key=STATS_KEY — private figures for UZB: per-page totals and the last 30 Singapore days.
import { redis, sgDay, keyOk } from './_lib.js';
import { ROUTES } from './_routes.js';

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Robots-Tag', 'noindex');
  const key = (req.query && req.query.key) || req.headers['x-stats-key'];
  if (!keyOk(Array.isArray(key) ? key[0] : key)) return res.status(401).json({ error: 'unauthorised' });
  try {
    const r = redis();
    const days = [];
    for (let i = 29; i >= 0; i--) days.push(sgDay(Date.now() - i * 86400e3));
    const vals = await r.mget('pv:total', ...days.map(d => `pv:day:${d}`), ...ROUTES.map(p => `pv:path:${p}`));
    const total = Number(vals[0]) || 0;
    const daily = days.map((d, i) => ({ date: d, views: Number(vals[1 + i]) || 0 }));
    const pages = ROUTES.map((p, i) => ({ path: p, views: Number(vals[1 + days.length + i]) || 0 }))
      .sort((a, b) => b.views - a.views || a.path.localeCompare(b.path));
    // Per-surah total = the surah's first page + all its parts.
    const bySurah = {};
    for (const { path, views } of pages) {
      const s = path === '/' ? '(home)' : path.split('/')[1];
      bySurah[s] = (bySurah[s] || 0) + views;
    }
    const surahs = Object.entries(bySurah).map(([surah, views]) => ({ surah, views })).sort((a, b) => b.views - a.views);
    return res.status(200).json({ timezone: 'Asia/Singapore', today: sgDay(), total, last30: daily, surahs, pages });
  } catch (e) {
    console.error('stats', e && e.message);
    return res.status(503).json({ error: 'unavailable' });
  }
}
