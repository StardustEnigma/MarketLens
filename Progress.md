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

## Day 8 — Feature Enrichment & SHAP Explainability

### Feature Enrichment

Added two additional features to provide more context around stock-level anomalies:

* `VWAP_Deviation` — measures the deviation of the closing price from the daily VWAP.
* `Turnover_Ratio` — measures current turnover relative to the stock's 20-day rolling average turnover.

Both features were validated using their distributions and extreme observations. No extreme values were removed because unusual market behavior is relevant to the detection task.

### 3-Feature vs 5-Feature Experiment

The original Isolation Forest used:

```text
Return
Volatility_20
Volume_Ratio
```

A controlled experiment was performed by adding the two new features:

```text
Return
Volatility_20
Volume_Ratio
VWAP_Deviation
Turnover_Ratio
```

Both models used the same Isolation Forest configuration:

```text
n_estimators = 200
contamination = 0.01
random_state = 42
```

and the same temporal split:

```text
Training: 2000–2015
Testing: 2016–2021
```

### Results

| Model     | Test Anomalies |
| --------- | -------------: |
| 3-Feature |            252 |
| 5-Feature |            313 |

The additional features significantly changed the behavior of the anomaly detector.

A historical comparison on **2009-05-18** showed:

| Model     | Anomalies | Breadth |
| --------- | --------: | ------: |
| 3-Feature |   27 / 42 |   64.3% |
| 5-Feature |    3 / 42 |    7.1% |

The 3-feature model captured the broad abnormal price movement across the stocks, while the 5-feature model suppressed most of these observations because many of the stocks had relatively low trading activity compared with their 20-day averages.

### Modeling Decision

The experiment showed that `VWAP_Deviation` and `Turnover_Ratio` contain useful information, but directly adding them to the Isolation Forest substantially changes what the detector considers anomalous.

Therefore, the **3-feature model was retained as the primary stock-level anomaly detector**:

```text
Return
Volatility_20
Volume_Ratio
        ↓
Isolation Forest
        ↓
Stock Anomaly
```

`VWAP_Deviation` and `Turnover_Ratio` are retained as **contextual signals** for later analysis and the Market Event Engine rather than being used as primary Isolation Forest inputs.

This separates:

* **Detection** — identifying unusual stock behavior.
* **Context** — describing the trading conditions surrounding the anomaly.

### SHAP Explainability

Added SHAP (`v0.52.0`) to explain why individual observations were classified as anomalous by the Isolation Forest.

Used:

```
explainer = shap.TreeExplainer(model)
```

Two representative anomalies were analyzed.

#### SBIN — 2017-10-25

```text
Return          +27.69%
Volatility_20     6.39%
Volume_Ratio     10.38×
```

SHAP contributions:

```text
Volume_Ratio     -4.507
Return           -3.065
Volatility_20    -2.107
```

`Volume_Ratio` was the strongest contributor, followed by `Return` and `Volatility_20`.

#### INDUSINDBK — 2020-03-18

```text
Return          -23.73%
Volatility_20     6.82%
Volume_Ratio      5.09×
```

SHAP contributions:

```text
Volume_Ratio     -3.531
Return           -2.883
Volatility_20    -2.554
```

Again, `Volume_Ratio` was the strongest contributor.

Both positive and negative stock anomalies were successfully explained using SHAP, and force plots were generated for both examples.

### Day 8 Outcome

* Added `VWAP_Deviation`.
* Added `Turnover_Ratio`.
* Validated both new features.
* Performed a controlled 3-feature vs 5-feature Isolation Forest experiment.
* Retained the 3-feature model as the primary anomaly detector.
* Retained VWAP deviation and turnover ratio as contextual signals.
* Added SHAP explainability using `TreeExplainer`.
* Explained both an upside anomaly (`SBIN`) and a downside anomaly (`INDUSINDBK`).
* Generated SHAP force plots for both examples.

**Status: Day 8 complete.**

# Day 9 — Kafka + Real-Time Replay + FastAPI Preparation 🟡

## Kafka Setup

Docker was selected for running Kafka locally.

Installed/verified:

```text
Docker: 29.2.1
Docker Compose: v5.0.2
kafka-python: 3.0.11
```

Kafka configuration:

```text
Broker: localhost:9092
Topic: market-events
Partitions: 3
```

Kafka is used to **replay historical market observations as a live stream** rather than simply acting as a storage layer.

This allows the project to demonstrate a real-time processing architecture using historical NSE data.

---

## Market Streaming Dataset

Created:

```text
Dataset/market_stream.csv
```

Contains:

```text
Date
CanonicalSymbol
Return
Volatility_20
Volume_Ratio
```

Final stream dataset:

```text
189,853 observations
```

The stream is sorted by:

```text
Date → CanonicalSymbol
```

---

## Kafka Producer

Created a configurable producer capable of replaying historical observations:

```bash
python producer.py --limit 100 --delay 0.01
```

The producer converts each market observation into a JSON event:

```json
{
    "date": "...",
    "symbol": "...",
    "return": "...",
    "volatility_20": "...",
    "volume_ratio": "..."
}
```

Messages are published to:

```text
market-events
```

Producer/consumer communication was successfully tested.

---

## Kafka + Isolation Forest

The saved Isolation Forest model:

```text
models/isolation_forest.joblib
```

was loaded directly by the Kafka consumer.

The consumer:

1. Receives a market observation.
2. Extracts the three model features.
3. Runs `model.predict()`.
4. Calculates the anomaly score.
5. Identifies anomalous stocks.

A known test anomaly:

```text
Date: 2016-05-04
Symbol: ADANIPORTS

Return:        -0.115711
Volatility_20:  0.036622
Volume_Ratio:  4.831902
```

The Kafka consumer correctly identified it as an anomaly.

---

## Daily Kafka Replay

A controlled replay of:

```text
2019-11-01 → 2020-03-23
```

produced:

```text
3,713 market observations
79 trading dates
47 stocks
```

The consumer reconstructed a daily return matrix:

```text
79 trading dates × 47 stocks
```

This was then used to calculate rolling market correlation during the replay.

---

## Streaming Correlation

The Kafka replay successfully reproduced the increase in market-wide correlation during March 2020.

Examples:

```text
2020-03-09  correlation ≈ 0.3277
2020-03-11  correlation ≈ 0.3212
2020-03-12  correlation ≈ 0.5120
2020-03-13  correlation ≈ 0.5042
2020-03-16  correlation ≈ 0.5665
2020-03-17  correlation ≈ 0.5542
2020-03-18  correlation ≈ 0.5463
2020-03-19  correlation ≈ 0.5338
2020-03-20  correlation ≈ 0.5598
2020-03-23  correlation ≈ 0.6358
```

The streaming correlation values are not expected to exactly match the offline values because the replay uses a shorter historical window and a smaller stock universe.

This distinction is important:

```text
Offline model
→ validated 252-day historical baseline

Streaming demo
→ shorter replay baseline
```

The streaming implementation demonstrates the architecture rather than reproducing the offline score exactly.

---
### Day 9 Outcome

* Built the Kafka-based streaming pipeline for historical market data.
* Created the `market-events` Kafka topic with 3 partitions.
* Streamed historical observations through Kafka using `producer/test_day.py`.
* Verified that the producer successfully streamed **3,713 observations**.
* Built and tested a raw Kafka consumer to verify that market events were actually being received.
* Implemented market-wide data collection by grouping incoming Kafka events by trading date and stock symbol.
* Built the return matrix containing **79 trading dates × 47 stocks**.
* Implemented rolling market correlation across stocks.
* Added correlation z-scores to measure how unusual the current market-wide synchronization was compared with the historical correlation baseline.
* Observed correlation increasing significantly during the March 2020 market stress period:

  * `2020-03-09` → correlation `0.3277`, z-score `5.00`
  * `2020-03-12` → correlation `0.5120`, z-score `5.62`
  * `2020-03-23` → correlation `0.6358`, z-score `1.83`
* Fixed a pandas error caused by using `pd.isclose` instead of the NumPy equivalent.
* Built the initial `market_event_engine.py`.
* Combined anomaly breadth with correlation z-score to create a **Market Stress Score**.
* Added event classification based on the combined market signals.
* Event categories currently include:

  * `Normal`
  * `Elevated Market Stress`
  * `Market-Wide Synchronization`
  * `Broad Market Downside Shock`
* Combined the anomaly detector output with the market correlation results.
* Created `Dataset/market_events.csv` containing the generated market-event dataset.
* Generated **15 market-event records** from the available event window.
* Built `event_explanations.py` to explain detected anomalies using SHAP.
* Added event-level explanations showing:

  * stock return
  * 20-day volatility
  * volume ratio
  * SHAP contribution of each feature
* Tested the explanation pipeline on the `2020-03-23` event.
* Detected **7 anomalies** on `2020-03-23`.
* The strongest anomaly explanations were primarily driven by highly negative returns and elevated volatility.
* Example:

  * `AXISBANK` → Return `-27.91%`, Volume Ratio `2.04`
  * `BAJAJFINSV` → Return `-25.86%`, Volume Ratio `1.50`
  * `BAJFINANCE` → Return `-23.23%`, Volume Ratio `1.43`
* Successfully integrated the individual-stock anomaly layer with the market-wide correlation layer.
* The project has now moved from simply detecting unusual stocks to detecting and explaining **market-level events**.

### Current Architecture

The project currently follows this pipeline:

`Historical Market Data`
→ `Feature Engineering`
→ `Isolation Forest`
→ `Stock-Level Anomaly Detection`
→ `Kafka Producer`
→ `Kafka Topic`
→ `Kafka Consumers`
→ `Market Correlation`
→ `Correlation Z-Score`
→ `Market Stress Score`
→ `Event Classification`
→ `SHAP Event Explanation`
→ `market_events.csv`

### Important Components

**1. Stock-Level Anomaly Detector**

Uses the primary 3-feature Isolation Forest model:

* Return
* Volatility_20
* Volume_Ratio

Additional features such as `VWAP_Deviation` and `Turnover_Ratio` are retained as contextual signals.

**2. Kafka Streaming Layer**

Kafka is being used to simulate a real-time market-event stream from historical data.

Topic:

`market-events`

Configuration:

* Partitions: `3`
* Replication factor: `1`

The producer streams historical observations while consumers process the events independently.

**3. Market Correlation Layer**

For every trading date, stock returns are collected into a matrix:

`(trading_dates × stocks)`

Current validated matrix:

`(79, 47)`

Rolling cross-sectional correlation is then calculated to detect periods where stocks begin moving together unusually strongly.

**4. Market Stress Score**

The current score combines:

* Anomaly breadth
* Correlation z-score

This creates a higher-level signal instead of relying on individual stock anomalies alone.

**5. Event Classification**

The event engine converts numerical signals into interpretable market events.

This is the first layer that attempts to answer:

> "What is happening across the market?"

rather than only:

> "Which stocks look unusual?"

**6. SHAP Explanation Layer**

SHAP is used to explain why individual stocks were classified as anomalies.

For the `2020-03-23` event, the explanations showed that negative returns and high volatility were the major contributors for most detected anomalies.

### Current Output

The system successfully produces:

```text
Combined event data
        ↓
Market Stress Score
        ↓
Event Type
        ↓
Affected Stocks
        ↓
SHAP Feature Contributions
```

Example:

```text
Event date: 2020-03-23
Anomalies found: 7

AXISBANK | Return=-0.2791 | Volume_Ratio=2.04
Return         → SHAP contribution: -3.6589
Volatility_20  → SHAP contribution: -3.4578
Volume_Ratio   → SHAP contribution: -0.9363
```

### Day 9 Status

**Status: Day 9 complete.**

The project now has a complete prototype for:

**streaming → detection → market-wide analysis → event generation → explainability.**

The next phase should focus on making the event engine more robust and closer to a real-time market monitoring system rather than continuing to add isolated features.

### Day 10 — Event Intelligence Layer

**Status: Day 10 complete.**

The market event pipeline was extended from basic event detection into a more structured event intelligence layer.

#### 1. Market Event Dataset

The event engine now generates and saves:

* `Date`
* `Stocks`
* `Anomalies`
* `Anomaly_Breadth`
* `Negative_Anomalies`
* `Positive_Anomalies`
* `Rolling_Correlation`
* `Correlation_Z`
* `Market_Stress_Score`
* `Severity`
* `Event_Type`
* `Event_Duration`

The resulting dataset is stored at:

`Dataset/market_events.csv`

A total of **15 market events** were generated from the current historical test window.

#### 2. Market Stress Score

A combined market stress score was created using:

* Anomaly breadth
* Cross-stock correlation
* Correlation Z-score

This provides a single numerical representation of how unusual and synchronized the market is on a given trading day.

Example:

`2020-03-09 → Market Stress Score = 44.87`

`2020-03-12 → Market Stress Score = 48.99`

#### 3. Event Severity

Events are now assigned severity levels based on the calculated market stress:

* `LOW`
* `MEDIUM`
* `HIGH`
* `CRITICAL`

Example:

`2020-03-09 → 44.87 → CRITICAL`

`2020-03-03 → 36.82 → HIGH`

This allows the system to distinguish ordinary anomalies from periods of substantially elevated market stress.

#### 4. Event Classification

The engine now classifies market conditions into event types.

Current examples include:

* `Normal`
* `Market-Wide Synchronization`
* `Elevated Market Stress`
* `Broad Market Downside Shock`

The classification combines anomaly breadth, direction of anomalies, correlation behavior, and market stress.

#### 5. Event Duration

An `Event_Duration` field was introduced to track the persistence of detected market conditions.

The current implementation is still a prototype and needs refinement so that duration represents the actual lifetime of a continuous event rather than simply counting consecutive rows.

This will be improved in the next phase.

#### 6. SHAP Event Explainability

The event engine is connected with the existing SHAP explainability layer.

For the `2020-03-23` event, the system identified **7 anomalous stocks**:

* AXISBANK
* BAJAJFINSV
* BAJFINANCE
* INDUSINDBK
* ONGC
* VEDL
* ZEEL

For these anomalies, SHAP explanations were generated using:

* `Return`
* `Volatility_20`
* `Volume_Ratio`

The results show that large negative returns and elevated volatility were major contributors to the anomaly scores for the detected stocks.

#### 7. End-to-End Pipeline

The project now follows this architecture:

```text
Historical Market Data
        ↓
Feature Engineering
        ↓
Kafka Producer
        ↓
Kafka Topic
        ↓
Anomaly Detection
        ↓
Cross-Stock Correlation
        ↓
Correlation Z-Score
        ↓
Market Stress Score
        ↓
Event Classification
        ↓
Severity Detection
        ↓
Event Duration
        ↓
SHAP Explainability
        ↓
market_events.csv
```

### Current Project State

The project has moved beyond individual stock anomaly detection and now attempts to identify **market-wide events** from multiple signals.

The major components currently working are:

* Kafka-based market streaming
* Feature engineering
* Isolation Forest anomaly detection
* Cross-stock rolling correlation
* Correlation Z-score
* Market stress scoring
* Market event classification
* Event severity
* SHAP-based anomaly explanation
* Event dataset generation

### Next Phase

The next phase should focus on making the event engine more robust and closer to a real-time market monitoring system.

Planned work:

1. Fix and properly define event duration.
2. Generate unique event IDs.
3. Identify affected stocks for each event.
4. Rank the strongest anomaly contributors.
5. Add event direction (`UP`, `DOWN`, `MIXED`, `NEUTRAL`).
6. Generate automatic event summaries.
7. Calculate an event confidence score.
8. Produce a final structured event record suitable for a dashboard/API.
9. Eventually connect the event engine directly to live Kafka streams instead of only historical replay.

**Status: Day 10 complete.**
