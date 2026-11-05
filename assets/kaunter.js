/* Kaunter lawatan / visit counter — E-Quran Perkata Berwarna (UZB, Nov 2026).
   Extra only: with JavaScript off nothing here runs and the badge stays hidden.
   - Page view: once per page per Singapore day (localStorage flag + server check). Refresh never counts.
   - Visit: a new sitting after 30 minutes away (UZB, 5 Nov 2026). Moving between pages in one sitting = one visit.
   - Device: an anonymous random ID kept in this browser (no name, no IP), so UZB's private stats can show
     how often devices come back. Nothing here identifies a person. */
(function () {
  if (!/^https?:$/.test(location.protocol) || !window.fetch) return;
  var path = location.pathname.replace(/index\.html?$/, '');
  if (path.slice(-1) !== '/') path += '/';
  var now = Date.now(), GAP = 30 * 60e3;
  var day = new Date(now + 288e5).toISOString().slice(0, 10); // Asia/Singapore (UTC+8)
  var K = 'pb-kv', seen = {}, st = null, did = '', last = 0;
  function get(k) { try { return localStorage.getItem(k); } catch (x) { return null; } }
  function put(k, v) { try { localStorage.setItem(k, v); } catch (x) {} }
  try { st = JSON.parse(get(K) || 'null'); } catch (x) {}
  if (st && st.d === day && st.p && typeof st.p === 'object' && !Array.isArray(st.p)) seen = st.p;
  did = get('pb-did') || '';
  if (!/^[A-Za-z0-9_-]{22}$/.test(did)) {
    did = '';
    try {
      var a = new Uint8Array(16); crypto.getRandomValues(a);
      did = btoa(String.fromCharCode.apply(null, a)).replace(/\+/g, '-').replace(/\//g, '_').slice(0, 22);
      put('pb-did', did);
      if (get('pb-did') !== did) did = ''; // storage blocked: the server falls back to its own daily check
    } catch (x) { did = ''; }
  }
  if (did) { var note = document.getElementById('kv-note'); if (note) note.hidden = false; } // privacy note, only when an ID is kept
  last = Number(get('pb-last')) || 0;
  var newVisit = !(last > 0 && now - last < GAP && last <= now);
  function touch() { put('pb-last', String(Date.now())); }
  touch();
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') touch(); });
  window.addEventListener('pagehide', touch);
  function badge() {
    var b = document.getElementById('kv');
    if (!b) return;
    fetch('/api/count', { credentials: 'omit' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (!j || !j.public || typeof j.total !== 'number') { b.hidden = true; return; }
      var f = function (n) { return Number(n).toLocaleString('en-US'); };
      b.querySelector('[data-k=total]').textContent = f(j.total);
      b.querySelector('[data-k=today]').textContent = f(j.today);
      b.hidden = false;
    }).catch(function () {});
  }
  function send(again, visit) {
    var body = { path: path };
    if (visit) body.v = 1;
    if (did) body.did = did;
    return fetch('/api/hit', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), credentials: 'omit', keepalive: true })
      .then(function (r) {
        if (r.ok) { seen[path] = 1; put(K, JSON.stringify({ d: day, p: seen })); }
        else if (r.status === 429 && again) setTimeout(function () { send(false, visit); }, 70000); // busy shared Wi-Fi: try once more
      }).catch(function () {});
  }
  var hit = (seen[path] && !newVisit) ? Promise.resolve() : send(true, newVisit);
  if (!document.getElementById('kv')) return;
  hit.then(badge);
  setInterval(function () { if (document.visibilityState === 'visible') { badge(); touch(); } }, 60000);
})();
