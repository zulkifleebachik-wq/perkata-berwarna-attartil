/* Kaunter lawatan / visit counter — E-Quran Perkata Berwarna (UZB, Nov 2026).
   Extra only: with JavaScript off nothing here runs and the badge stays hidden.
   One count per page per Singapore day (localStorage flag + server check). */
(function () {
  if (!/^https?:$/.test(location.protocol) || !window.fetch) return;
  var path = location.pathname.replace(/index\.html?$/, '');
  if (path.slice(-1) !== '/') path += '/';
  var day = new Date(Date.now() + 288e5).toISOString().slice(0, 10); // Asia/Singapore (UTC+8)
  var K = 'pb-kv', seen = {}, st = null;
  try { st = JSON.parse(localStorage.getItem(K) || 'null'); } catch (x) {}
  if (st && st.d === day && st.p && typeof st.p === 'object' && !Array.isArray(st.p)) seen = st.p;
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
  function send(again) {
    return fetch('/api/hit', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: path }), credentials: 'omit', keepalive: true })
      .then(function (r) {
        if (r.ok) { seen[path] = 1; try { localStorage.setItem(K, JSON.stringify({ d: day, p: seen })); } catch (x) {} }
        else if (r.status === 429 && again) setTimeout(function () { send(false); }, 70000); // busy shared Wi-Fi: try once more
      }).catch(function () {});
  }
  var hit = seen[path] ? Promise.resolve() : send(true);
  if (!document.getElementById('kv')) return;
  hit.then(badge);
  setInterval(function () { if (document.visibilityState === 'visible') badge(); }, 60000);
})();
