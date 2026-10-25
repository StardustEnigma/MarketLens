# MarketLens: Verification & Testing Report

**Date of Execution:** 2026-10-25  
**Environment:** Windows, Python 3.10.11 (`.venv`), FastAPI 0.141.1, Scikit-Learn 1.9.1, SHAP 0.52.0  
**Test Runner:** `unittest` runner via `test_marketlens.py` and `consumer/anomaly_consumer.py`  
**Overall Result:** **ALL 17 TESTS PASSED (100% PASS RATE)**

---

## 1. Test Execution Summary

| Test Category | Total Tests | Passed | Failed | Skipped | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **API & Route Integrity** | 6 | 6 | 0 | 0 | **PASS** |
| **SHAP Explainability** | 2 | 2 | 0 | 0 | **PASS** |
| **Historical Date Analysis** | 6 | 6 | 0 | 0 | **PASS** |
| **Live Surveillance Mode** | 1 | 1 | 0 | 0 | **PASS** |
| **Kafka Replay Verification** | 1 | 1 | 0 | 0 | **PASS** |
| **Total** | **17** | **17** | **0** | **0** | **PASS** |

---

## 2. Detailed Test Cases & Results

### Category A: Core API & Events Integrity
| ID | Test Name | Expected Behavior | Actual Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| `TC-01` | Root Health Check (`GET /`) | Status 200, returns `{"service": "MarketLens", "status": "running"}` | Returned `200 OK`, matched schema | **PASS** |
| `TC-02` | System Status (`GET /status`) | Status 200, reports model loaded, universe size, and date bounds | Returned `200 OK`, active universe > 40, model confirmed | **PASS** |
| `TC-03` | Consolidated Events List (`GET /events`) | Returns exactly 7 consolidated multi-day historical events | Returned 7 events with stable IDs (`E20200303-01` to `E20200323-07`) | **PASS** |
| `TC-04` | Event Severity Filter (`GET /events?severity=CRITICAL`) | Filters event list to only `CRITICAL` severity events | Returned 5 critical events, all with `Severity == "CRITICAL"` | **PASS** |
| `TC-05` | Single Event Detail (`GET /events/E20200323-07`) | Returns March 23 event with CRITICAL severity and 7 affected stocks | Returned event, peak stress 49.35, 7 affected stocks | **PASS** |
| `TC-06` | Non-Existent Event Handling (`GET /events/E99999999-99`) | Returns HTTP 404 with structured error detail | Returned `404 Not Found`, message: `Event 'E99999999-99' not found` | **PASS** |

### Category B: Explainable AI (SHAP)
| ID | Test Name | Expected Behavior | Actual Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| `TC-07` | Event Explanation March 23 | Computes SHAP contributions for 7 anomalies across Return, Volatility, Volume | 7 anomalies explained, exact 3 feature attributions generated | **PASS** |
| `TC-08` | Event Explanation March 16 (Zero Anomalies) | Returns `Anomalies: 0` without fabricating explanations or throwing errors | Returned `Anomalies: 0`, empty explanations list with informative note | **PASS** |

### Category C: Historical Date Analysis (Feature One)
| ID | Test Name | Expected Behavior | Actual Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| `TC-09` | **Historical Checkpoint: 2020-03-16** | 47 stocks, 0 IF anomalies, negative breadth 100%, severe breadth 76.6%, mean return -7.05%, CRITICAL via breadth override | Stocks: 47, Anomalies: 0, Negative Breadth: 100.0%, Severe: 76.6%, Event: `Broad Market Downside Shock`, Severity: `CRITICAL` | **PASS** |
| `TC-10` | **Historical Checkpoint: 2020-03-23** | 47 stocks, 7 anomalies, negative breadth 100%, severe breadth 89.4%, CRITICAL | Stocks: 47, Anomalies: 7 (`AXISBANK`, `BAJAJFINSV`, `BAJFINANCE`, `INDUSINDBK`, `ONGC`, `VEDL`, `ZEEL`), Severity: `CRITICAL` | **PASS** |
| `TC-11` | **Historical Checkpoint: 2020-03-12** | 47 stocks, 2 anomalies (ONGC, VEDL), peak stress ~65.14, CRITICAL | Stocks: 47, Anomalies: 2, Stress Score: 65.14, Severity: `CRITICAL` | **PASS** |
| `TC-12` | **Unlisted Historical Date: 2008-10-24** | Can analyze date outside `market_events.csv`; Lehman trough (45 stocks, 10 anomalies, 100% negative breadth) | Stocks: 45, Anomalies: 10, Negative Breadth: 100.0%, Event: `Broad Market Downside Shock`, Severity: `CRITICAL` | **PASS** |
| `TC-13` | Non-Trading Day (Sunday 2020-03-15) | Returns `observations_available: false` with clear calendar warning | `observations_available: False`, Event: `Non-Trading Day`, clear explanation | **PASS** |
| `TC-14` | Out-of-Bounds Date (1995-05-10) | Returns `observations_available: false` with range bounds explanation | `observations_available: False`, Event: `Out of Range`, date bounds detailed | **PASS** |
| `TC-15` | Malformed Date Format (`invalid-format`) | Returns HTTP 400 Bad Request with validation message | Returned `400 Bad Request`, `Invalid date format` | **PASS** |

### Category D: Live Market Surveillance (Feature Two)
| ID | Test Name | Expected Behavior | Actual Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| `TC-16` | Live Surveillance Endpoint (`GET /analysis/live`) | Returns latest closed daily session with breadth, frequency label, and timestamps | Data source: `live_daily`, frequency: `Daily Close (End-of-Day / Delayed)`, `is_intraday: false`, timestamp present | **PASS** |

### Category E: Kafka Replay Verification (Feature Seven)
| ID | Test Name | Expected Behavior | Actual Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| `TC-17` | Kafka Streaming Replay (March 23, 2020) | Serializes historical stream to JSON, consumes, validates schema, verifies 47 stocks, 7 anomalies (14.89%), 7 negative, 0 positive | Published 47 events, consumed & validated. Verified: 47 stocks, 7 anomalies, 14.89% breadth, 7 negative, 0 positive | **PASS** |

---

## 3. Scope, Limitations & Environment Verification

1. **Docker / Kafka Broker:**  
   Docker daemon was not running during the test run (`dont do docker yet` user instruction). The Kafka producer and consumer scripts were reinforced with clean connection timeout handling (`NoBrokersAvailable` caught with clear user guidance), and deterministic streaming replay was verified via `consumer/anomaly_consumer.py --simulate`.
2. **Observation Frequency:**  
   Yahoo Finance provider delivers daily closing bars. Surveillance frequency is explicitly identified in responses as daily observation frequency; no false claim of real-time intraday tick streaming is made.
