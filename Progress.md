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