# MarketLens: Presentation Material & Viva Guide

---

## 1. Executive Project Summary

**MarketLens** is an end-to-end quantitative surveillance and market anomaly detection platform designed for Indian equities (NSE NIFTY 50 universe). 

Traditional surveillance tools often suffer from one of two fundamental flaws:
1. **Micro-isolation bias:** They flag individual stock outliers while missing systemic market-wide liquidations where every stock drops together.
2. **Black-box opacity:** Complex deep learning models fail to explain *why* an equity or session was flagged as anomalous.

MarketLens resolves both flaws by introducing a **three-signal market intelligence engine**:
- **Stock-Level Anomaly Detection:** An Isolation Forest model trained chronologically on 3 corporate-action-adjusted features (`Return`, `Volatility_20`, `Volume_Ratio`).
- **Market-Wide Breadth Metrics:** Direct monitoring of `Negative_Breadth`, `Severe_Decline_Breadth` ($\le -5\%$), and `Mean_Return` to capture broad market selloffs (such as March 16, 2020) where zero individual stocks breach the outlier threshold.
- **Cross-Stock Correlation Breaks:** Measuring multi-asset synchronization through 60-day rolling pairwise correlation matrices and Z-scores against historical baselines.
- **Explainable AI:** SHAP TreeExplainer integration attributing anomalies to exact directional contributions of return, volatility, and volume.
- **Serving & Presentation:** A resilient FastAPI REST backend paired with a dark-themed Streamlit dashboard providing on-demand historical date investigation and live daily surveillance.

---

## 2. 5–7 Minute Speaking Script

> **Speaker Note:** Maintain a confident, disciplined engineering tone. Emphasize empirical design choices and mathematical transparency over buzzwords.

### Slide / Topic 1: Introduction & The Core Problem (Minute 0:00 – 1:15)
"Good morning, respected evaluators. Today, I am presenting **MarketLens**, a market anomaly detection and event surveillance system designed for Indian equities.

When institutions monitor market stability, they typically apply single-stock anomaly detectors. But in financial markets, a critical paradox occurs during systemic crashes: when the entire market experiences panic selling, every stock drops in unison. Because all stocks behave similarly, multi-dimensional clustering or distance-based algorithms like Isolation Forest often flag **zero anomalies**—even on days of catastrophic market decline.

MarketLens was built specifically to solve this gap by synthesizing individual machine learning anomaly detection with macro-level market breadth and cross-asset correlation breaks."

### Slide / Topic 2: Feature Engineering & Isolation Forest (Minute 1:15 – 2:30)
"Our underlying universe covers 21 years of NSE historical data, encompassing 4,642 trading sessions and 189,853 observations.

For individual stock surveillance, we engineered three features:
1. **Daily Return**, rigorously adjusted for historical stock splits and corporate actions using Yahoo Finance adjusted closes. Without this correction, stock splits—like Eicher Motors dropping 89% purely due to a 10-for-1 split—trigger false positive crashes.
2. **20-day Rolling Volatility**, capturing short-term price instability.
3. **Volume Ratio**, normalizing daily volume against its 20-day historical baseline.

We trained an **Isolation Forest** with 200 estimators and a disciplined 1% contamination threshold chronologically on data prior to 2016, and evaluated it out-of-sample from 2016 to 2021."

### Slide / Topic 3: The Macro Breadth Signal & Stress Scoring (Minute 2:30 – 3:45)
"To address the systemic liquidation paradox, we designed three market breadth signals:
- **Negative Breadth:** the proportion of stocks falling on a given day.
- **Severe Decline Breadth:** the proportion of stocks falling by 5% or more.
- **Mean Market Return.**

We combined these into a **Three-Signal Composite Market Stress Score**:
30% Anomaly Breadth, 30% Correlation Z-Score, and 40% Breadth Stress Score.

Furthermore, we established a **Downside Shock Override**: if negative breadth exceeds 90%, severe decline exceeds 10%, and mean return is below minus 2%, the session is automatically classified as a **Broad Market Downside Shock** with **CRITICAL** severity.

This explains why **March 16, 2020**—where the market plunged 7% and 100% of stocks declined, yet Isolation Forest flagged zero individual outliers—is correctly classified by MarketLens as a **CRITICAL** market event."

### Slide / Topic 4: Explainability & Historical Date Exploration (Minute 3:45 – 5:00)
"For every anomalous observation, MarketLens runs **SHAP TreeExplainer** directly on the Isolation Forest trees. It decomposes the anomaly score into exact feature attributions, showing analysts whether extreme return, heightened volatility, or volume expansion drove the flag.

In our Streamlit interface and FastAPI backend, we introduced **On-Demand Historical Date Analysis**. An analyst can pick *any* date from the 21-year dataset—even dates outside our consolidated events table, like the October 2008 Lehman collapse—and immediately receive stock-by-stock anomaly scores, breadth metrics, severity ratings, and SHAP charts."

### Slide / Topic 5: Live Mode & Conclusion (Minute 5:00 – 6:15)
"Finally, MarketLens features a **Live Daily Market Surveillance** mode. Using our provider abstraction, it retrieves the latest closed trading session from Yahoo Finance, computes the 20-day rolling indicators, and evaluates current market conditions. We are completely transparent that this operates at daily observation frequency, as true sub-second tick streaming requires enterprise exchange feeds.

In summary, MarketLens is mathematically grounded, robustly tested across 17 automated regression checkpoints, and offers complete end-to-end explainability. Thank you, and I look forward to your questions."

---

## 3. Short Live-Demo Sequence (Step-by-Step)

1. **Step 1: Start the Backend and Dashboard**
   - Terminal 1: `python -m uvicorn main:app --host 127.0.0.1 --port 8000`
   - Terminal 2: `python -m streamlit run streamlit_app.py --server.port 8501`
   - Show the browser opening to `http://localhost:8501`. Note the green indicator: `● FastAPI Connected (Port 8000)`.

2. **Step 2: Overview & Seven Consolidated Events**
   - Show the **Market Stress Trajectory** line chart across March 2020.
   - Point out the 7 consolidated events table with peak stress dates and duration.

3. **Step 3: The Historic Checkpoint — March 23, 2020**
   - Navigate to **Historical Date Analysis**.
   - Click the preset button: `Preset: 2020-03-23`.
   - Click **🔍 Analyze Date**.
   - Point out: 47 stocks analyzed, 7 anomalies detected (`AXISBANK`, `BAJAJFINSV`, `BAJFINANCE`, `INDUSINDBK`, `ONGC`, `VEDL`, `ZEEL`), 100% Negative Breadth, 89.36% Severe Decline Breadth, Stress Score 49.35, **CRITICAL**.
   - Scroll down to **SHAP Feature Contributions**, expand `AXISBANK`, and show the horizontal bar chart where negative return (-27.9%) and volatility (7.0%) drove the anomaly.

4. **Step 4: The Zero-Anomaly Macro Crash — March 16, 2020**
   - Click the preset button: `Preset: 2020-03-16`.
   - Click **🔍 Analyze Date**.
   - Highlight the key result: **0 IF Anomalies Detected**, yet Event Type is **Broad Market Downside Shock** and Severity is **CRITICAL**.
   - Explain to the jury: *"Market breadth is 100% negative and severe decline breadth is 76.6%. The macro breadth override captured this systemic crash without fabricating false stock-level anomalies."*

5. **Step 5: Unlisted Historical Date Investigation — October 24, 2008**
   - Click the preset button: `Preset: 2008-10-24` (Lehman Brothers collapse).
   - Click **🔍 Analyze Date**.
   - Show that an unlisted date from 2008 is dynamically analyzed from the underlying 21-year stream: 45 stocks analyzed, 10 anomalies detected, 100% negative breadth, mean return -9.65%, **CRITICAL**.

6. **Step 6: Live Market Surveillance & Non-Trading Day Handling**
   - Select a weekend date (e.g. `2020-03-15`, Sunday) and show the clean message: *"Date is not a recorded trading day (weekend or market holiday)."*
   - Navigate to **Live Market Surveillance**, click **Refresh Live Market Data**, and show current NIFTY daily closing statistics, data freshness label, and observation frequency disclaimer.

---

## 4. Technical Viva Question-and-Answer Sheet

### Q1: Why did you choose Isolation Forest over autoencoders, DBSCAN, or One-Class SVM?
**Answer:**  
"Isolation Forest was chosen for three reasons:
1. **Linear Time Complexity & Efficiency:** $O(n \log n)$ training and $O(n)$ inference, which is essential for real-time or streaming replay.
2. **Resistance to the Curse of Dimensionality:** Unlike distance-based algorithms like DBSCAN or k-NN, Isolation Forest isolates anomalies by randomly partitioning feature values; anomalies require substantially fewer splits to isolate.
3. **Direct Tree Compatibility with SHAP:** `shap.TreeExplainer` provides exact, polynomial-time local attribution on tree ensembles without requiring the sampling approximations needed by kernel SHAP for deep autoencoders."

### Q2: Why did March 16, 2020 have 0 Isolation Forest anomalies, and how did your system handle it?
**Answer:**  
"On March 16, 2020, the NIFTY plunged over 7%, and 100% of equities declined. However, because the decline was uniform across almost all stocks with moderate volume, no single stock formed an isolated outlier in 3D feature space compared to historical flash crashes.  
If we relied solely on stock outliers, the system would have reported a normal day. MarketLens addresses this by introducing the **Market-Wide Breadth Layer**. When `Negative_Breadth >= 0.90`, `Severe_Decline_Breadth >= 0.10`, and `Mean_Return <= -0.02`, our downside shock override flags the session as **CRITICAL** regardless of individual outlier counts."

### Q3: What corporate-action issue did you encounter with raw NSE data, and how did you resolve it?
**Answer:**  
"In raw exchange trade data, stock splits and bonus issues create artificial price drops. For example, when Eicher Motors executed a 10-for-1 split on 2020-08-24, its raw price dropped 89.97%. An unadjusted detector flags this as a massive crash.  
We resolved this by using Yahoo Finance corporate-action adjusted closing prices specifically for the `Return` calculation and normalized volume onto a comparable share basis, while retaining authentic NSE exchange data for VWAP and turnover. This completely eliminated false split anomalies."

### Q4: How is the Composite Market Stress Score formulated, and why these weights?
**Answer:**  
"$$\text{Market\_Stress\_Score} = 0.30 \times \text{Anomaly\_Score} + 0.30 \times \text{Correlation\_Score} + 0.40 \times \text{Breadth\_Stress\_Score}$$  
- **Breadth (40%):** Received the highest weight because severe systemic selloffs are macro liquidity events.
- **Correlation (30%):** Measures asset synchronization (correlation breaks), where assets suddenly move in lockstep.
- **Anomaly Breadth (30%):** Measures the proportion of stocks displaying idiosyncratic price-volume instability."

### Q5: How do you explain an anomaly to a portfolio manager or risk officer?
**Answer:**  
"We use `shap.TreeExplainer`. For every anomalous stock, SHAP computes the Shapley value of each feature relative to the tree ensemble's base expectation. In our dashboard, we display both the actual feature value and its directional SHAP attribution—for instance, showing that Axis Bank's -27.9% return contributed -3.66 to its anomaly score, while its 2.04x volume ratio contributed -0.94. We explicitly document that SHAP describes model attribution, not economic causation."

### Q6: Can this system predict market crashes in advance?
**Answer:**  
"No, and we explicitly document this limitation. MarketLens is a **surveillance and detection system**, not a predictive forecasting model. It identifies, classifies, and explains market stress in real time as trading sessions unfold. Making predictive claims without forward-looking alpha validation would be mathematically unscientific."

---

## 5. Limitations & Future Roadmap

| Current Limitation | Technical Reason | Future Roadmap Solution |
| :--- | :--- | :--- |
| **Daily Close Observation Frequency** | Public Yahoo Finance APIs deliver daily close bars or 15-minute delayed snapshots. | Integrate enterprise WebSocket tick stream (e.g. Zerodha Kite Connect WebSocket or TrueData) for true sub-second tick surveillance. |
| **Fixed Precomputed Baseline for Single-Date Z-Score** | Calculating a 252-day correlation baseline requires 252 continuous trading sessions of correlation history. | Implement an asynchronous background indexing worker that pre-calculates and caches rolling Z-scores across all 4,642 historical dates in SQLite/DuckDB. |
| **Historical Stock Universe Shifts** | Constituents of NIFTY 50 change over time as companies enter and exit the index. | Implement survivorship-bias-free dynamic index universe mapping using historical NSE constituent change archives. |
| **Fixed Linear Weights in Stress Score** | The 30/30/40 weighting is an operational composite metric rather than an empirically calibrated posterior probability. | Calibrate composite score weights using logistic regression or Hidden Markov Models (HMM) fitted against documented SEBI circuit breaker days. |
