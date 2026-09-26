"""results.json → 검증 리포트 HTML 두 장 (크몽 상세 이미지용).

차트는 손으로 그린 SVG 다. 색은 dataviz 검증기를 통과한 두 색만 쓴다:
전략 = #3987e5, 그냥 보유 = #d95926 (배경 #0f1420 기준 CVD ΔE 26.8).
색은 대상을 따른다 — 모든 차트에서 파랑은 전략, 주황은 보유, 회색은 "착시"다.

    python render_report.py <출력 폴더>
"""
from __future__ import annotations

import html
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
R = json.loads((HERE / "results.json").read_text())

C = {
    "bg": "#0f1420", "panel": "#161d2d", "line": "#2a3346", "grid": "#222a3b",
    "t1": "#f2f4f8", "t2": "#aab6c9", "t3": "#7b8aa3",
    "s1": "#3987e5", "s2": "#d95926", "gray": "#6b778c",
    "good": "#0ca30c", "bad": "#d03b3b",
}
RAMP = ["#0d366b", "#104281", "#184f95", "#1c5cab", "#256abf", "#2a78d6",
        "#3987e5", "#5598e7", "#6da7ec", "#86b6ef", "#9ec5f4", "#b7d3f6"]
FONT = '"Malgun Gothic","Apple SD Gothic Neo",-apple-system,"Segoe UI",sans-serif'


def e(s):
    return html.escape(str(s))


def pct(x, d=1, sign=False):
    s = f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"
    return s


def ramp(t):
    t = min(max(t, 0.0), 1.0)
    return RAMP[min(int(t * (len(RAMP) - 1) + 0.5), len(RAMP) - 1)]


def bar_path(x, w, y0, y1, r=3):
    """기준선에 붙은 쪽은 평평하고 데이터 끝만 둥근 막대."""
    if abs(y1 - y0) < 0.5:
        return f'M{x},{y0}h{w}'
    r = min(r, w / 2, abs(y1 - y0))
    if y1 < y0:   # 위로
        return (f"M{x},{y0}V{y1 + r}Q{x},{y1} {x + r},{y1}H{x + w - r}"
                f"Q{x + w},{y1} {x + w},{y1 + r}V{y0}Z")
    return (f"M{x},{y0}V{y1 - r}Q{x},{y1} {x + r},{y1}H{x + w - r}"
            f"Q{x + w},{y1} {x + w},{y1 - r}V{y0}Z")


def swatch(color, kind="line"):
    if kind == "line":
        return f'<svg width="18" height="10"><rect x="0" y="4" width="18" height="2.5" rx="1" fill="{color}"/></svg>'
    if kind == "diamond":
        return f'<svg width="12" height="12"><rect x="2.5" y="2.5" width="7" height="7" fill="{color}" transform="rotate(45 6 6)"/></svg>'
    return f'<svg width="12" height="12"><rect x="0" y="0" width="12" height="12" rx="2" fill="{color}"/></svg>'


# ── 차트 1: 누적 곡선 (로그) ───────────────────────────────────────────
def chart_equity(W=920, H=300):
    eq = R["equity"]
    a, b = np.array(eq["best_cost15"]), np.array(eq["buy_hold"])
    dates = eq["dates"]
    ml, mr, mt, mb = 52, 118, 12, 28
    lo = math.log10(min(a.min(), b.min()) * 0.9)
    hi = math.log10(max(a.max(), b.max()) * 1.1)
    X = lambda i: ml + i / (len(a) - 1) * (W - ml - mr)
    Y = lambda v: mt + (hi - math.log10(v)) / (hi - lo) * (H - mt - mb)
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for v in [0.25, 0.5, 1, 2, 5, 10, 20, 50, 100]:
        if lo <= math.log10(v) <= hi:
            y = Y(v)
            s.append(f'<line x1="{ml}" x2="{W - mr}" y1="{y:.1f}" y2="{y:.1f}" stroke="{C["grid"]}" stroke-width="1"/>')
            lab = f"{v:g}배"
            s.append(f'<text x="{ml - 8}" y="{y + 4:.1f}" fill="{C["t3"]}" font-size="11" text-anchor="end">{lab}</text>')
    prev = None
    for i, d in enumerate(dates):
        yr = d[:4]
        if yr == prev:
            continue
        prev = yr
        if True:
            x = X(i)
            s.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{H - mb}" y2="{H - mb + 4}" stroke="{C["line"]}"/>')
            s.append(f'<text x="{x:.1f}" y="{H - 8}" fill="{C["t3"]}" font-size="11" text-anchor="middle">{yr}</text>')
    for arr, col in ((b, C["s2"]), (a, C["s1"])):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(arr))
        s.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2" stroke-linejoin="round"/>')
    # 끝 라벨: 글자는 글자색, 옆에 색 표식
    ends = sorted([(Y(a[-1]), "고른 조합", a[-1], C["s1"]), (Y(b[-1]), "그냥 보유", b[-1], C["s2"])])
    if ends[1][0] - ends[0][0] < 34:
        ends[1] = (ends[0][0] + 34,) + ends[1][1:]
    for y, name, v, col in ends:
        x = W - mr + 10
        s.append(f'<rect x="{x}" y="{y - 6:.1f}" width="10" height="2.5" rx="1" fill="{col}"/>')
        s.append(f'<text x="{x + 14}" y="{y - 1:.1f}" fill="{C["t1"]}" font-size="12" font-weight="700">{v:.1f}배</text>')
        s.append(f'<text x="{x + 14}" y="{y + 14:.1f}" fill="{C["t2"]}" font-size="11">{name}</text>')
    s.append("</svg>")
    return "".join(s)


# ── 차트 2: 격자 열지도 ────────────────────────────────────────────────
def chart_heat(cw=44, ch=30):
    fast, slow = R["grid"]["fast"], R["grid"]["slow"]
    h = R["heat_cost0"]
    vals = np.array(list(h.values()))
    lo, hi = float(vals.min()), float(vals.max())
    bf, bs = R["best_cost0"]["pick"]
    ml, mt = 52, 22
    W, H = ml + cw * len(slow) + 4, mt + ch * len(fast) + 40
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for ci, sl in enumerate(slow):
        s.append(f'<text x="{ml + ci * cw + cw / 2}" y="{mt - 7}" fill="{C["t3"]}" font-size="11" text-anchor="middle">{sl}</text>')
    for ri, fa in enumerate(fast):
        y = mt + ri * ch
        s.append(f'<text x="{ml - 8}" y="{y + ch / 2 + 4}" fill="{C["t3"]}" font-size="11" text-anchor="end">{fa}</text>')
        for ci, sl in enumerate(slow):
            x = ml + ci * cw
            k = f"{fa}/{sl}"
            if k not in h:
                continue
            t = (h[k] - lo) / (hi - lo)
            col = ramp(t)
            txt = C["bg"] if t > 0.62 else C["t1"]
            s.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cw - 2}" height="{ch - 2}" rx="3" fill="{col}"/>')
            s.append(f'<text x="{x + cw / 2}" y="{y + ch / 2 + 4}" fill="{txt}" font-size="10.5" text-anchor="middle">{h[k]:.2f}</text>')
            if fa == bf and sl == bs:
                s.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="4" fill="none" stroke="{C["t1"]}" stroke-width="2.5"/>')
    # 축 제목
    s.append(f'<text x="{ml + cw * len(slow) / 2}" y="{mt + ch * len(fast) + 18}" fill="{C["t2"]}" font-size="11.5" text-anchor="middle">장기 이동평균 (일)</text>')
    s.append(f'<text x="14" y="{mt + ch * len(fast) / 2}" fill="{C["t2"]}" font-size="11.5" text-anchor="middle" transform="rotate(-90 14 {mt + ch * len(fast) / 2})">단기 (일)</text>')
    s.append("</svg>")
    # 눈금 막대
    stops = "".join(f'<stop offset="{i / (len(RAMP) - 1):.3f}" stop-color="{c}"/>' for i, c in enumerate(RAMP))
    bh = R["buy_hold"]["sharpe"]
    L = 260
    bx = (bh - lo) / (hi - lo) * L if lo < bh < hi else None
    leg = [f'<svg width="{L + 90}" height="52"><defs><linearGradient id="g">{stops}</linearGradient></defs>',
           f'<rect x="0" y="6" width="{L}" height="10" rx="3" fill="url(#g)"/>',
           f'<text x="0" y="32" fill="{C["t3"]}" font-size="11">{lo:.2f}</text>',
           f'<text x="{L}" y="32" fill="{C["t3"]}" font-size="11" text-anchor="end">{hi:.2f}</text>',
           f'<text x="{L + 10}" y="15" fill="{C["t2"]}" font-size="11">샤프 (비용 0)</text>']
    if bx is not None:
        leg.append(f'<rect x="{bx - 1:.1f}" y="2" width="2.5" height="18" fill="{C["t1"]}"/>')
        leg.append(f'<text x="{bx - 3:.1f}" y="48" fill="{C["t1"]}" font-size="11">▲ 그냥 보유 {bh:.2f}</text>')
    if bx is None and bh < lo:
        leg.append(f'<text x="0" y="44" fill="{C["t3"]}" font-size="10.5">그냥 보유 {bh:.2f} 는 이 눈금보다 아래</text>')
    leg.append("</svg>")
    return "".join(s), "".join(leg)


# ── 차트 3: 워크포워드 ─────────────────────────────────────────────────
def chart_wf(W=920, H=228):
    folds = R["walk_forward"]["folds"]
    dates = R["equity"]["dates"]  # 주간 샘플이라 날짜는 따로 계산
    ml, mr, mt, mb = 52, 16, 22, 50
    vals = [v for f in folds for v in (f["is_sharpe"], f["oos_sharpe"], f["bh_sharpe"])]
    lo, hi = min(-0.5, min(vals) * 1.4), max(vals) * 1.15
    Y = lambda v: mt + (hi - v) / (hi - lo) * (H - mt - mb)
    gw = (W - ml - mr) / len(folds)
    bw = min(34, gw * 0.24)
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for v in np.arange(math.ceil(lo), math.floor(hi) + 1):
        y = Y(v)
        s.append(f'<line x1="{ml}" x2="{W - mr}" y1="{y:.1f}" y2="{y:.1f}" stroke="{C["grid"] if v else C["line"]}" stroke-width="{1 if v else 1.5}"/>')
        s.append(f'<text x="{ml - 8}" y="{y + 4:.1f}" fill="{C["t3"]}" font-size="11" text-anchor="end">{v:+.0f}</text>')
    y0 = Y(0)
    first = int(R["data"]["first"][:4])
    for i, f in enumerate(folds):
        cx = ml + gw * i + gw / 2
        x1, x2 = cx - bw - 3, cx + 3
        s.append(f'<path d="{bar_path(x1, bw, y0, Y(f["is_sharpe"]))}" fill="{C["gray"]}"/>')
        s.append(f'<path d="{bar_path(x2, bw, y0, Y(f["oos_sharpe"]))}" fill="{C["s1"]}"/>')
        v = f["oos_sharpe"]
        ty = Y(v) - 7 if v >= 0 else Y(v) + 15
        s.append(f'<text x="{x2 + bw / 2:.1f}" y="{ty:.1f}" fill="{C["t1"]}" font-size="11.5" font-weight="700" text-anchor="middle">{v:+.2f}</text>')
        dx, dy = cx + bw + 14, Y(f["bh_sharpe"])
        s.append(f'<rect x="{dx - 4.5:.1f}" y="{dy - 4.5:.1f}" width="9" height="9" fill="{C["s2"]}" stroke="{C["panel"]}" stroke-width="2" transform="rotate(45 {dx:.1f} {dy:.1f})"/>')
        yr = first + 3 + i
        s.append(f'<text x="{cx:.1f}" y="{H - 30}" fill="{C["t2"]}" font-size="12" text-anchor="middle">{yr}.03 ~ {yr + 1}.03</text>')
        fa, sl = f["pick"]
        s.append(f'<text x="{cx:.1f}" y="{H - 12}" fill="{C["t3"]}" font-size="11" text-anchor="middle">고른 조합 {fa}/{sl}</text>')
    s.append("</svg>")
    return "".join(s)


# ── 차트 4: 순열 검정 분포 ─────────────────────────────────────────────
def chart_perm(W=520, H=196):
    p = np.array(R["perm"]["perm_max"])
    real = R["perm"]["real_max"]
    q95 = R["perm"]["perm_q"]["0.95"]
    lo, hi, step = 0.4, 1.7, 0.05
    edges = np.arange(lo, hi + 1e-9, step)
    cnt, _ = np.histogram(np.clip(p, lo, hi - 1e-9), bins=edges)
    ml, mr, mt, mb = 16, 16, 34, 40
    X = lambda v: ml + (v - lo) / (hi - lo) * (W - ml - mr)
    Y = lambda c: H - mb - c / cnt.max() * (H - mt - mb)
    bw = (W - ml - mr) / len(cnt)
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    s.append(f'<line x1="{ml}" x2="{W - mr}" y1="{H - mb}" y2="{H - mb}" stroke="{C["line"]}" stroke-width="1.5"/>')
    for i, c in enumerate(cnt):
        if c:
            s.append(f'<path d="{bar_path(ml + i * bw + 1, bw - 2, H - mb, Y(c), 2)}" fill="{C["gray"]}"/>')
    for v in (0.5, 0.75, 1.0, 1.25, 1.5):
        s.append(f'<text x="{X(v):.1f}" y="{H - mb + 16}" fill="{C["t3"]}" font-size="11" text-anchor="middle">{v:.2f}</text>')
    s.append(f'<text x="{W / 2}" y="{H - 6}" fill="{C["t2"]}" font-size="11" text-anchor="middle">격자를 다시 뒤져 찾은 최고 샤프</text>')
    xq = X(q95)
    s.append(f'<line x1="{xq:.1f}" x2="{xq:.1f}" y1="{mt - 4}" y2="{H - mb}" stroke="{C["t3"]}" stroke-width="1.5" stroke-dasharray="4 3"/>')
    s.append(f'<text x="{xq + 5:.1f}" y="{mt + 6}" fill="{C["t3"]}" font-size="10.5">상위 5% 선 {q95:.2f}</text>')
    xr = X(real)
    s.append(f'<line x1="{xr:.1f}" x2="{xr:.1f}" y1="{mt - 18}" y2="{H - mb}" stroke="{C["s1"]}" stroke-width="2.5"/>')
    s.append(f'<text x="{xr - 6:.1f}" y="{mt - 8}" fill="{C["t1"]}" font-size="11.5" font-weight="700" text-anchor="end">실제 결과 {real:.2f}</text>')
    s.append("</svg>")
    return "".join(s)


# ── 페이지 ─────────────────────────────────────────────────────────────
CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1000px;background:{C['bg']};color:{C['t1']};font-family:{FONT};padding:40px 40px 34px}}
.brand{{display:flex;justify-content:space-between;align-items:center;font-size:13px;color:{C['t3']}}}
.brand b{{color:{C['s1']};letter-spacing:.3px}}
.chip{{font-size:12px;color:{C['t2']};border:1px solid {C['line']};border-radius:4px;padding:3px 9px}}
h1{{font-size:30px;font-weight:800;letter-spacing:-.4px;margin-top:14px}}
h1 small{{font-size:16px;color:{C['t3']};font-weight:600;margin-left:8px}}
.meta{{margin-top:10px;font-size:13px;color:{C['t2']};line-height:1.65}}
.meta b{{color:{C['t1']}}}
.card{{background:{C['panel']};border:1px solid {C['line']};border-radius:10px;padding:18px 22px;margin-top:14px}}
.ct{{font-size:15.5px;font-weight:700}}
.cs{{font-size:12.5px;color:{C['t2']};margin-top:4px;line-height:1.55}}
.leg{{display:flex;gap:18px;margin:12px 0 6px;font-size:12px;color:{C['t2']};align-items:center}}
.leg span{{display:flex;gap:6px;align-items:center}}
.tiles{{display:flex;gap:12px;margin-top:18px}}
.tile{{flex:1;background:{C['panel']};border:1px solid {C['line']};border-radius:10px;padding:16px 18px}}
.tile .k{{font-size:12.5px;color:{C['t2']}}}
.tile .v{{font-size:30px;font-weight:800;margin-top:6px;letter-spacing:-.5px}}
.tile .v small{{font-size:13px;color:{C['t2']};font-weight:600;margin-left:6px}}
.tile .d{{font-size:12px;color:{C['t3']};margin-top:6px;line-height:1.5}}
.row{{display:flex;gap:18px}}
.note{{font-size:12.5px;color:{C['t2']};line-height:1.6}}
.note b{{color:{C['t1']}}}
.callout{{border-left:3px solid {C['line']};padding:2px 0 2px 12px;margin-top:12px}}
table{{width:100%;border-collapse:collapse;margin-top:10px;font-size:13px}}
td,th{{padding:7px 8px;border-bottom:1px solid {C['line']};text-align:left;vertical-align:middle}}
th{{font-size:11.5px;color:{C['t3']};font-weight:600}}
td.r{{text-align:right;font-variant-numeric:tabular-nums}}
.st{{display:inline-flex;gap:6px;align-items:center;font-weight:700;font-size:12.5px}}
.verdict{{font-size:20px;font-weight:800}}
.concl{{font-size:14px;line-height:1.7;color:{C['t1']}}}
.foot{{margin-top:18px;font-size:11.5px;color:{C['t3']};line-height:1.7}}
.foot b{{color:{C['t2']}}}
"""


def head(n):
    d = R["data"]
    return f"""
<div class="brand"><div><b>여의도 퀀트 연구원 출신</b> &nbsp;|&nbsp; 백테스트 검증 리포트 견본</div>
<div class="chip">예시이며 특정 전략을 권하지 않습니다</div></div>
<h1>{'1. 백테스트만 보면' if n == 1 else '2. 검증하면'}<small>{n}/2</small></h1>
<div class="meta">규칙 <b>단기 이동평균이 장기보다 위면 보유, 아니면 현금</b> (교과서 예시, 공매도 없음)<br>
데이터 바이낸스 BTC/USDT 일봉 {d['first']} ~ {d['last']} ({d['days']:,}일) &nbsp;|&nbsp;
탐색 {R['grid']['n']}개 조합 &nbsp;|&nbsp; 비용 편도 {R['cost_bp_per_side'] / 100:.2f}%</div>"""


def page1():
    b0, bc, bh = R["best_cost0"]["cost0"], R["best_cost0"]["cost15"], R["buy_hold"]
    f, sl = R["best_cost0"]["pick"]
    heat, heatleg = chart_heat()
    h = np.array(list(R["heat_cost0"].values()))
    beat = int((h > bh["sharpe"]).sum())
    look = R["lookahead"]
    tiles = f"""
<div class="tiles">
 <div class="tile"><div class="k">샤프 (위험 대비 수익)</div>
  <div class="v">{b0['sharpe']:.2f}<small>보유 {bh['sharpe']:.2f}</small></div>
  <div class="d">고른 조합 단기 {f}일, 장기 {sl}일</div></div>
 <div class="tile"><div class="k">연 수익률</div>
  <div class="v">{pct(b0['cagr'])}<small>보유 {pct(bh['cagr'])}</small></div>
  <div class="d">그냥 들고 있는 것의 {b0['cagr'] / bh['cagr']:.1f}배</div></div>
 <div class="tile"><div class="k">최대 낙폭</div>
  <div class="v">{pct(b0['mdd'])}<small>보유 {pct(bh['mdd'])}</small></div>
  <div class="d">보유 낙폭의 {b0['mdd'] / bh['mdd'] * 100:.0f}% 수준</div></div>
</div>"""
    eqc = f"""
<div class="card"><div class="ct">누적 자산 (로그 눈금, 비용 반영)</div>
<div class="leg"><span>{swatch(C['s1'])}고른 조합 {f}/{sl}</span><span>{swatch(C['s2'])}그냥 보유</span></div>
{chart_equity()}</div>"""
    heatc = f"""
<div class="card"><div class="row">
 <div>
  <div class="ct">{R['grid']['n']}개 조합의 샤프</div>
  <div class="cs">흰 테두리가 고른 조합입니다</div>
  <div style="margin-top:10px">{heat}</div>
  <div style="margin-top:4px">{heatleg}</div>
 </div>
 <div style="flex:1;padding-top:4px">
  <div class="note callout"><b>{R['grid']['n']}개 중 {beat}개가 그냥 보유({bh['sharpe']:.2f})보다 좋아 보입니다.</b><br>
  과거 데이터 위에서는 거의 무엇을 골라도 좋아 보인다는 뜻입니다. 그중 가장 좋은 칸을 고르면 숫자는 더 좋아집니다.</div>
  <div class="note callout"><b>신호 시점이 하루만 어긋나도 샤프 {look['right']:.2f} → {look['same_bar']:.2f}</b><br>
  오늘 종가로 신호를 만들고 오늘 수익까지 가져가면 미래 정보가 섞입니다. 이 리포트는 오늘 신호를 내일 수익에만 적용하고, 완전예지 신호로 그 정렬을 따로 검증했습니다.</div>
  <div class="note callout"><b>비용 반영: 샤프 {b0['sharpe']:.2f} → {bc['sharpe']:.2f}</b><br>
  이 규칙은 {b0['days'] // 365}년 넘는 동안 진입이 {b0['entries']}번뿐이라 비용 영향이 작았습니다. 거래가 잦은 규칙일수록 이 차이가 커집니다.</div>
 </div>
</div></div>"""
    tail = f"""
<div class="card" style="text-align:center;padding:18px">
 <div class="concl">여기서 멈추면 이 규칙은 <b>수익은 두 배, 낙폭은 절반</b>인 훌륭한 전략으로 보입니다.<br>
 <span style="color:{C['t2']}">다음 장에서 이 숫자를 믿어도 되는지 검증합니다.</span></div></div>"""
    return f"<style>{CSS}</style>{head(1)}{tiles}{eqc}{heatc}{tail}"


def status(ok):
    col = C["good"] if ok else C["bad"]
    icon = "✓" if ok else "✕"
    txt = "통과" if ok else "탈락"
    return f'<span class="st" style="color:{col}">{icon} {txt}</span>'


def page2():
    wf = R["walk_forward"]
    o, ob = wf["oos"], wf["oos_bh"]
    g = R["gates"]
    npass = sum(1 for v in g.values() if v["pass"])
    picks = " → ".join(f"{f['pick'][0]}/{f['pick'][1]}" for f in wf["folds"])
    wfc = f"""
<div class="card"><div class="ct">워크포워드: 3년으로 고르고, 다음 1년에 써 봤다</div>
<div class="cs">해마다 앞 3년에서 가장 좋았던 조합을 골라, 아직 보지 않은 다음 1년에 그대로 적용했습니다. 실제로 쓸 때와 같은 방식입니다.</div>
<div class="leg"><span>{swatch(C['gray'], 'box')}고를 때 본 샤프 (앞 3년)</span>
<span>{swatch(C['s1'], 'box')}다음 1년 실제 샤프</span><span>{swatch(C['s2'], 'diamond')}같은 1년 그냥 보유</span></div>
{chart_wf()}
<div class="row" style="margin-top:6px">
 <div class="note callout" style="flex:1"><b>해마다 1등 조합이 바뀌었습니다</b><br>{picks}</div>
 <div class="note callout" style="flex:1.3"><b>5년을 이어 붙이면 연 {pct(o['cagr'], sign=True)}, 그냥 보유는 연 {pct(ob['cagr'], sign=True)}</b><br>
 최대 낙폭은 둘 다 {pct(o['mdd'], 0)} 안팎. 백테스트의 "낙폭 절반" 효과가 보지 않은 구간에서는 사라졌습니다.</div>
</div></div>"""
    pb, ds, pm = R["pbo"], R["dsr"], R["perm"]
    mid = f"""
<div class="row">
 <div class="card" style="flex:1.25"><div class="ct">순열 검정: 우연으로도 이만큼 나오나</div>
  <div class="cs">가격 움직임의 순서만 섞은 가짜 시장 {pm['n']:,}개를 만들고, 각각에서 {R['grid']['n']}개 조합을 다시 전부 뒤져 가장 좋은 샤프를 기록했습니다.</div>
  <div style="margin-top:8px">{chart_perm()}</div>
  <div class="note"><b>실제 결과보다 낮았던 가짜 시장이 {pct(float((np.array(pm['perm_max']) < pm['real_max']).mean()))}.</b> 우연히 이만큼 나올 확률 {pct(pm['p'])}로, 기준인 5%를 넘지 못했습니다.</div>
 </div>
 <div style="flex:1;display:flex;flex-direction:column">
  <div class="tile" style="margin-top:14px"><div class="k">PBO (백테스트 과최적화 확률)</div>
   <div class="v">{pct(pb['pbo'])}</div>
   <div class="d">데이터를 반으로 나눠 {pb['splits']:,}가지로 바꿔 보며, 한쪽 1등이 다른 쪽에서 중간도 못 하는 비율. 20% 미만이어야 통과.</div>
   <div style="margin-top:8px">{status(g['G3']['pass'])}</div></div>
  <div class="tile" style="margin-top:10px"><div class="k">디플레이티드 샤프</div>
   <div class="v">{ds['dsr']:.3f}</div>
   <div class="d">{ds['trials']}번 시도한 것을 감안해도 샤프가 0보다 클 확률. <b style="color:{C['t2']}">통과했지만 "돈을 벌었나"이지 "보유보다 나았나"가 아닙니다.</b> 비트코인이 올라 들고만 있어도 0보다는 큽니다.</div>
   <div style="margin-top:8px">{status(g['G4']['pass'])}</div></div>
 </div>
</div>"""
    rows = [
        ("G1", "고른 조합을 다음 해에 썼을 때 벌었나", "샤프 0 초과", f"{g['G1']['value']:+.2f}"),
        ("G2", "그냥 들고 있는 것보다 나았나", f"보유 샤프 {ob['sharpe']:.2f} 초과", f"{o['sharpe']:+.2f}"),
        ("G3", "한쪽 1등이 다른 쪽에서도 버티나", "PBO 20% 미만", pct(pb['pbo'])),
        ("G4", "시도 횟수를 감안해도 0보다 큰가", "0.95 이상", f"{ds['dsr']:.3f}"),
        ("G5", "우연으로 설명되지 않나", "5% 미만", pct(pm['p'])),
    ]
    trs = "".join(f"<tr><td style='color:{C['t3']}'>{k}</td><td>{q}</td><td style='color:{C['t2']}'>{c}</td>"
                  f"<td class='r'>{v}</td><td class='r'>{status(g[k]['pass'])}</td></tr>" for k, q, c, v in rows)
    verdict = "검증 통과" if R["verdict"] else "통과 못함"
    vcol = C["good"] if R["verdict"] else C["bad"]
    table = f"""
<div class="card"><div style="display:flex;justify-content:space-between;align-items:baseline">
 <div class="ct">판정 (기준은 데이터를 받기 전에 고정)</div>
 <div class="verdict" style="color:{vcol}">{'✓' if R['verdict'] else '✕'} {verdict} <span style="font-size:13px;color:{C['t2']};font-weight:600">5개 중 {npass}개 통과</span></div></div>
<table><tr><th></th><th>질문</th><th>기준</th><th style="text-align:right">결과</th><th style="text-align:right">판정</th></tr>{trs}</table></div>"""
    concl = f"""
<div class="card" style="border-color:{C['s1']}">
<div class="concl">이 규칙은 백테스트만 보면 그냥 들고 있는 것보다 수익은 두 배, 낙폭은 절반이었습니다.
그러나 해마다 가장 좋은 조합이 바뀌었고, 전년도 1등을 다음 해에 쓰면 그냥 들고 있는 것보다 못했습니다.
수익이 난 것은 비트코인이 올랐기 때문이며, 이동평균 타이밍이 더한 가치는 확인되지 않았습니다.
<b>이 상태로 자동매매를 만들었다면 제작비를 쓰고, 실전에서 한 번 더 잃었을 것입니다.</b></div></div>"""
    foot = f"""
<div class="foot"><b>사전등록</b> 분석 계획과 판정 기준 다섯 개는 데이터를 받기 전에 고정해 기록했습니다 (2026-09-26 23:36 커밋). 결과를 본 뒤 기준을 바꾸지 않았습니다.<br>
<b>방법</b> 워크포워드 (학습 3년, 검증 1년) &nbsp;|&nbsp; CSCV 기반 PBO, Bailey 외 (2015) &nbsp;|&nbsp; 디플레이티드 샤프, Bailey와 López de Prado (2014) &nbsp;|&nbsp; 몬테카를로 순열 검정 {pm['n']:,}회, 매회 격자 탐색 전체 재수행<br>
<b>시점</b> t일 종가 신호를 t+1일 수익에 적용. 완전예지 신호 대조로 정렬 검증 (샤프 {R['oracle_sharpe']:.1f}) &nbsp;|&nbsp; <b>한계</b> 자산 하나이며 비트코인 자체가 살아남은 자산이라는 생존편향, 비용 고정 가정<br>
예시이며 특정 전략이나 종목을 권하지 않습니다. 과거 결과는 미래를 보장하지 않습니다.</div>"""
    return f"<style>{CSS}</style>{head(2)}{wfc}{mid}{table}{concl}{foot}"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report_1.html").write_text(page1(), encoding="utf-8")
    (OUT / "report_2.html").write_text(page2(), encoding="utf-8")
    print("wrote", OUT / "report_1.html", OUT / "report_2.html")
