# Indian Market Event Detection System

## Project Overview

A market surveillance and event detection system designed to identify
abnormal behavior in Indian equities and distinguish between
stock-level anomalies and broader market events.

The system will eventually combine:

- Stock-level anomaly detection
- Cross-stock correlation breaks
- Market-level event aggregation
- Market stress scoring
- SHAP-based explanations
- Kafka-based historical market replay
- FastAPI backend
- Streamlit dashboard

---

# Development Log

## Day 1 — Data Audit & Understanding

### Objective
Understand the historical NSE dataset and verify that it is clean and
suitable for building the event detection system.

### Dataset

- **Rows:** 235,192
- **Columns:** 15
- **Unique stocks:** 65
- **Date range:** 2000-01-03 → 2021-04-30
- **Trading dates:** 5,306
- **Average stocks per day:** ~44
- **Maximum stocks per day:** 49
- **Minimum stocks per day:** 28
- **Series:** EQ only

### Data Quality Checks

- No duplicate complete rows
- No duplicate `(Date, Symbol)` combinations
- OHLC prices contain no zero/negative values
- VWAP contains no zero/negative values
- Core OHLC and volume fields have no missing values
- `Trades` has significant missing data (~48.83%)
- `Deliverable Volume` has ~6.84% missing values
- `%Deliverble` has ~6.84% missing values

### Important Finding

The dataset contains a **changing historical stock universe** rather than
exactly the same 50 stocks every day.

Therefore, cross-stock analysis must account for stocks entering/leaving
the dataset and should not assume that all 65 symbols existed throughout
the entire period.

### Special Case

One `Prev Close = 0` value was found for:

`BHARTI — 2002-02-18`

This was determined to be legitimate because it corresponds to the
company's first trading day in the dataset. Therefore, it was **not
replaced with a fabricated previous close**.

### Day 1 Status

**Data audit completed ✅**

The dataset is structurally suitable for feature engineering and
subsequent anomaly/event detection.

## Day 2 — Feature Engineering

### Objective
Transform raw market data into features that can capture abnormal
stock behavior.

### Features Created

1. **Return**
   - Measures daily percentage price movement.
   - Calculated separately for each stock using its previous trading day.

2. **Volatility_20**
   - 20-trading-day rolling standard deviation of returns.
   - Captures recent changes in price instability.

3. **Volume_Ratio**
   - Current volume divided by the stock's 20-day average volume.
   - Values above 1 indicate higher-than-usual trading activity.

### Validation

- Extreme returns were inspected rather than removed.
- 1,359 observations had absolute returns greater than 10%.
- These were retained because extreme movements may represent genuine
  market anomalies.
- Initial rolling-window NaN values were expected and retained.

### Day 2 Status

**Core feature engineering completed ✅**

## Day 3 — Stock-Level Anomaly Detection

### Objective
Build the first stock-level anomaly detection layer using Isolation Forest.

### Initial Model
Features:
- Return
- Volatility_20
- Volume_Ratio

A chronological train/test split was created:

- Training: 2000–2015
- Testing: 2016–2021

### Important Data Discovery

Initial Isolation Forest results contained several extreme returns
such as -80% to -90%.

Investigation showed that many of these were **corporate-action artifacts**
rather than genuine market crashes.

Example:

- EICHERMOT, 2020-08-24
- Raw return: approximately -89.97%
- Yahoo adjusted return: approximately +0.29%

The raw NSE price dropped by approximately 10× because of a stock split.

### Decision

Do not remove or manually alter the original NSE records.

Use Yahoo Finance `Adj Close` only for the price-return calculation,
while retaining the original NSE data for volume, VWAP, turnover and
other market features.

### Current Status

**Isolation Forest paused pending adjusted-return integration.**

## Day 4 — Corporate-Action-Aware Anomaly Detection

The initial anomaly model produced several extreme observations caused
by historical stock splits rather than genuine market events.

### Correction

Yahoo Finance adjusted closing prices were used to calculate returns,
while the original NSE dataset was retained for market activity data.

Historical stock split information was also used to normalize volume
onto a comparable share basis before calculating Volume_Ratio.

Final model features:

- Return
- Volatility_20
- Volume_Ratio

### Isolation Forest Results

Using the same model configuration:

- Training period: 2000–2015
- Test period: 2016–2021
- Test observations: 58,186
- Anomalies detected: 253

Validation:

- Anomalies with absolute return > 50%: 0
- Maximum absolute return among anomalies: 44.67%

The corrected model no longer appears dominated by obvious corporate-action
artifacts. The detected anomalies show combinations of significant price
movement, elevated volatility and unusual trading activity.

### Status

**Day 4 complete — corporate-action-aware stock anomaly layer validated.**
## Day 5 — Market-Wide Correlation Break Detection

The second detection layer was developed to identify periods where stocks
move together more strongly than their historical baseline.

### Method

- 48 stocks were used after excluding HDFC due to unavailable adjusted-return history.
- Calculated 60-day rolling pairwise correlations.
- Required at least 40 overlapping observations for each correlation.
- Calculated the average off-diagonal pairwise correlation for each trading day.
- Compared daily correlation against a 252-trading-day trailing baseline.
- The baseline was shifted by one day to prevent future data leakage.

### Correlation Break Score

The score is calculated as the positive z-score of the current average
market correlation relative to its historical baseline.

A higher score indicates unusually strong synchronization across stocks.

### Validation

The detector identified multiple historical periods with unusually high
market-wide correlation.

Examples:

- 2020-03-16: **5.96σ**
- 2020-03-12: **5.83σ**
- 2020-03-23: **5.53σ**
- 2015-08-24: **4.77σ**
- 2015-08-25: **4.23σ**
- 2015-08-27: **4.14σ**

The COVID-19 period produced several consecutive high correlation scores,
while the 2015 period shows that the detector is not limited to a single
historical event.

### Important Note

This layer measures unusually high **market-wide synchronized movement**.
It does not capture every possible type of correlation or relationship
break between individual stocks.

### Status

**Day 5 complete — market-wide correlation detection validated.**
## Day 6 — Market Event Engine

The stock-level anomaly detector and market-wide correlation detector
were combined into a market-level event detection layer.

### Market Signals

The engine combines:

- **Anomaly Breadth** — percentage of stocks showing anomalous behavior.
- **Correlation Break Score** — unusually high market-wide synchronized movement.
- **Directional Anomaly Ratio** — proportion of anomalous stocks moving
  positively or negatively.

### Market Stress Score

The two primary signals were normalized to a 0–100 scale and combined
with equal weighting:

- Anomaly Breadth Score: 0–100
- Correlation Score: 0–100
- Market Stress Score: weighted combination of both signals.

### Event Classification

The engine currently identifies:

- Broad Market Downside Shock
- Broad Market Upside Shock
- Market-Wide Synchronization
- Elevated Market Stress
- Normal

Classification uses market stress, anomaly breadth, correlation strength,
and the directional distribution of anomalous stocks.

### Validation

Across the 2016–2021 evaluation period:

- Normal: **1,213 days**
- Elevated Market Stress: **16 days**
- Market-Wide Synchronization: **6 days**
- Broad Market Upside Shock: **2 days**
- Broad Market Downside Shock: **1 day**

The strongest detected stress period was March–April 2020, where the system
identified sustained increases in both market-wide synchronization and
stock-level abnormal activity.

The highest combined stress score was:

- **2020-03-23 — 53.49**
- Anomaly breadth: **14.89%**
- Correlation score: **92.09**

The system also distinguished between downside and upside abnormal activity.
For example, 2020-03-23 showed predominantly negative anomalies, while
2020-04-07 showed predominantly positive anomalies.

### Limitation

The current event-engine evaluation begins in 2016 because the Isolation
Forest test period begins in 2016. Therefore, historical periods such as
the 2008 financial crisis have not yet been evaluated by the complete event
engine.

### Status

**Day 6 complete — market-level event engine implemented and validated
on the 2016–2021 evaluation period.**

## Day 7 — Historical Backtesting

The complete event detection pipeline was backtested on historical market
periods outside the original 2016–2021 evaluation window.

### 2008–2009 Backtest

The existing Isolation Forest model was applied to 2008–2009 without
retraining specifically on this period.

The period contained:

- 489 trading days
- ~46.6 stocks per day on average
- 44–47 stocks per day

### October 2008 Validation

The correlation detector was recalculated using the full historical
correlation series so that the 252-day baseline did not restart at
January 2008.

The system identified elevated market-wide synchronization during the
October 2008 turmoil.

The strongest combined event was:

- **Date:** 2008-10-24
- **Anomalous stocks:** 10 / 45
- **Anomaly breadth:** 22.22%
- **Correlation break:** 1.47σ
- **Correlation score:** 24.51 / 100
- **Market Stress Score:** 23.37 / 100
- **Negative anomalies:** 10
- **Positive anomalies:** 0
- **Mean anomalous return:** −13.07%

This indicates that the stock-level and market-wide signals aligned during
the period, with all detected anomalies moving negatively.

### 2009 Validation

The system also detected a strong positive market-wide event on:

**2009-05-18**

- **Anomalous stocks:** 27 / 42
- **Anomaly breadth:** 64.29%
- **Correlation break:** 1.38σ
- **Correlation score:** 23.03 / 100
- **Market Stress Score:** 43.66 / 100
- **Positive anomalies:** 27
- **Negative anomalies:** 0
- **Mean anomalous return:** +17.44%

This demonstrates that the event engine is not limited to detecting
downside events. It can identify unusually strong positive market behavior
as well.

### Comparison with 2020

The historical backtest showed different signal structures across major
market periods.

**2008-10-24**
- Higher stock-level anomaly breadth
- Moderate correlation deviation
- 100% negative anomalies

**2020-03-23**
- 14.89% anomaly breadth
- 5.53σ correlation break
- 100% negative anomalies
- Market Stress Score: **53.49**

The results show that market events can be characterized by different
combinations of stock-level abnormal activity and market-wide
synchronization.

### Important Limitation

The backtest demonstrates that the system identifies unusual historical
market behavior. It does **not** establish that the system could have
predicted these events in advance.

### Status

**Day 7 complete — historical backtesting performed on 2008–2009 and
validated against the 2020 stress period.**