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
  return String(process.env.COUNTER_PUBLIC ?? 'true').trim().toLowerCase() !== 'false';
}

// Link-preview fetchers and crawlers (WhatsApp, Facebook, Telegram …) are not counted.
const BOT = /bot|crawl|spider|slurp|preview|whatsapp|facebookexternalhit|facebot|meta-external|telegram|discord|slack|linkedin|skype|embedly|pinterest|vkshare|headless|lighthouse|pagespeed|gtmetrix|curl|wget|python|node-fetch|axios|go-http|java\/|okhttp|libwww|httpclient|monitor|uptime|pingdom|scan/i;
export function isBot(ua) {
  return !ua || BOT.test(ua);
}

// Anonymous id for one visitor on one day: HMAC(ip + UA) with a key that changes daily.
// The raw IP and User-Agent are never stored; the id itself expires after 2 days.
export function visitorId(req, day) {
  const fwd = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim();
  const ip = String(req.headers['x-real-ip'] || fwd || '');
  const ua = String(req.headers['user-agent'] || '');
  const secret = process.env.STATS_KEY || process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN || '';
  const daily = createHmac('sha256', secret).update('salt:' + day).digest();
  return createHmac('sha256', daily).update(ip + '\n' + ua).digest('base64url').slice(0, 22);
}

export function keyOk(given) {
  const want = process.env.STATS_KEY || '';
  if (want.length < 24 || typeof given !== 'string') return false;
  const a = Buffer.from(given), b = Buffer.from(want);
  return a.length === b.length && timingSafeEqual(a, b);
}
