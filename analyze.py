"""크몽 샘플 검증 리포트 — PREREGISTRATION.md 를 그대로 실행한다.

**여기서 기준을 바꾸지 않는다.** 격자, 비용, 분할, 문턱은 전부 사전등록 파일과 같다.
바꿔야 할 이유가 생기면 사전등록을 새로 쓰고 새로 커밋한 뒤 다시 돌린다.

    python analyze.py <원본 저장 경로.json>

원본(바이낸스 일봉)은 저장소 밖에 둔다. 재배포 금지 전제라서다.
결과는 이 폴더의 results.json 으로만 나간다(가공값만).
"""
from __future__ import annotations

import itertools
import json
import math
import sys
import time
import urllib.request
from pathlib import Path
from statistics import NormalDist

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "_raw.json"

ANN = 365
COST = 15 / 1e4                     # 편도 15bp
FAST = [5, 10, 15, 20, 25, 30, 40, 50]
SLOW = [20, 30, 40, 50, 60, 80, 100, 120, 150, 200]
GRID = [(f, s) for f in FAST for s in SLOW if f < s]
WARM = max(SLOW)                    # 모든 조합이 정의되는 첫 날부터 평가
TRAIN, TEST = 1095, 365
BLOCKS = 16
NPERM, SEED = 1000, 20260926
GATES = {"G3_pbo": 0.20, "G4_dsr": 0.95, "G5_p": 0.05}
N = NormalDist()


# ── 데이터 ──────────────────────────────────────────────────────────────
def fetch() -> list:
    rows, start = [], 1502928000000          # 2017-08-17 00:00 UTC
    while True:
        url = ("https://api.binance.com/api/v3/klines?symbol=BTCUSDT"
               f"&interval=1d&startTime={start}&limit=1000")
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.load(r)
        if not d:
            break
        rows += d
        start = d[-1][0] + 86_400_000
        if len(d) < 1000:
            break
        time.sleep(0.3)
    return rows


def load():
    if not RAW.exists():
        RAW.write_text(json.dumps(fetch()))
    rows = json.loads(RAW.read_text())
    now = int(time.time() * 1000)
    rows = [r for r in rows if r[6] < now]    # 아직 안 끝난 봉은 버린다
    dates = np.array([time.strftime("%Y-%m-%d", time.gmtime(r[0] / 1000)) for r in rows])
    close = np.array([float(r[4]) for r in rows])
    return dates, close


# ── 엔진 ────────────────────────────────────────────────────────────────
def sma(x, w):
    c = np.cumsum(np.insert(x, 0, 0.0))
    out = np.full(len(x), np.nan)
    out[w - 1:] = (c[w:] - c[:-w]) / w
    return out


def simple_ret(close):
    r = np.full(len(close), np.nan)
    r[1:] = close[1:] / close[:-1] - 1
    return r


def run_grid(close, cost, same_bar=False):
    """조합별 일간 순수익 행렬 (n × len(GRID)) 과 포지션 행렬.

    pos[t] = sig[t-1] — t일 종가로 만든 신호는 t+1일 수익에만 쓴다.
    same_bar=True 는 대조 시연용 잘못된 정렬이다(판정에 안 쓴다).
    """
    ret = simple_ret(close)
    ws = sorted(set(FAST) | set(SLOW))
    m = {w: sma(close, w) for w in ws}
    n = len(close)
    R = np.empty((n, len(GRID)))
    P = np.empty((n, len(GRID)))
    for j, (f, s) in enumerate(GRID):
        with np.errstate(invalid="ignore"):
            sig = (m[f] > m[s]).astype(float)   # NaN 비교는 False = 현금
        pos = sig if same_bar else np.concatenate([[0.0], sig[:-1]])
        turn = np.abs(np.diff(pos, prepend=0.0))
        R[:, j] = pos * ret - turn * cost
        P[:, j] = pos
    return R, P, ret


def sharpe(x, axis=0):
    x = np.asarray(x, float)
    sd = x.std(axis=axis, ddof=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return x.mean(axis=axis) / sd * math.sqrt(ANN)


def metrics(r, pos=None):
    r = np.asarray(r, float)
    eq = np.cumprod(1 + r)
    peak = np.maximum.accumulate(eq)
    out = {
        "cagr": float(eq[-1] ** (ANN / len(r)) - 1),
        "vol": float(r.std(ddof=1) * math.sqrt(ANN)),
        "sharpe": float(sharpe(r)),
        "mdd": float((eq / peak - 1).min()),
        "days": int(len(r)),
    }
    if pos is not None:
        pos = np.asarray(pos, float)
        out["entries"] = int(((pos[1:] > 0) & (pos[:-1] == 0)).sum())
        out["exposure"] = float(pos.mean())
    return out


# ── 검정 ────────────────────────────────────────────────────────────────
def walk_forward(Rnet, bh):
    folds, oos, oos_bh = [], [], []
    k = 0
    while True:
        a = WARM + k * TEST
        b, c = a + TRAIN, a + TRAIN + TEST
        if c > len(Rnet):
            break
        tr = sharpe(Rnet[a:b])
        j = int(np.nanargmax(tr))
        te = Rnet[b:c, j]
        folds.append({"train": [a, b], "test": [b, c], "pick": GRID[j],
                      "is_sharpe": float(tr[j]), "oos_sharpe": float(sharpe(te)),
                      "bh_sharpe": float(sharpe(bh[b:c]))})
        oos.append(te)
        oos_bh.append(bh[b:c])
        k += 1
    oos, oos_bh = np.concatenate(oos), np.concatenate(oos_bh)
    return folds, oos, oos_bh


def cscv_pbo(M):
    T = (len(M) // BLOCKS) * BLOCKS
    M = M[len(M) - T:]                          # 앞쪽 나머지를 버린다
    L = T // BLOCKS
    S = np.stack([M[i * L:(i + 1) * L].sum(0) for i in range(BLOCKS)])
    Q = np.stack([(M[i * L:(i + 1) * L] ** 2).sum(0) for i in range(BLOCKS)])

    def sr(idx):
        c = L * len(idx)
        s, q = S[list(idx)].sum(0), Q[list(idx)].sum(0)
        var = (q - s * s / c) / (c - 1)
        return (s / c) / np.sqrt(var)

    logits, is_best, oos_of_best = [], [], []
    for isb in itertools.combinations(range(BLOCKS), BLOCKS // 2):
        osb = tuple(i for i in range(BLOCKS) if i not in isb)
        a, b = sr(isb), sr(osb)
        j = int(np.nanargmax(a))
        rank = 1 + int((b < b[j]).sum())       # 오름차순 순위
        w = rank / (len(b) + 1)
        logits.append(math.log(w / (1 - w)))
        is_best.append(float(a[j] * math.sqrt(ANN)))
        oos_of_best.append(float(b[j] * math.sqrt(ANN)))
    logits = np.array(logits)
    return {"pbo": float((logits <= 0).mean()), "splits": len(logits),
            "logits": logits.tolist(), "is_best": is_best, "oos_of_best": oos_of_best}


def deflated_sharpe(Rnet_eval):
    sr_all = Rnet_eval.mean(0) / Rnet_eval.std(0, ddof=1)     # 일 단위
    j = int(np.nanargmax(sr_all))
    x = Rnet_eval[:, j]
    T = len(x)
    sr = float(sr_all[j])
    z = (x - x.mean()) / x.std(ddof=0)
    g3, g4 = float((z ** 3).mean()), float((z ** 4).mean())
    Nt = len(GRID)
    v = float(np.nanvar(sr_all, ddof=1))
    em = 0.5772156649015329
    sr0 = math.sqrt(v) * ((1 - em) * N.inv_cdf(1 - 1 / Nt) + em * N.inv_cdf(1 - 1 / (Nt * math.e)))
    denom = math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr * sr)
    dsr = N.cdf((sr - sr0) * math.sqrt(T - 1) / denom)
    return {"pick": GRID[j], "sr_ann": sr * math.sqrt(ANN), "sr0_ann": sr0 * math.sqrt(ANN),
            "trials": Nt, "skew": g3, "kurt": g4, "T": T, "dsr": float(dsr)}


def permutation(close, real_max):
    rng = np.random.default_rng(SEED)
    lr = np.log(close[1:] / close[:-1])
    best = np.empty(NPERM)
    for i in range(NPERM):
        path = close[0] * np.exp(np.concatenate([[0.0], np.cumsum(rng.permutation(lr))]))
        R, _, _ = run_grid(path, COST)
        best[i] = np.nanmax(sharpe(R[WARM:]))
    p = (1 + int((best >= real_max).sum())) / (1 + NPERM)
    return {"n": NPERM, "seed": SEED, "real_max": float(real_max), "p": float(p),
            "perm_max": best.tolist(),
            "perm_q": {q: float(np.quantile(best, q)) for q in (0.5, 0.9, 0.95, 0.99)}}


# ── 실행 ────────────────────────────────────────────────────────────────
def main():
    dates, close = load()
    print(f"데이터 {dates[0]} ~ {dates[-1]}, {len(close)}일, 조합 {len(GRID)}개")

    R0, P0, ret = run_grid(close, 0.0)
    Rc, _, _ = run_grid(close, COST)
    E = slice(WARM, len(close))
    bh = np.nan_to_num(ret)

    # 선행 점검: 완전예지 신호가 큰 샤프를 내야 정렬이 맞다
    oracle_pos = np.concatenate([[0.0], (ret[1:] > 0).astype(float)])
    oracle_sr = float(sharpe((oracle_pos * np.nan_to_num(ret))[E]))
    if not oracle_sr > 5:
        sys.exit(f"시점 자기검증 실패: 완전예지 샤프 {oracle_sr:.2f}. 분석 중단")
    print(f"시점 자기검증 통과: 완전예지 샤프 {oracle_sr:.1f}")

    sr0 = sharpe(R0[E])
    src = sharpe(Rc[E])
    jb = int(np.nanargmax(sr0))
    best = GRID[jb]

    Rsb, _, _ = run_grid(close, 0.0, same_bar=True)
    look = {"right": float(sr0[jb]), "same_bar": float(sharpe(Rsb[E, jb]))}

    heat0 = {f"{f}/{s}": float(sr0[j]) for j, (f, s) in enumerate(GRID)}
    heatc = {f"{f}/{s}": float(src[j]) for j, (f, s) in enumerate(GRID)}

    folds, oos, oos_bh = walk_forward(Rc, bh)
    wf = {"folds": folds, "oos": metrics(oos), "oos_bh": metrics(oos_bh)}

    pbo = cscv_pbo(Rc[E])
    dsr = deflated_sharpe(Rc[E])
    print("순열 검정 중 (1,000회, 격자 전체 재탐색)...")
    t0 = time.time()
    perm = permutation(close, float(np.nanmax(src)))
    print(f"  {time.time() - t0:.0f}초")

    gates = {
        "G1": {"label": "워크포워드 검증 구간 샤프 > 0",
               "value": wf["oos"]["sharpe"], "pass": wf["oos"]["sharpe"] > 0},
        "G2": {"label": "워크포워드 샤프 > 같은 구간 그냥 보유",
               "value": wf["oos"]["sharpe"] - wf["oos_bh"]["sharpe"],
               "pass": wf["oos"]["sharpe"] > wf["oos_bh"]["sharpe"]},
        "G3": {"label": "PBO < 0.20", "value": pbo["pbo"], "pass": pbo["pbo"] < GATES["G3_pbo"]},
        "G4": {"label": "디플레이티드 샤프 ≥ 0.95", "value": dsr["dsr"], "pass": dsr["dsr"] >= GATES["G4_dsr"]},
        "G5": {"label": "순열 검정 p < 0.05", "value": perm["p"], "pass": perm["p"] < GATES["G5_p"]},
    }
    verdict = all(g["pass"] for g in gates.values())

    step = 7
    eq = lambda r: np.cumprod(1 + r)[::step].tolist()
    out = {
        "data": {"first": str(dates[E][0]), "last": str(dates[-1]), "days": int(len(close) - WARM),
                 "source": "Binance BTCUSDT 1d close (public API)"},
        "grid": {"fast": FAST, "slow": SLOW, "n": len(GRID)},
        "cost_bp_per_side": COST * 1e4,
        "oracle_sharpe": oracle_sr,
        "best_cost0": {"pick": best,
                       "cost0": metrics(R0[E, jb], P0[E, jb]),
                       "cost15": metrics(Rc[E, jb], P0[E, jb])},
        "buy_hold": metrics(bh[E]),
        "lookahead": look,
        "heat_cost0": heat0, "heat_cost15": heatc,
        "equity": {"dates": dates[E][::step].tolist(),
                   "best_cost0": eq(R0[E, jb]), "best_cost15": eq(Rc[E, jb]), "buy_hold": eq(bh[E])},
        "walk_forward": wf,
        "pbo": pbo, "dsr": dsr, "perm": perm,
        "gates": gates, "verdict": verdict,
    }
    (HERE / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

    b0, bc, bhm = out["best_cost0"]["cost0"], out["best_cost0"]["cost15"], out["buy_hold"]
    print(f"\n전체기간 최적(비용 0): {best}  샤프 {b0['sharpe']:.2f}  연 {b0['cagr']:.1%}  MDD {b0['mdd']:.1%}  진입 {b0['entries']}회")
    print(f"  같은 조합 비용 반영: 샤프 {bc['sharpe']:.2f}  연 {bc['cagr']:.1%}")
    print(f"  그냥 보유:          샤프 {bhm['sharpe']:.2f}  연 {bhm['cagr']:.1%}  MDD {bhm['mdd']:.1%}")
    print(f"  잘못된 정렬 시연:    샤프 {look['same_bar']:.2f} (올바른 정렬 {look['right']:.2f})")
    print(f"워크포워드 {len(folds)}개 구간: 검증 샤프 {wf['oos']['sharpe']:.2f} vs 보유 {wf['oos_bh']['sharpe']:.2f}")
    for f in folds:
        print(f"   {dates[f['test'][0]]}~  pick {f['pick']}  IS {f['is_sharpe']:.2f}  OOS {f['oos_sharpe']:.2f}  보유 {f['bh_sharpe']:.2f}")
    print(f"PBO {pbo['pbo']:.3f} ({pbo['splits']}분할)")
    print(f"DSR {dsr['dsr']:.3f}  (최적 {dsr['pick']} 샤프 {dsr['sr_ann']:.2f}, 기대최대 {dsr['sr0_ann']:.2f}, N={dsr['trials']})")
    print(f"순열 p {perm['p']:.4f}  (실제 최대 {perm['real_max']:.2f}, 섞은 쪽 95% {perm['perm_q'][0.95]:.2f})")
    print("\n판정:", "검증 통과" if verdict else "통과 못함")
    for k, g in gates.items():
        print(f"  {k} {'✅' if g['pass'] else '❌'} {g['label']}  ({g['value']:.3f})")


if __name__ == "__main__":
    main()
