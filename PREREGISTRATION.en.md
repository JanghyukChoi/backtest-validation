# Preregistration: sample validation report (English translation)

*Translation of `PREREGISTRATION.md`. The Korean file is the binding version and was committed before the data was downloaded.*

**Written and committed before the data was downloaded.** The commit time of this file precedes the analysis run.
Whatever the outcome, it is judged by the criteria below, and the criteria are not changed afterwards.
If the verdict is unfavourable it is published as it is.

## Purpose
A **sample validation report** to put on a freelance-marketplace product page (Kmong, a Korean marketplace). It does not recommend a
strategy. Its purpose is to show with real numbers that "the backtest looks good" and "the result can be trusted" are different things.

## Data
- Binance BTC/USDT spot **daily close**, public API (`/api/v3/klines`)
- Period: from the listing date (2017-08-17) to the last completed bar available
- Raw data is not placed in the repository (assumed not redistributable). Only processed results are used.

## Rule (textbook example, not a recommendation)
If the short simple moving average is above the long one, **hold**; otherwise cash. No shorting.

## Timing convention (blocking future information)
- The signal is computed from day t's close and **applied to day t+1's return** (`pos[t] = sig[t-1]`).
- Pre-check: a perfect-foresight signal (`sig[t-1] = ret[t] > 0`) must give a very large Sharpe.
  If not, treat it as an alignment error and **stop the analysis**.
- Contrast demo: the result of a wrong alignment that uses the same day's close for both signal and return
  (`pos[t] = sig[t]`) is shown separately. It is not used in the verdict.

## Search grid
- Short: 5, 10, 15, 20, 25, 30, 40, 50
- Long: 20, 30, 40, 50, 60, 80, 100, 120, 150, 200
- Only pairs with short < long. The number of trials N follows from this grid.

## Costs
**15 bp** per side (exchange taker fee 10 bp plus slippage 5 bp), charged on position changes.

## Metrics
365-day year. Sharpe = daily mean / daily standard deviation x sqrt(365), risk-free rate 0. Max drawdown, number of trades, exposure.

## Tests
1. **Full-period optimum**: the pair with the highest Sharpe at zero cost. This is the "good-looking number".
2. **Walk-forward**: 3 years training (1,095 days), 1 year test (365 days), rolled by 1 year. Pick the pair with
   the best cost-adjusted training Sharpe and apply it to the next year. Chain only the test-window returns.
3. **CSCV / PBO** (Bailey, Borwein, Lopez de Prado, Zhu 2015): split the evaluation period into 16 contiguous blocks and use all
   8/8 splits (12,870). PBO is the share where the in-sample best pair has a relative-rank logit <= 0 out of sample.
   Cost-adjusted returns.
4. **Deflated Sharpe** (Bailey, Lopez de Prado 2014): for the cost-adjusted best pair over the full period, the probability that the
   "true Sharpe > 0", corrected for the number of trials N, the variance of Sharpes across pairs, skewness and kurtosis.
5. **Monte Carlo permutation test** (Masters): shuffle the order of daily log returns to build a new price path and
   **repeat the whole grid search**, recording the best Sharpe. 1,000 shuffles, seed 20260926.
   p = (1 + number of shuffles whose best >= the real best) / 1001. Cost-adjusted.

## Verdict criteria (fixed)
| | Criterion |
|---|---|
| G1 | Walk-forward test-window Sharpe (cost-adjusted) > 0 |
| G2 | Walk-forward test-window Sharpe > buy-and-hold Sharpe over the same windows |
| G3 | PBO < 0.20 |
| G4 | Deflated Sharpe >= 0.95 |
| G5 | Permutation p < 0.05 |

**All five must pass to be "validated".** If any fails, the failed item is reported as it is.

## Known limits (written before the result)
- One asset. That Bitcoin survived is itself survivorship bias.
- The permutation test also breaks volatility clustering. The null hypothesis is "the timing has no value".
- Costs are a fixed assumption. Real fills depend on size and timing.
