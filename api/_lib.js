// Visit counter: shared helpers (UZB, Nov 2026). Files starting with "_" are not served as functions.
import { Redis } from '@upstash/redis';
import { createHmac, timingSafeEqual } from 'node:crypto';

// The Vercel Marketplace (Upstash) integration creates either UPSTASH_REDIS_REST_* or KV_REST_API_*.
// Redis.fromEnv() reads both; this check only gives a clear error when neither is set.
export function redis() {
  const url = process.env.UPSTASH_REDIS_REST_URL || process.env.KV_REST_API_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN;
  if (!url || !token) throw new Error('Redis env vars missing (UPSTASH_REDIS_REST_URL/_TOKEN or KV_REST_API_URL/_TOKEN)');
  return Redis.fromEnv();
}

// Calendar day in Singapore (UTC+8, no daylight saving).
export function sgDay(ms = Date.now()) {
  return new Date(ms + 8 * 3600e3).toISOString().slice(0, 10);
}

export function isPublic() {
  return !['false', '0', 'no', 'off'].includes(String(process.env.COUNTER_PUBLIC ?? 'true').trim().toLowerCase());
}

// Link-preview fetchers and crawlers (WhatsApp, Facebook, Telegram …) are not counted.
// In-app browsers of Telegram/LinkedIn/Slack/Discord are real readers; only their fetchers (…bot, slack-imgproxy) are dropped.
const BOT = /bot|crawl|spider|slurp|preview|inspectiontool|whatsapp|facebookexternalhit|facebot|meta-external|slack-imgproxy|skypeuripreview|embedly|pinterest|vkshare|headless|lighthouse|pagespeed|gtmetrix|curl|wget|python|node-fetch|axios|go-http|java\/|okhttp|libwww|httpclient|monitor|uptime|pingdom|scan/i;
export function isBot(ua) {
  return !ua || BOT.test(ua);
}

// Anonymous id for one visitor on one day: HMAC(ip + UA) with a key that changes daily.
// The raw IP and User-Agent are never stored; the id itself expires after 2 days.
function clientIp(req) {
  const fwd = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim();
  return String(req.headers['x-real-ip'] || fwd || '');
}
function dailyKey(day) {
  const secret = process.env.STATS_KEY || process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN || '';
  return createHmac('sha256', secret).update('salt:' + day).digest();
}
export function visitorId(req, day) {
  const ua = String(req.headers['user-agent'] || '');
  return createHmac('sha256', dailyKey(day)).update(clientIp(req) + '\n' + ua).digest('base64url').slice(0, 22);
}
// Same daily key, IP only: used for the rate limit, so changing the User-Agent does not get round it.
// IPv6 clients are bucketed by their /64 (one home or phone network), so rotating addresses inside it does not help.
export function ipBucket(ip) {
  if (!ip.includes(':') || /^::ffff:\d+\.\d+\.\d+\.\d+$/i.test(ip)) return ip.replace(/^::ffff:/i, '');
  const [a, b = ''] = ip.toLowerCase().split('%')[0].split('::');
  const L = a ? a.split(':') : [], R = b ? b.split(':') : [];
  const full = ip.includes('::') ? [...L, ...Array(Math.max(0, 8 - L.length - R.length)).fill('0'), ...R] : L;
  return full.slice(0, 4).map(h => (parseInt(h, 16) || 0).toString(16)).join(':') + '::/64';
}
export function ipId(req, day) {
  return createHmac('sha256', dailyKey(day)).update('ip\n' + ipBucket(clientIp(req))).digest('base64url').slice(0, 22);
}

// Only count requests sent by the site's own pages (browsers always send Origin on a POST fetch).
export function sameOrigin(req) {
  const o = String(req.headers['origin'] || '');
  const h = String(req.headers['x-forwarded-host'] || req.headers['host'] || '');
  if (!o || !h) return false;
  try { return new URL(o).host === h; } catch { return false; }
}

// Anonymous device key for UZB's engagement figures: HMAC of the browser's random ID (fixed key, so a device
// can be recognised across days). Without a usable ID, falls back to the daily IP+UA id (that day only).
export function deviceKey(did, vid) {
  if (typeof did === 'string' && /^[A-Za-z0-9_-]{22}$/.test(did)) {
    const secret = process.env.STATS_KEY || process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN || '';
    return 'd' + createHmac('sha256', secret).update('dev\n' + did).digest('base64url').slice(0, 16);
  }
  // Storage blocked: a separate daily HMAC (not a prefix of the page-view id), so visits cannot be joined to pages.
  const secret = process.env.STATS_KEY || process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN || '';
  return 'v' + createHmac('sha256', secret).update('fallback\n' + vid).digest('base64url').slice(0, 16);
}

export function keyOk(given) {
  const want = process.env.STATS_KEY || '';
  if (want.length < 24 || typeof given !== 'string') return false;
  const a = Buffer.from(given), b = Buffer.from(want);
  return a.length === b.length && timingSafeEqual(a, b);
}
