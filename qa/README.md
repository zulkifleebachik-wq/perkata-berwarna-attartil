# QA wajib — Perkata Berwarna (D-237, D-238)

Jalankan **sebelum setiap halaman surah baharu (atau suntingan) diterbitkan**. Kedua-duanya mesti selesai dengan kod keluar 0.

```
pip install uharfbuzz fonttools          # sekali sahaja
python3 qa/ligatur.py semak              # 0 masalah
python3 qa/faail.py                      # 0 RALAT
```

Semak satu halaman: `python3 qa/ligatur.py semak al-insan/index.html` · `python3 qa/faail.py al-insan/index.html`

## 1. `qa/ligatur.py` — warna huruf bercantum
> **Kaedah B (lulus iPhone Safari, 27 Nov 2026):** lapisan `.cwo` mestilah SALINAN span berwarna yang sama (bukan teks tunggal / `::before`) — jika struktur berbeza, Safari menyusun huruf berbeza dan perkataan kelihatan berganda. Kaedah baharu **wajib diuji pada iPhone sebenar** sebelum terbit.

Fon KFGQPC Hafs (tidak diubah, lesen KFGQPC) melukis lām+alif (ٱلۡأ, لِأ, لَا…), hamzah atas tatwil (بِـَٔا…)
dan perkataan sajdah sebagai satu glif / kepingan. Safari mewarnakan seluruh glif satu warna; Chrome memotong di tempat salah.
- `semak` melaporkan setiap perkataan berbilang warna yang glifnya merentas sempadan warna dan belum dibaiki.
- `baiki <halaman>` menambah tindanan warna (`.cw` + `.cwo` = salinan span yang sama, aria-hidden):
  ٱ + batang lām + jazm/baris lām ikut warna lām; alif + hamzah/madd ikut kata selepasnya. Rupa mushaf tidak berubah.
- Perkataan **sajdah** (ۤ) hanya dilaporkan — baiki dengan kaedah `.sjw` (D-033 option C) dan semak visual.
- Perkataan `.ar.lf` (fon LF: «لِلَّهِ», «بِسۡمِ») sudah dikira dibaiki.

## 2. `qa/faail.py` — kurungan fā‘il / NF / ism
Pelaku ditulis dengan **kalimah Arab asal dari kad ayat** dalam `<span class="faar" lang="ar" dir="rtl">` (warna ikut kad),
bukan rumi; ḥarf zā'idah tidak dipaparkan (كَفَىٰ بِٱللَّهِ → ٱللَّهِ). Kurungan rujukan bertitik dua («dia: Nabi Musa») dan klausa kekal.
- **RALAT** (mesti 0): rumi tertinggal; separuh rumi; Arab BM ≠ EN; kalimah tiada dalam kad ayat itu (atau ayat berikutnya).
- **AMARAN** (`--amaran`): kalimah sebelum fi‘il; baris akhir bukan marfū‘ — kebanyakannya sah (ganti nama -ka/-hum, jar zā'idah,
  mabnī, jar-majrūr NF). ATV menyemak setiap amaran baharu dengan I‘rāb al-Qur'ān, Dār al-Ṣaḥābah (Shamela 86).

Selepas QA: ATV (teks + paparan) → PA final vetting → "ya" UZB → terbit.
Folder ini tidak diterbitkan ke laman (lihat `.vercelignore`).
