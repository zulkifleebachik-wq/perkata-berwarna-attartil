#!/usr/bin/env python3
"""QA ligatur merentas warna — Perkata Berwarna AtTartil (D-237, D-238).

Fon KFGQPC Hafs melukis lām+alif (ٱلۡأ, لِأ, لَا…), hamzah atas tatwil (بِـَٔا…) dan perkataan sajdah
sebagai satu glif atau kepingan yang tidak sejajar dengan huruf. Safari mewarnakan seluruh glif dengan
satu warna; Chrome memotong di tempat salah. Alat ini:

  python3 qa/ligatur.py semak [halaman.html ...]   # semak (lalai: semua halaman); kod keluar 1 jika ada masalah
  python3 qa/ligatur.py baiki halaman.html [...]   # tambah tindanan warna (.cw/.cwo) pada perkataan yang belum dibaiki

Tindanan (kaedah B, lulus iPhone Safari 27 Nov 2026): warna asal dikekalkan; lapisan aria-hidden = SALINAN span yang sama
(struktur mesti sama, jika tidak Safari menyusun huruf berbeza → bertindih) mewarnakan semula
kawasan bercantum sahaja, dipotong pada batang lām (dikesan dari bentuk glif). Rupa mushaf tidak berubah.
Perkataan sajdah (ۤ) dilaporkan sahaja — guna kaedah .sjw (D-033 option C).
Keperluan: pip install uharfbuzz fonttools
"""
import os,sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import re,glob,html,json,collections
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
P=os.path.join(ROOT,'assets','kfgqpc-hafs-v18.ttf'); TT=TTFont(P); GS=TT.getGlyphSet(); NAMES=TT.getGlyphOrder()
FONT=hb.Font(hb.Face(open(P,'rb').read()))
GDEF=TT['GDEF'].table.GlyphClassDef.classDefs
def ismark(n): return GDEF.get(n)==3
class Flat(BasePen):
    def __init__(s,gs,dx): super().__init__(gs); s.dx=dx; s.polys=[]; s.cur=[]
    def _moveTo(s,p): s.cur=[(p[0]+s.dx,p[1])]
    def _lineTo(s,p): s.cur.append((p[0]+s.dx,p[1]))
    def _qCurveToOne(s,p1,p2):
        p0=(s.cur[-1][0]-s.dx,s.cur[-1][1])
        for k in range(1,9):
            t=k/8; x=(1-t)**2*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0]; y=(1-t)**2*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]; s.cur.append((x+s.dx,y))
    def _curveToOne(s,p1,p2,p3):
        p0=(s.cur[-1][0]-s.dx,s.cur[-1][1])
        for k in range(1,9):
            t=k/8; mt=1-t
            x=mt**3*p0[0]+3*mt*mt*t*p1[0]+3*mt*t*t*p2[0]+t**3*p3[0]; y=mt**3*p0[1]+3*mt*mt*t*p1[1]+3*mt*t*t*p2[1]+t**3*p3[1]; s.cur.append((x+s.dx,y))
    def _closePath(s): s.polys.append(s.cur); s.cur=[]
    _endPath=_closePath
def crossings(polys,y):
    xs=[]
    for poly in polys:
        n=len(poly)
        for i in range(n):
            (x1,y1),(x2,y2)=poly[i],poly[(i+1)%n]
            if (y1<=y<y2) or (y2<=y<y1): xs.append(x1+(y-y1)*(x2-x1)/(y2-y1))
    xs.sort(); return [(xs[i],xs[i+1]) for i in range(0,len(xs)-1,2)]
def stem_left(glyphs):
    """glyphs: list of (name,x). returns left edge of the rightmost tall vertical stroke (lām stem)."""
    polys=[]
    for n,x in glyphs:
        pen=Flat(GS,x); GS[n].draw(pen); polys+=pen.polys
    lefts=[]
    for y in range(700,1201,50):
        runs=[r for r in crossings(polys,y) if r[1]-r[0]>40]
        if runs and runs[-1][1]-runs[-1][0]<330: lefts.append(runs[-1][0])
    if not lefts: return None
    lefts.sort(); return lefts[len(lefts)//2]
MK=''.join(chr(c) for c in list(range(0x64b,0x660))+[0x670]+list(range(0x6d6,0x6ee)))
ALIFS='أإآاٱ'
def shape(t):
    b=hb.Buffer(); b.add_str(t); b.guess_segment_properties(); hb.shape(FONT,b,{})
    out=[];x=0
    for i,q in zip(b.glyph_infos,b.glyph_positions):
        out.append((NAMES[i.codepoint],i.cluster,x+q.x_offset,q.x_advance)); x+=q.x_advance
    return out,x
def shape_off(t):
    b=hb.Buffer(); b.add_str(t); b.guess_segment_properties(); hb.shape(FONT,b,{'calt':False})
    return [(NAMES[i.codepoint],i.cluster,q.x_advance) for i,q in zip(b.glyph_infos,b.glyph_positions)]
def regions(segs):
    """segs: [(cls,text)] -> (need, [(x0,x1,cls)], total)"""
    text=''.join(t for _,t in segs); starts=[];pos=0
    for c,t in segs: starts.append(pos); pos+=len(t)
    segof=lambda cl:max(k for k,s0 in enumerate(starts) if s0<=cl)
    g,tot=shape(text)
    base=[(n,cl,x,a) for n,cl,x,a in g if a>0 and not ismark(n)]
    # cluster spans of each base glyph
    cls_sorted=sorted(set(cl for _,cl,_,_ in g))
    def clend(cl):
        nx=[c for c in cls_sorted if c>cl]; return nx[0] if nx else len(text)
    regs=[]; need=False; why=set()
    # lām-alif units
    la=[]
    for k in range(len(segs)-1):
        c1,t1=segs[k]; c2,t2=segs[k+1]
        if c1!=c2 and t1.rstrip(MK).endswith('ل') and t2[:1] in ALIFS:
            lam_i=starts[k]+len(t1.rstrip(MK))-1; alif_i=starts[k+1]
            la.append((lam_i,alif_i,segs[k][0],segs[k+1][0]))
    consumed=set(); special=[]
    for lam_i,alif_i,lc,ac in la:
        unit=[(n,x,a) for n,cl,x,a in base if cl<=lam_i<clend(cl) or cl<=alif_i<clend(cl) or (lam_i<=cl<=alif_i)]
        if not unit: continue
        x0=min(x for _,x,_ in unit); x1=max(x+a for _,x,a in unit)
        sl=stem_left([(n,x) for n,x,_ in unit])
        if sl is None or not (x0<sl<x1): continue
        split=sl-25
        special.append((x0,split,ac)); special.append((split,x1,lc)); need=True; why.add('lamalif')
        for n,x,a in unit: consumed.add((n,x))
    for n,cl,x,a in base:
        if (n,x) in consumed: continue
        e=clend(cl); ks=sorted(set(segof(c) for c in range(cl,e)))
        cols=[segs[k][0] for k in ks]
        if len(set(cols))==1: regs.append((x,x+a,cols[0])); continue
        need=True; why.add('lig:'+n)
        # proportional split using calt-off advances of the covered characters
        off=shape_off(text); w={}
        for nn,c2,a2 in off:
            if cl<=c2<e: w[segof(c2)]=w.get(segof(c2),0)+a2
        totw=sum(w.values()) or 1
        # visual: later chars to the left (RTL) -> walk from right edge
        right=x+a
        for k in ks:
            ww=a*w.get(k,0)/totw; regs.append((right-ww,right,segs[k][0])); right-=ww
    regs+=special; regs.sort()
    merged=[]
    for r in regs:
        if merged and merged[-1][2]==r[2] and r[0]<=merged[-1][1]+1: merged[-1]=(merged[-1][0],max(r[1],merged[-1][1]),r[2])
        else: merged.append(r)
    return need,merged,tot,why
def markup(segs,merged,tot,extra_cls=''):
    text=''.join(t for _,t in segs)
    widths=collections.Counter()
    for x0,x1,c in merged: widths[c]+=x1-x0
    base=widths.most_common(1)[0][0]
    ov=''
    for i,(x0,x1,c) in enumerate(merged):
        if c==base: continue
        L=-400 if i==0 else 100*x0/tot; R=400 if i==len(merged)-1 else 100*x1/tot
        ov+=f'<span class="cwo {c}" aria-hidden="true" style="clip-path:polygon({L:.1f}% -60%,{R:.1f}% -60%,{R:.1f}% 160%,{L:.1f}% 160%)">{html.escape(text,quote=False)}</span>'
    title=' · '.join(f'{t} {dict(p="ḥarf",n="isim",v="fiʿil").get(c,c)}' for c,t in segs)
    return f'<span class="cw{extra_cls}" title="{html.escape(title)}"><span class="{base}">{html.escape(text,quote=False)}</span>{ov}</span>'

def ink_range(glyphs):
    xs=[]
    for n,x in glyphs:
        pen=Flat(GS,x); GS[n].draw(pen)
        for poly in pen.polys: xs+= [p[0] for p in poly]
    return (min(xs),max(xs)) if xs else None
def fixes(segs):
    """overlays (x0,x1,cls) that repaint only the problem units; ordinary boundaries stay native."""
    text=''.join(t for _,t in segs); starts=[];pos=0
    for c,t in segs: starts.append(pos); pos+=len(t)
    segof=lambda cl:max(k for k,s0 in enumerate(starts) if s0<=cl)
    g,tot=shape(text)
    base=[(n,cl,x,a) for n,cl,x,a in g if a>0 and not ismark(n)]
    cls_sorted=sorted(set(cl for _,cl,_,_ in g))
    def clend(cl):
        nx=[c for c in cls_sorted if c>cl]; return nx[0] if nx else len(text)
    out=[]; used=set()
    for k in range(len(segs)-1):
        c1,t1=segs[k]; c2,t2=segs[k+1]
        if c1!=c2 and t1.rstrip(MK).endswith('ل') and t2[:1] in ALIFS:
            lam_i=starts[k]+len(t1.rstrip(MK))-1; alif_i=starts[k+1]
            unit=[(n,x,a) for n,cl,x,a in base if cl<=lam_i<clend(cl) or cl<=alif_i<clend(cl) or (lam_i<=cl<=alif_i)]
            if not unit: continue
            sl=stem_left([(n,x) for n,x,_ in unit]); ir=ink_range([(n,x) for n,x,_ in unit])
            if sl is None or ir is None: continue
            split=sl-25
            if not (ir[0]<split<ir[1]): continue
            out.append((ir[0]-20,split,c2)); out.append((split,ir[1]+20,c1))
            for n,x,a in unit: used.add((n,x))
    for n,cl,x,a in base:
        if (n,x) in used: continue
        e=clend(cl); ks=sorted(set(segof(c) for c in range(cl,e)))
        if len(set(segs[k][0] for k in ks))==1: continue
        if n.startswith('sajda'): continue
        off=shape_off(text); w={}
        for nn,c2,a2 in off:
            if cl<=c2<e: w[segof(c2)]=w.get(segof(c2),0)+a2
        totw=sum(w.values()) or 1
        ir=ink_range([(n,x)]); right=x+a
        bounds=[]
        for k in ks:
            ww=a*w.get(k,0)/totw; bounds.append([right-ww,right,segs[k][0]]); right-=ww
        bounds[0][1]=max(bounds[0][1],ir[1]+20); bounds[-1][0]=min(bounds[-1][0],ir[0]-20)
        out+= [tuple(b) for b in bounds]
    return out,tot
def markup_fix(inner_html,text,ovs,tot):
    ov=''.join(f'<span class="cwo {c}" aria-hidden="true" style="clip-path:polygon({100*x0/tot:.1f}% -60%,{100*x1/tot:.1f}% -60%,{100*x1/tot:.1f}% 160%,{100*x0/tot:.1f}% 160%)">{html.escape(text,quote=False)}</span>' for x0,x1,c in ovs)
    return f'<span class="cw">{inner_html}{ov}</span>'

UPEM=2048
def shape_full(t):
    b=hb.Buffer(); b.add_str(t); b.guess_segment_properties(); hb.shape(FONT,b,{})
    out=[];x=0
    for i,q in zip(b.glyph_infos,b.glyph_positions):
        out.append((NAMES[i.codepoint],i.cluster,x+q.x_offset,q.y_offset,q.x_advance)); x+=q.x_advance
    return out,x
def contours(n,dx,dy=0):
    pen=Flat(GS,dx); GS[n].draw(pen)
    return [[(px,py+dy) for px,py in poly] for poly in pen.polys]
def bbox(poly): xs=[p[0] for p in poly]; ys=[p[1] for p in poly]; return min(xs),min(ys),max(xs),max(ys)
def fixes2(segs):
    """band overlays + mark boxes. returns list of ('band',x0,x1,cls) / ('box',x0,y0,x1,y1,cls), tot"""
    text=''.join(t for _,t in segs); starts=[];pos=0
    for c,t in segs: starts.append(pos); pos+=len(t)
    segof=lambda cl:max(k for k,s0 in enumerate(starts) if s0<=cl)
    g,tot=shape_full(text)
    cls_sorted=sorted(set(x[1] for x in g))
    def clend(cl):
        nx=[c for c in cls_sorted if c>cl]; return nx[0] if nx else len(text)
    base=[(n,cl,x,y,a) for n,cl,x,y,a in g if a>0 and not ismark(n)]
    marks=[(n,cl,x,y) for n,cl,x,y,a in g if ismark(n)]
    bands=[]; used=set(); cuts=[]   # cuts: (split, left_cls, right_cls, x0,x1, unit glyphs)
    for k in range(len(segs)-1):
        c1,t1=segs[k]; c2,t2=segs[k+1]
        if c1!=c2 and t1.rstrip(MK).endswith('ل') and t2[:1] in ALIFS:
            lam_i=starts[k]+len(t1.rstrip(MK))-1; alif_i=starts[k+1]
            unit=[(n,x,y) for n,cl,x,y,a in base if cl<=lam_i<clend(cl) or cl<=alif_i<clend(cl) or (lam_i<=cl<=alif_i)]
            if not unit: continue
            sl=stem_left([(n,x) for n,x,_ in unit]); ir=ink_range([(n,x) for n,x,_ in unit])
            if sl is None or ir is None: continue
            split=sl-25
            if not (ir[0]<split<ir[1]): continue
            bands.append(('band',ir[0]-20,split,c2)); bands.append(('band',split,ir[1]+20,c1))
            cuts.append((split,c2,c1,unit))
            for n,x,y in unit: used.add((n,x))
    for n,cl,x,y,a in base:
        if (n,x) in used or n.startswith('sajda'): continue
        e=clend(cl); ks=sorted(set(segof(c) for c in range(cl,e)))
        if len(set(segs[k][0] for k in ks))==1: continue
        off=shape_off(text); w={}
        for nn,c2_,a2 in off:
            if cl<=c2_<e: w[segof(c2_)]=w.get(segof(c2_),0)+a2
        totw=sum(w.values()) or 1; ir=ink_range([(n,x)]); right=x+a; bb=[]
        for kk in ks:
            ww=a*w.get(kk,0)/totw; bb.append(['band',right-ww,right,segs[kk][0]]); right-=ww
        bb[0][2]=max(bb[0][2],ir[1]+20); bb[-1][1]=min(bb[-1][1],ir[0]-20)
        for i in range(len(bb)-1): cuts.append((bb[i][1],bb[i+1][3],bb[i][3],[(n,x,0)]))
        bands+=[tuple(b) for b in bb]
    boxes=[]
    def colour_at(xc):
        for b in bands:
            if b[1]<=xc<b[2]: return b[3]
        return None
    for split,lc,rc,unit in cuts:
        # separate mark glyphs near the cut
        for n,cl,x,y in marks:
            for poly in contours(n,x,y):
                x0,y0,x1,y1=bbox(poly)
                mc=segs[segof(cl)][0]
                if (x0<split<x1) or (colour_at((x0+x1)/2) not in (None,mc) and abs((x0+x1)/2-split)<600):
                    boxes.append(('box',x0-15,y0-15,x1+15,y1+15,mc))
        # mark-like contours inside the unit glyphs (jazm/hamza/madda drawn in the ligature)
        for n,x,y in unit:
            for poly in contours(n,x,y):
                x0,y0,x1,y1=bbox(poly)
                if y0>1250 and (y1-y0)<500 and (x1-x0)<600:
                    mc=rc if (x0+x1)/2>split else lc
                    if x0<split<x1: boxes.append(('box',x0-15,y0-15,x1+15,y1+15,mc))
    return bands+boxes,tot
def markup2(inner_html,text,items,tot):
    ov=''
    for it in items:
        if it[0]=='band':
            _,x0,x1,c=it; X0=100*x0/tot; X1=100*x1/tot
            pts=f'{X0:.1f}% -60%,{X1:.1f}% -60%,{X1:.1f}% 160%,{X0:.1f}% 160%'
        else:
            _,x0,y0,x1,y1,c=it; X0=100*x0/tot; X1=100*x1/tot
            T=f'calc(var(--bl) - {y1/UPEM:.3f}em)'; B=f'calc(var(--bl) - {y0/UPEM:.3f}em)'
            pts=f'{X0:.1f}% {T},{X1:.1f}% {T},{X1:.1f}% {B},{X0:.1f}% {B}'
        ov+=f'<span class="cwo {c}" aria-hidden="true" style="clip-path:polygon({pts})">{inner_html}</span>'
    return f'<span class="cw">{inner_html}{ov}</span>'


# ---------------- semak / baiki ----------------
CARD=re.compile(r'(<div class="w[^"]*"><p class="ar)( lf)?(" lang="ar" dir="rtl">)(.*?)(</p>)')
FAAR=re.compile(r'(<span class="faar( lf)?" lang="ar" dir="rtl">)(.*?)(</span>)(?=</span><span class="le"|</span>\))')
SEG=re.compile(r'<span class="([pnv])">([^<]*)</span>')
CSS=(".cw{position:relative;display:inline-block;white-space:nowrap}.ar .cw{line-height:2;--bl:1.293em}"
     ".faar .cw{line-height:1.3;--bl:0.943em}.cwo{position:absolute;top:0;right:0;white-space:nowrap;pointer-events:none;"
     "-webkit-user-select:none;user-select:none}.cwo .p,.cwo .n,.cwo .v{color:inherit!important}.sjo::before{content:attr(data-t)}")
KF=".ar{font-family:'KFGQPC Hafs'"
def words_in(inner):
    """split an .ar/.faar inner html into words: [(raw_html, segs)]; covered words (cw/sjw/lsj) marked None"""
    out=[]
    for part in re.split(r'(?<=</span>) (?=<span)',inner):
        if 'class="cw"' in part or 'class="sjw"' in part or 'class="lsj"' in part: out.append((part,None)); continue
        segs=[(c,html.unescape(t)) for c,t in SEG.findall(part)]
        out.append((part,segs))
    return out
def problem(segs):
    if len(segs)<2 or len(set(c for c,_ in segs))<2: return None
    text=''.join(t for _,t in segs)
    if 'ۤ' in text:
        g,_=shape(text)
        return 'SAJDAH (guna kaedah .sjw)' if any(n.startswith('sajda') for n,*_ in g) else None
    items,_=fixes2(segs)
    return 'ligatur merentas warna' if items else None
def scan(path,fix=False):
    s=open(path,encoding='utf-8').read()
    if KF not in s: return [],False
    probs=[]; changed=False
    def handle(inner,ctx,lf):
        nonlocal changed
        parts=[]
        for raw,segs in words_in(inner):
            if segs is None or lf: parts.append(raw); continue
            why=problem(segs)
            if why:
                text=''.join(t for _,t in segs)
                m2=re.match(r'^(.*?)((?:<span class="wq"[^>]*>[^<]*</span>)*)$',raw,re.S); core,wq=m2.group(1),m2.group(2)
                if fix and why.startswith('ligatur') and core==''.join(f'<span class="{c}">{html.escape(t,quote=False)}</span>' for c,t in segs):
                    items,tot=fixes2(segs); raw=markup2(core,text,items,tot)+wq; changed=True
                else: probs.append((ctx,text,why))
            parts.append(raw)
        return ' '.join(parts)
    def card(m): return m.group(1)+(m.group(2) or '')+m.group(3)+handle(m.group(4),'kad',bool(m.group(2)))+m.group(5)
    def faar(m): return m.group(1)+handle(m.group(3),'kurungan fā‘il',bool(m.group(2)))+m.group(4)
    n=CARD.sub(card,s); n=FAAR.sub(faar,n)
    if fix and changed:
        if '.cwo .p,.cwo .n' not in n: n=n.replace('</style>',CSS+'</style>',1)
        open(path,'w',encoding='utf-8').write(n)
    return probs,changed
def main():
    if len(sys.argv)<2 or sys.argv[1] not in ('semak','baiki'): print(__doc__); sys.exit(2)
    mode=sys.argv[1]; files=sys.argv[2:] or sorted(glob.glob(os.path.join(ROOT,'**','index.html'),recursive=True))
    total=0
    for f in files:
        probs,ch=scan(f,fix=(mode=='baiki'))
        rel=os.path.relpath(f,ROOT)
        if ch: print('DIBAIKI',rel)
        for ctx,t,why in probs: print(f'MASALAH {rel} · {ctx} · {t} · {why}'); total+=1
    print(f'Selesai: {len(files)} halaman, {total} masalah.' + ('' if total==0 else ' Jalankan: python3 qa/ligatur.py baiki <halaman>'))
    sys.exit(1 if total else 0)
if __name__=='__main__': main()
