#!/usr/bin/env python3
"""QA kurungan fā‘il — Perkata Berwarna AtTartil (D-238).

Setiap kurungan fā‘il / nā'ib fā‘il (NF) / ism kāna di bawah fi‘il menunjukkan pelaku dengan
KALIMAH ARAB ASAL dari kad ayat itu (bukan ejaan rumi), dalam <span class="faar">.

  python3 qa/faail.py [halaman.html ...]          # semak (lalai: semua halaman); kod keluar 1 jika ada RALAT
  python3 qa/faail.py --amaran [halaman.html ...] # tunjuk juga AMARAN (untuk semakan ATV)

RALAT  : rumi tertinggal di hujung kurungan; Arab BM ≠ Arab EN; kalimah Arab tiada dalam kad ayat itu
         (atau ayat berikutnya); separuh rumi separuh Arab.
AMARAN : kalimah dipilih terletak SEBELUM fi‘il; baris akhir bukan marfū‘ (selalunya sah: ganti nama
         -ka/-hum, ḥarf jar zā'idah, mabnī, jar-majrūr NF) — semak dengan I‘rāb Dār al-Ṣaḥābah (Shamela 86).
Kurungan rujukan bertitik dua («dia: Nabi Musa») dan klausa tidak disemak untuk rumi.
"""
import os, re, sys, glob, html, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = re.compile(r'<section class="ay" id="a(\d+)"[^>]*>.*?</section>', re.S)
CARD = re.compile(r'<div class="w[^"]*"><p class="ar[^"]*"[^>]*>(.*?)</p>')
BR = re.compile(r'<span class="fa ([a-z]+)">\(<span class="lm">(.*?)</span><span class="le" lang="en">(.*?)</span>\)')
FAAR = re.compile(r'<span class="faar[^"]*"[^>]*>(.*)</span>', re.S)
SEG = re.compile(r'<span class="([pnv])">([^<]*)</span>')
OVL = re.compile(r'<span class="(?:cwo|sjo)[^"]*"[^>]*>[^<]*</span>')
MARKS = ''.join(chr(c) for c in range(0x06D6, 0x06EE))
LATIN = re.compile(r"^[A-Za-zĀ-ſḀ-ỿ‘’'ʼ‑\-]+$")


def plain(h):
    return html.unescape(re.sub(r'<[^>]+>', '', OVL.sub('', h)))


def card_segs(inner):
    inner = OVL.sub('', inner)
    m = re.search(r'<span class="sjw" title="([^"]*)"', inner)
    if m:
        out = []
        for part in html.unescape(m.group(1)).split(' · '):
            t, c = part.rsplit(' ', 1)
            out.append(({'ḥarf': 'p', 'isim': 'n', 'fiʿil': 'v'}[c], t))
        return out
    return [(c, html.unescape(t)) for c, t in SEG.findall(inner)]


def deacc(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    for a, b in (('dz', 'd'), ('dh', 'd'), ('sy', 's'), ('sh', 's'), ('ts', 't'), ('th', 't'), ('kh', 'h'), ('gh', 'g'), ('aw', 'au'), ('ay', 'ai')):
        s = s.replace(a, b)
    return re.sub(r"[‘’'ʼ‑\-]", '', s)


def is_rumi_tail(lm_text, le_text):
    """last token of BM is a transliteration if EN ends with the same token (accent-insensitive)."""
    if ':' in lm_text:
        return None
    a, b = lm_text.split(), le_text.split()
    if not a or not b:
        return None
    ta, tb = a[-1], b[-1]
    if LATIN.match(ta) and LATIN.match(tb) and deacc(ta) == deacc(tb) and len(deacc(ta)) >= 2:
        return ta
    return None


def marfu(w):
    w = w.rstrip(MARKS + ' ')
    if w.endswith(('ونَ', 'انِ', 'ىٰ', 'ى', 'ا', 'آ')):
        return True
    tail = w[-2:]
    if any(c in tail for c in 'ٌࣱُٞ'):
        return True
    if any(c in tail for c in 'ًࣰٍࣲَِٖٗ'):
        return False
    return True


def check(path, warn=False):
    s = open(path, encoding='utf-8').read()
    errs, warns, n = [], [], 0
    secs = list(SEC.finditer(s))
    allcards = []
    for m in secs:
        allcards.append([(c.start(), card_segs(c.group(1))) for c in CARD.finditer(m.group(0))])
    for si, sm in enumerate(secs):
        ay = sm.group(1); body = sm.group(0); cards = allcards[si]
        nxt = allcards[si + 1] if si + 1 < len(secs) else []
        texts = [''.join(t for _, t in cs) for _, cs in cards]
        # each card word also without a leading ḥarf segment (zā'id / conjunction dropped)
        def forms(cs):
            out = {''.join(t for _, t in cs)}
            for d in (1, 2):
                if len(cs) > d and all(c == 'p' for c, _ in cs[:d]):
                    out.add(''.join(t for _, t in cs[d:]))
            return out
        here = [forms(cs) for _, cs in cards]
        there = set().union(*[forms(cs) for _, cs in nxt]) if nxt else set()
        for b in BR.finditer(body):
            n += 1
            lm, le = b.group(2), b.group(3)
            lt, et = plain(lm), plain(le)
            vi = max([i for i, (p, _) in enumerate(cards) if p < b.start()] or [0])
            loc = f'{os.path.relpath(path, ROOT)} a{ay} · fi‘il «{texts[vi] if texts else ""}» · ({lt})'
            fm, fe = FAAR.search(lm), FAAR.search(le)
            if not fm:
                t = is_rumi_tail(lt, et)
                if t:
                    errs.append(f'RALAT rumi tertinggal «{t}» · {loc}')
                continue
            ab, ae = plain(fm.group(0)), plain(fe.group(0)) if fe else ''
            if ab != ae:
                errs.append(f'RALAT Arab BM ≠ EN («{ab}» / «{ae}») · {loc}')
            pre = plain(lm[:fm.start()]).split()
            if pre and LATIN.match(pre[-1]) and pre[-1][0].islower() and re.search(r'(u|un|an|in|i|a|una|ina|ani)$', pre[-1]) and len(pre[-1]) <= 12:
                # e.g. "kullu أَمۡرٍ" — a lowercase transliteration right before the Arabic
                en_pre = plain(le[:fe.start()]).split() if fe else []
                if en_pre and deacc(en_pre[-1]) == deacc(pre[-1]):
                    errs.append(f'RALAT separuh rumi «{pre[-1]} …» · {loc}')
            for w in ab.split(' '):
                hit = [i for i, f in enumerate(here) if w in f]
                if not hit and w not in there:
                    errs.append(f'RALAT «{w}» tiada dalam kad ayat ini · {loc}')
                elif hit and all(i < vi for i in hit) and w not in there:
                    warns.append(f'AMARAN «{w}» sebelum fi‘il · {loc}')
            last = ab.split(' ')[-1]
            if not marfu(last):
                warns.append(f'AMARAN bukan marfū‘ «{last}» · {loc}')
    return n, errs, warns


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    warn = '--amaran' in sys.argv
    files = args or sorted(glob.glob(os.path.join(ROOT, '**', 'index.html'), recursive=True))
    tn = te = tw = 0
    for f in files:
        n, errs, warns = check(f, warn)
        tn += n; te += len(errs); tw += len(warns)
        for e in errs:
            print(e)
        if warn:
            for w in warns:
                print(w)
    print(f'Selesai: {len(files)} halaman, {tn} kurungan, {te} RALAT, {tw} AMARAN'
          + ('' if warn else ' (guna --amaran untuk senarai)'))
    sys.exit(1 if te else 0)


if __name__ == '__main__':
    main()
