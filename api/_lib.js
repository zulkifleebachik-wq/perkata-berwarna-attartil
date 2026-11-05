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
export function ipId(req, day) {
  return createHmac('sha256', dailyKey(day)).update('ip\n' + clientIp(req)).digest('base64url').slice(0, 22);
}

// Only count requests sent by the site's own pages (browsers always send Origin on a POST fetch).
export function sameOrigin(req) {
  const o = String(req.headers['origin'] || '');
  const h = String(req.headers['x-forwarded-host'] || req.headers['host'] || '');
  if (!o || !h) return false;
  try { return new URL(o).host === h; } catch { return false; }
}

export function keyOk(given) {
  const want = process.env.STATS_KEY || '';
  if (want.length < 24 || typeof given !== 'string') return false;
  const a = Buffer.from(given), b = Buffer.from(want);
  return a.length === b.length && timingSafeEqual(a, b);
}
