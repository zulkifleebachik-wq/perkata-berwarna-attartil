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
    const vv = await r.mget('vis:total', ...days.map(d => `vis:day:${d}`));
    const dp = r.pipeline(); for (const d of days) dp.hlen(`dv:${d}`); const devDay = await dp.exec();
    const wp = r.pipeline(); for (const d of days.slice(-7)) wp.hgetall(`dv:${d}`); const week = await wp.exec();
    const total = Number(vals[0]) || 0;
    const daily = days.map((d, i) => ({ date: d, views: Number(vals[1 + i]) || 0, visits: Number(vv[1 + i]) || 0, devices: Number(devDay[i]) || 0 }));
    // Engagement over the last 7 Singapore days (anonymous devices; one device = one browser).
    const per = {};
    week.forEach(h => { for (const [k, n] of Object.entries(h || {})) { const e = per[k] || (per[k] = { days: 0, visits: 0 }); e.days++; e.visits += Number(n) || 0; } });
    const devs = Object.values(per), dist = {};
    for (const e of devs) dist[e.days] = (dist[e.days] || 0) + 1;
    const wv = devs.reduce((s, e) => s + e.visits, 0);
    const engagement7 = { devices: devs.length, visits: wv, visitsPerDevice: devs.length ? +(wv / devs.length).toFixed(2) : 0,
      returnedOn2PlusDays: devs.filter(e => e.days >= 2).length, returnedOn3PlusDays: devs.filter(e => e.days >= 3).length,
      devicesByDaysActive: dist, note: 'devices = browsers that started a visit that day (anonymous ID). A person on two devices counts twice. Browsers that block storage count as a new device each day and about one visit per 30 min of reading.' };
    const pages = ROUTES.map((p, i) => ({ path: p, views: Number(vals[1 + days.length + i]) || 0 }))
      .sort((a, b) => b.views - a.views || a.path.localeCompare(b.path));
    // Per-surah total = the surah's first page + all its parts.
    const bySurah = {};
    for (const { path, views } of pages) {
      const s = path === '/' ? '(home)' : path.split('/')[1];
      bySurah[s] = (bySurah[s] || 0) + views;
    }
    const surahs = Object.entries(bySurah).map(([surah, views]) => ({ surah, views })).sort((a, b) => b.views - a.views);
    return res.status(200).json({ timezone: 'Asia/Singapore', today: sgDay(), total, visitsTotal: Number(vv[0]) || 0,
      visitRule: 'new visit after 30 minutes away', engagement7, last30: daily, surahs, pages });
  } catch (e) {
    console.error('stats', e && e.message);
    return res.status(503).json({ error: 'unavailable' });
  }
}
