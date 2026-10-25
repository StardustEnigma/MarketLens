# MarketLens: Market Anomaly Detection & Event Surveillance System

**MarketLens** is an end-to-end quantitative surveillance and market anomaly detection platform designed for Indian equities (NSE NIFTY 50 universe). The platform bridges the gap between individual stock anomaly detection and macro-level market stress by synthesizing machine learning (Isolation Forest), multi-asset cross-sectional correlation breaks, systemic market breadth metrics, and local explainability (SHAP).

---

## 1. System Architecture

The following diagram illustrates the implemented architecture, data pipelines, surveillance layers, and presentation interfaces:

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

---

## 2. Core Capabilities & Methodology

### A. Feature Engineering Pipeline
The anomaly detection layer evaluates equities across a 3-dimensional normalized feature space:
1. **`Return`**: Daily percentage price movement (corporate-action adjusted using Yahoo Finance `Adj Close` conventions to prevent stock split false positives).
2. **`Volatility_20`**: 20-trading-day rolling standard deviation of daily returns, capturing price instability.
3. **`Volume_Ratio`**: Current daily volume divided by the stock's 20-day rolling average volume.

### B. Stock-Level Anomaly Detection (Isolation Forest)
- **Model:** `sklearn.ensemble.IsolationForest`
- **Configuration:** `n_estimators=200`, `contamination=0.01`, `random_state=42`
- **Temporal Split:** Trained chronologically on observations prior to `2016-01-01`; evaluated out-of-sample on `2016-01-01` to `2021-04-30`.
- **Artifact:** Persisted at `models/isolation_forest.joblib`.

### C. Market-Wide Breadth Metrics
A key finding during development was that broad market selloffs (such as March 16, 2020) can plunge an entire market without individual stocks breaching the 1% multivariate anomaly boundary. MarketLens addresses this detection gap through three macro signals:
- **`Negative_Breadth`**: $\frac{\sum \mathbb{I}(\text{Return} < 0)}{N}$ (Percentage of stocks declining).
- **`Severe_Decline_Breadth`**: $\frac{\sum \mathbb{I}(\text{Return} \le -5\%)}{N}$ (Percentage of stocks suffering severe liquidations).
- **`Mean_Return`**: Cross-sectional mean equity return.

### D. Three-Signal Composite Market Stress Score
$$\text{Market\_Stress\_Score} = 0.30 \times \text{Anomaly\_Score} + 0.30 \times \text{Correlation\_Score} + 0.40 \times \text{Breadth\_Stress\_Score}$$
Where:
- $\text{Anomaly\_Score} = \text{Anomaly\_Breadth} \times 100$
- $\text{Correlation\_Score} = \frac{\text{clip}(\text{Correlation\_Z}, 0, 6)}{6} \times 100$
- $\text{Breadth\_Stress\_Score} = 100 \times \text{Negative\_Breadth} \times \text{clip}(\text{Severe\_Decline\_Breadth}, 0, 1)$

### E. Event Classification & Severity Rules
- **Downside Shock Override:** If $\text{Negative\_Breadth} \ge 90\%$, $\text{Severe\_Decline\_Breadth} \ge 10\%$, and $\text{Mean\_Return} \le -2.0\%$, the event is classified as **Broad Market Downside Shock** with **CRITICAL** severity (ensuring systemic days like March 16, 2020 reach CRITICAL regardless of zero stock outliers).
- **Score Thresholds:** $\ge 40$ (CRITICAL), $\ge 25$ (HIGH), $\ge 15$ (MEDIUM), $< 15$ (LOW).

### F. Explainable AI via SHAP
Local feature attributions are computed via `shap.TreeExplainer(model)` on the Isolation Forest trees, quantifying the directional contributions of Return, Volatility, and Volume Ratio for each anomalous stock.

---

## 3. Dataset Specifications

- **Historical Raw Data:** `Dataset/NIFTY50_all.csv` (235,192 rows, 65 stocks, 2000–2021).
- **Stream Dataset:** `Dataset/market_stream.csv` (189,853 observations across 4,642 trading dates).
- **Consolidated Events:** `Dataset/market_events.csv` (7 multi-day consolidated events including March 2020 turmoil).
- **Correlation Baseline:** `Dataset/streamed_correlation.csv` (15 streaming correlation benchmarks).

---

## 4. Installation & Environment Setup

### Prerequisites
- Python 3.10+
- (Optional) Docker & Docker Compose for Kafka event streaming.

### Setup Instructions
1. Clone or navigate to the repository directory:
   ```bash
   cd c:\Users\Atharva\PycharmProjects\MLProject
   ```
2. Activate your virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
3. Verify required packages:
   ```powershell
   pip install -r requirements.txt
   ```
4. Configure optional environment variables:
   ```powershell
   cp .env.example .env
   ```

---

## 5. Execution Commands

### A. Run Automated Test Suite
Execute the 16 regression and unit tests:
```powershell
.\.venv\Scripts\python.exe test_marketlens.py
```

### B. Launch FastAPI Backend
Start the REST API server on port 8000:
```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation will be available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### C. Launch Streamlit Surveillance Dashboard
Start the interactive dashboard on port 8501:
```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8501
```

### D. Kafka Event Streaming (Optional)
1. Start the Kafka broker container:
   ```bash
   docker compose up -d
   ```
2. Run the historical replay producer (e.g. streaming 100 observations):
   ```powershell
   .\.venv\Scripts\python.exe producer/market_producer.py --limit 100 --delay 0.01
   ```
3. Run the Kafka anomaly consumer:
   ```powershell
   .\.venv\Scripts\python.exe consumer/anomaly_consumer.py
   ```
4. **Offline Replay Simulation Mode (No Docker required):**
   ```powershell
   .\.venv\Scripts\python.exe consumer/anomaly_consumer.py --simulate --date 2020-03-23
   ```

---

## 6. API Route Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Service health status. |
| `GET` | `/status` | System capabilities, universe size, and historical range. |
| `GET` | `/events` | List all consolidated market events (filters: `severity`, `event_type`). |
| `GET` | `/events/{event_id}` | Fetch detailed event record with affected stocks. |
| `GET` | `/events/{event_id}/explanation` | Fetch SHAP feature attributions for peak event date. |
| `GET` | `/analysis/date/{analysis_date}` | **On-demand analysis of any historical trading date** (e.g. `2020-03-16`). |
| `GET` | `/analysis/live` | **Live daily surveillance** using latest closed market session. |

---

## 7. Known Regression Checkpoints

| Date | Stocks Analyzed | IF Anomalies | Negative Breadth | Severe Breadth | Severity | Stress Score | Notable Characteristics |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2020-03-12** | 47 | 2 | 100.0% | 89.36% | **CRITICAL** | 65.14 | Peak stress shock, ONGC and VEDL anomalies. |
| **2020-03-16** | 47 | 0 | 100.0% | 76.60% | **CRITICAL** | 43.97 | **Zero stock outliers**, flagged via Breadth override. |
| **2020-03-23** | 47 | 7 | 100.0% | 89.36% | **CRITICAL** | 49.35 | 7 affected stocks (AXISBANK, BAJAJFINSV, BAJFINANCE, INDUSINDBK, ONGC, VEDL, ZEEL). |
| **2008-10-24** | 45 | 10 | 100.0% | 80.00% | **CRITICAL** | N/A | Lehman Crisis trough; unlisted in `market_events.csv` but verified via on-demand date analysis. |

---

## 8. Data Transparency & Limitations

1. **Daily Observation Frequency:** MarketLens operates on daily close-to-close bars. Delayed daily bars from Yahoo Finance do not represent sub-second intraday data. True sub-second tick streaming surveillance requires an enterprise tick feed connection (e.g., Zerodha Kite Connect WebSocket, TrueData).
2. **Predictive Scope:** MarketLens is an anomaly detection and surveillance system, not a directional forecasting or trade-recommendation tool.
3. **Survivor Universe:** Historical equity universes change over time (e.g., stocks entering or leaving NIFTY 50). The system dynamically evaluates available active stocks on each date rather than assuming fixed membership.
