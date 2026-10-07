# Backtest validation, preregistered

A worked example of how a backtest that looks good can fail honest checks.

A moving-average crossover on Bitcoin looks clearly better than buy-and-hold when you pick the best
parameters on the full history. This repository runs that strategy through five fixed gates, with the
rules **committed before the data was downloaded**, and publishes the result even though it does not pass.

- Data: Binance BTCUSDT daily close, public API, 2018-03-05 to 2026-09-25 (3,127 days)
- Rule: long when the short SMA is above the long SMA, otherwise cash. No shorting.
- Search grid: 69 (short, long) pairs. Cost: 15 bp per side.
- Everything below is computed by `analyze.py` from the preregistration, with no criteria changed afterwards.

## The result in one table

| What it looks like | Value |
|---|---|
| Best pair in the full history (cost-free search) | SMA(5, 100) |
| Its Sharpe, after 15 bp costs | **1.16** |
| Buy and hold, same period | 0.69 |

| Gate (fixed in advance) | Result | Pass |
|---|---|---|
| G1 Walk-forward out-of-sample Sharpe > 0 (5 test years, 1,825 days; CAGR -9.0%) | -0.05 | no |
| G2 Walk-forward Sharpe > buy and hold over the same windows (buy and hold: 0.39) | -0.44 (difference) | no |
| G3 Probability of backtest overfitting (CSCV) < 0.20 | 0.435 | no |
| G4 Deflated Sharpe ratio >= 0.95 | 0.996 | yes |
| G5 Monte Carlo permutation p-value < 0.05 | 0.077 | no |

**Verdict: not validated (1 of 5).** The preregistration says all five must pass.

How to read it: the in-sample Sharpe of 1.16 is the number a sales page would show. Chosen in-sample, it
does not carry out of sample, and the chance that the in-sample winner ranks below median out of sample
is 43%. The deflated Sharpe passes, which says the Sharpe is unlikely to be zero given 69 trials. The permutation test
asks a stricter question (does the timing rule beat shuffled price paths when the whole grid search is
repeated each time?) and the answer is "not clearly" (p = 0.077). Both facts are reported.

Sanity checks built in: a perfect-foresight signal must give a huge Sharpe (it gives 10.6), and a deliberately
mis-aligned signal that uses the same day's close shows how look-ahead inflates results (cost-free Sharpe 1.37 vs 1.18
for the correct alignment). The correct alignment is `pos[t] = signal[t-1]`.

## Methods

- Walk-forward: 3-year training window, 1-year test window, rolled yearly; only test-window returns are chained.
- CSCV / PBO: Bailey, Borwein, Lopez de Prado, Zhu (2015). 16 contiguous blocks, all 12,870 half/half splits.
- Deflated Sharpe: Bailey and Lopez de Prado (2014), using the number of trials, the variance of Sharpes across
  trials, skewness and kurtosis.
- Monte Carlo permutation (Masters): shuffle daily log returns, **repeat the whole grid search**, record the
  best Sharpe. 1,000 shuffles, seed 20260926.

## Integrity

`PREREGISTRATION.md` (Korean original) was committed at 2026-09-26 23:36 KST. The analysis result was committed at
23:47 KST. An English translation is in `PREREGISTRATION.en.md`; the Korean file is the binding one.
The commit hashes were rewritten once to replace the author email with a GitHub noreply address. Commit dates were kept.

## Run it

```bash
pip install numpy
python analyze.py            # downloads public data to _raw.json (not committed), writes results.json
python render_report.py      # builds two HTML report pages from results.json (optional)
```

Re-running today downloads a longer history than the committed run, so the numbers will differ somewhat from the
table above. `results.json` is the output of the committed run and is kept for reference. The raw price file is
not included.

## Limits (written before the result, still true)

- One asset. That Bitcoin survived to be studied is itself survivorship bias.
- The permutation null also destroys volatility clustering; its null is "the timing has no value".
- Costs are a fixed assumption. Real fills depend on size and timing.
- This is an illustration of validation practice, not a trading recommendation.

## License

MIT
