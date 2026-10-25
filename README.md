<div align="center">

# 🔍 MarketLens

### Market Anomaly Detection & Event Surveillance for Indian Equities

**Most anomaly detectors watch single stocks. MarketLens also sees the crash where no single stock looks unusual.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-Isolation%20Forest-F7931E?logo=scikitlearn&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)
![SHAP](https://img.shields.io/badge/SHAP-Explainable%20AI-8A2BE2)
![Kafka](https://img.shields.io/badge/Kafka-Optional%20Streaming-231F20?logo=apachekafka&logoColor=white)
![Tests](https://img.shields.io/badge/tests-16%20passing-brightgreen)

[Why](#-the-problem-that-started-this) · [Architecture](#-architecture) · [Methodology](#-methodology) · [Quickstart](#-quickstart) · [API](#-api-reference) · [Results](#-regression-checkpoints) · [Limitations](#-limitations--honest-notes)

</div>

---

## ✨ Highlights

| | |
|---|---|
| 🌲 **Stock-level ML** | Isolation Forest over `Return`, `Volatility_20`, `Volume_Ratio`, trained chronologically to avoid look-ahead leakage |
| 🌊 **Market-wide breadth** | Catches systemic selloffs that produce *zero* single-stock outliers |
| 🔗 **Correlation breaks** | 60-day rolling pairwise correlation, z-scored to flag "everything moves together" regimes |
| 🎯 **One composite score** | Three signals fused into a single 0–100 Market Stress Score with calibrated severity tiers |
| 🧠 **Explainable** | SHAP `TreeExplainer` attributions for every flagged stock |
| ⚡ **Two ways to run** | Historical on-demand analysis for any trading date, or live daily surveillance via Yahoo Finance |
| 📡 **Streaming-ready** | Optional Kafka producer/consumer with an offline replay mode (no Docker required) |
| 🖥️ **Full stack** | FastAPI backend + 5-page Streamlit dashboard |

---

## 💡 The Problem That Started This

On **16 March 2020**, Indian equities were in freefall: every NIFTY 50 stock in the analysis universe closed down, and more than three-quarters fell 5% or more.

A standard per-stock Isolation Forest flagged **zero** of them.

Why? When *everything* drops together, no individual stock looks unusual relative to the rest of the crash. The model's 1% contamination boundary is never breached, even though it is arguably the most important day of the year.

MarketLens fixes this blind spot by layering **three complementary signals**: individual anomalies, cross-stock correlation, and market breadth. It then adds a downside-shock override so systemic days can't slip through.

---

## 🏗 Architecture

```mermaid
flowchart TD
    subgraph DataIngestion [Data Sources & Ingestion]
        A1[(Dataset/market_stream.csv<br/>4,642 Trading Days)] --> B1[Historical Stream Extractor]
        A2[Yahoo Finance API<br/>Daily Closing Bars] --> B2[Live Daily Provider]
        A3[Historical Replay Producer] -->|JSON Messages| K1[Kafka Topic: market-events]
    end

    subgraph CoreEngine [MarketLens Intelligence Engine]
        B1 --> C1[Feature Normalizer<br/>Return, Volatility_20, Volume_Ratio]
        B2 --> C1
        K1 -->|Consumer| C1

        C1 --> D1[Isolation Forest Detector<br/>models/isolation_forest.joblib]
        D1 -->|Predictions & Scores| E1[Stock Anomaly Aggregator]

        C1 --> E2[Market Breadth Engine<br/>Negative & Severe-Decline Breadth]
        C1 --> E3[Cross-Stock Correlation<br/>60-Day Rolling Pairwise Matrix]

        E1 --> F1[Composite Market Stress Scorer]
        E2 --> F1
        E3 --> F1

        F1 --> G1[Event Classifier & Severity Engine<br/>Downside Override & Calibrated Thresholds]
        G1 --> G2[Event Consolidator]

        D1 --> H1[SHAP Explainability Layer<br/>TreeExplainer Attribution]
    end

    subgraph ServiceLayer [FastAPI Backend Service]
        G1 --> API[FastAPI REST API<br/>Port 8000]
        G2 --> API
        H1 --> API
        API --> Endpoints[Endpoints:<br/>GET /events<br/>GET /analysis/date/{date}<br/>GET /analysis/live<br/>GET /events/{id}/explanation]
    end

    subgraph UserInterface [Streamlit Surveillance Dashboard]
        API --> UI[Streamlit UI<br/>Port 8501]
        UI --> P1[Overview & Trajectory]
        UI --> P2[Historical Date Analysis]
        UI --> P3[Event Explorer & SHAP]
        UI --> P4[Live Daily Surveillance]
        UI --> P5[Model & Methodology]
    end
```

**Data flow in one sentence:** daily bars come in (from CSV, Yahoo Finance, or Kafka), get turned into three features per stock, are scored by the Isolation Forest, combined with breadth and correlation signals into a composite stress score, classified by severity, consolidated into multi-day events, and served through the API and dashboard.

---

## 🧪 Methodology

### 1. Feature Engineering

Every stock on every day is described by three normalized features:

| Feature | Definition | What it captures |
|---|---|---|
| `Return` | Daily % price change, using Yahoo Finance `Adj Close` | Direction and magnitude of the move. Adjusted prices prevent stock splits from appearing as false crashes. |
| `Volatility_20` | 20-day rolling standard deviation of daily returns | Price instability |
| `Volume_Ratio` | Today's volume ÷ 20-day average volume | Unusual trading activity |

### 2. Stock-Level Detection: Isolation Forest

| Parameter | Value |
|---|---|
| Model | `sklearn.ensemble.IsolationForest` |
| `n_estimators` | `200` |
| `contamination` | `0.01` |
| `random_state` | `42` |
| Training window | All observations **before 2016-01-01** |
| Evaluation window | **2016-01-01 → 2021-04-30**, fully out-of-sample |
| Artifact | `models/isolation_forest.joblib` |

The split is **chronological, not random**. Shuffling time-series data would leak future regimes into training and flatter the results.

### 3. Market-Wide Breadth

Three cross-sectional signals computed over the *N* stocks trading on a given day:

$$\text{Negative\_Breadth} = \frac{\sum \mathbb{I}(\text{Return} < 0)}{N}$$

$$\text{Severe\_Decline\_Breadth} = \frac{\sum \mathbb{I}(\text{Return} \le -5\%)}{N}$$

$$\text{Mean\_Return} = \frac{1}{N}\sum \text{Return}$$

### 4. Composite Market Stress Score

$$\text{Market\_Stress\_Score} = 0.30 \times \text{Anomaly\_Score} + 0.30 \times \text{Correlation\_Score} + 0.40 \times \text{Breadth\_Stress\_Score}$$

| Component | Formula | Weight |
|---|---|:---:|
| **Anomaly Score** | `Anomaly_Breadth × 100` (share of stocks flagged by the Isolation Forest) | 30% |
| **Correlation Score** | `clip(Correlation_Z, 0, 6) / 6 × 100` | 30% |
| **Breadth Stress Score** | `100 × Negative_Breadth × clip(Severe_Decline_Breadth, 0, 1)` | 40% |

Breadth carries the most weight because it is the signal that catches what the per-stock model structurally cannot.

#### Worked example: 16 March 2020

| Component | Value | Weighted contribution |
|---|---|:---:|
| Anomaly Score | 0 (no stocks flagged) | 0.00 |
| Breadth Stress Score | `100 × 1.00 × 0.766 = 76.6` | **30.64** |
| Correlation Score (implied) | ≈ 44.4 | ≈ 13.33 |
| **Market Stress Score** | | **43.97** |

The Isolation Forest contributed nothing, and the day still reached **CRITICAL**.

### 5. Event Classification & Severity

**Downside Shock Override.** If all three conditions hold, the day is labelled **Broad Market Downside Shock** at **CRITICAL** severity, regardless of the composite score:

- `Negative_Breadth ≥ 90%`
- `Severe_Decline_Breadth ≥ 10%`
- `Mean_Return ≤ -2.0%`

**Score thresholds:**

| Severity | Stress Score |
|:---:|:---:|
| 🔴 **CRITICAL** | ≥ 40 |
| 🟠 **HIGH** | ≥ 25 |
| 🟡 **MEDIUM** | ≥ 15 |
| 🟢 **LOW** | < 15 |

Consecutive flagged days are then merged by the **Event Consolidator** into multi-day events (for example, the March 2020 turmoil), so you see one coherent episode instead of a pile of daily alerts.

### 6. Explainability with SHAP

For each anomalous stock, `shap.TreeExplainer(model)` attributes the anomaly score to `Return`, `Volatility_20`, and `Volume_Ratio`. That tells you *why* a stock was flagged, for example a price collapse versus a volume spike, not just *that* it was.

---

## 🖥 Dashboard

The Streamlit app has five pages:

| Page | What you get |
|---|---|
| **Overview & Trajectory** | Stress score over time and a summary of detected events |
| **Historical Date Analysis** | Pick any trading date and get a full on-demand breakdown |
| **Event Explorer & SHAP** | Drill into an event, see affected stocks and feature attributions |
| **Live Daily Surveillance** | Analyze the most recent closed market session |
| **Model & Methodology** | In-app documentation of the approach |

> 📸 *Add screenshots here: `docs/images/overview.png`, `docs/images/shap.png`*

---

## 🚀 Quickstart

### Prerequisites

- Python **3.10+**
- *(Optional)* Docker & Docker Compose for Kafka streaming

### Installation

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd MLProject

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Configure environment variables
cp .env.example .env
```

### Run it

**1. Verify everything works** (16 regression and unit tests)

```bash
python test_marketlens.py
```

**2. Start the API** → http://127.0.0.1:8000/docs

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**3. Start the dashboard** → http://localhost:8501

```bash
python -m streamlit run streamlit_app.py --server.port 8501
```

> 💡 Start the API first. The dashboard reads from it.
> Windows users with a venv can also call the interpreter directly: `.\.venv\Scripts\python.exe <command>`.

---

## 📡 Kafka Streaming (Optional)

Replay history as a live event stream.

```bash
# 1. Start the broker
docker compose up -d

# 2. Terminal A: replay 100 observations with a 10ms delay
python producer/market_producer.py --limit 100 --delay 0.01

# 3. Terminal B: consume and detect anomalies in real time
python consumer/anomaly_consumer.py
```

**No Docker? Use offline replay simulation:**

```bash
python consumer/anomaly_consumer.py --simulate --date 2020-03-23
```

---

## 🌐 API Reference

Base URL: `http://127.0.0.1:8000`. Interactive docs are at [`/docs`](http://127.0.0.1:8000/docs) (Swagger) and [`/redoc`](http://127.0.0.1:8000/redoc).

| Method | Endpoint | Description |
|:---:|---|---|
| `GET` | `/` | Service health status |
| `GET` | `/status` | Capabilities, universe size, historical range |
| `GET` | `/events` | All consolidated events. Filter with `severity`, `event_type` |
| `GET` | `/events/{event_id}` | Event detail including affected stocks |
| `GET` | `/events/{event_id}/explanation` | SHAP attributions for the event's peak date |
| `GET` | `/analysis/date/{analysis_date}` | **On-demand analysis of any historical trading date** |
| `GET` | `/analysis/live` | **Live surveillance** on the latest closed session |

### Examples

```bash
# Analyze the COVID crash day that the stock-level model missed
curl http://127.0.0.1:8000/analysis/date/2020-03-16

# All CRITICAL events
curl "http://127.0.0.1:8000/events?severity=CRITICAL"

# Why was this event flagged?
curl http://127.0.0.1:8000/events/1/explanation

# What's the market doing right now?
curl http://127.0.0.1:8000/analysis/live
```

---

## ✅ Regression Checkpoints

These dates are locked into the test suite so any change to the pipeline that alters known outcomes fails loudly.

| Date | Stocks | IF Anomalies | Negative Breadth | Severe Breadth | Severity | Stress Score | Notes |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **2020-03-12** | 47 | 2 | 100.0% | 89.36% | 🔴 CRITICAL | 65.14 | Peak stress shock. ONGC and VEDL flagged |
| **2020-03-16** | 47 | **0** | 100.0% | 76.60% | 🔴 CRITICAL | 43.97 | **Zero stock outliers**, caught by the breadth override |
| **2020-03-23** | 47 | 7 | 100.0% | 89.36% | 🔴 CRITICAL | 49.35 | AXISBANK, BAJAJFINSV, BAJFINANCE, INDUSINDBK, ONGC, VEDL, ZEEL |
| **2008-10-24** | 45 | 10 | 100.0% | 80.00% | 🔴 CRITICAL | N/A | Lehman crisis trough. Not in `market_events.csv`, but verified via on-demand analysis |

The 2008 row shows the system generalizing beyond the events it was tuned on. The date is queryable on demand even though it isn't in the consolidated event file.

---

## 📦 Dataset

| File | Contents |
|---|---|
| `Dataset/NIFTY50_all.csv` | Raw history: 235,192 rows, 65 stocks, 2000–2021 |
| `Dataset/market_stream.csv` | Processed stream: 189,853 observations across 4,642 trading dates |
| `Dataset/market_events.csv` | 7 consolidated multi-day events, including March 2020 |
| `Dataset/streamed_correlation.csv` | 15 streaming correlation benchmarks |

---

## 🗂 Project Structure

```
MLProject/
├── main.py                    # FastAPI application
├── streamlit_app.py           # Streamlit dashboard
├── test_marketlens.py         # 16 regression & unit tests
├── producer/
│   └── market_producer.py     # Kafka historical replay producer
├── consumer/
│   └── anomaly_consumer.py    # Kafka consumer / offline simulator
├── models/
│   └── isolation_forest.joblib
├── Dataset/                   # Raw, stream, event & correlation CSVs
├── docker-compose.yml         # Kafka broker
├── requirements.txt
└── .env.example
```

---

## ⚠️ Limitations & Honest Notes

1. **Daily bars, not ticks.** MarketLens works on close-to-close data. Yahoo Finance daily bars are delayed and are not sub-second intraday data. True tick-level surveillance would need an enterprise feed such as Zerodha Kite Connect WebSocket or TrueData.
2. **Surveillance, not prediction.** MarketLens detects and explains unusual market behavior. It does not forecast direction or recommend trades. **This is not financial advice.**
3. **Changing universe.** NIFTY 50 membership changes over time. The system evaluates whichever stocks are active on each date rather than assuming fixed membership, which is why daily stock counts vary (e.g., 45 in 2008 vs. 47 in 2020). Results are not survivorship-free.
4. **Hand-set thresholds.** Severity cutoffs (40/25/15) and the override rules were calibrated against known stress episodes. Treat them as tunable defaults, not universal constants.

---

## 🛣 Roadmap

- [ ] Intraday / tick-level ingestion
- [ ] Sector-level breadth and contagion views
- [ ] Alerting (email / Slack / webhook) on HIGH+ severity
- [ ] Backtest of lead/lag versus realized volatility (VIX-equivalent)
- [ ] Dockerized one-command deployment for API + dashboard

---

## 🤝 Contributing

Issues and pull requests are welcome. Please run `python test_marketlens.py` before submitting. All 16 tests should pass.

## 📄 License

Add your license here (e.g., MIT).

## 👤 Author

Built by **Your Name** · [GitHub](https://github.com/your-username) · [LinkedIn](https://linkedin.com/in/your-profile)

---

<div align="center">

*When the whole market moves as one, MarketLens notices.*

</div>