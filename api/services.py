import ast
import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import shap
import yfinance as yf

logger = logging.getLogger("marketlens.services")

# -------------------------------------------------------------
# Constants & Configuration
# -------------------------------------------------------------
MODEL_PATH = "models/isolation_forest.joblib"
HISTORICAL_STREAM_PATH = "Dataset/market_stream.csv"
MARKET_EVENTS_PATH = "Dataset/market_events.csv"
CORRELATION_PATH = "Dataset/streamed_correlation.csv"

FEATURES = ["Return", "Volatility_20", "Volume_Ratio"]

# NSE Canonical Symbol to Yahoo Finance Ticker mapping
YAHOO_SYMBOL_OVERRIDES = {
    "M&M": "M&M.NS",
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "L&TFH": "L&TFH.NS",
    "MCDOWELL-N": "UNITDSPR.NS",
}


def to_yahoo_symbol(symbol: str) -> str:
    """Map NSE canonical symbol to Yahoo Finance ticker."""
    if symbol in YAHOO_SYMBOL_OVERRIDES:
        return YAHOO_SYMBOL_OVERRIDES[symbol]
    return f"{symbol}.NS"


def clean_val(val: Any) -> Any:
    """Ensure value is JSON-serializable (handles NaN, inf, numpy types)."""
    if val is None:
        return None
    if isinstance(val, (np.floating, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    return val


# -------------------------------------------------------------
# Classification & Severity Helpers
# -------------------------------------------------------------
def classify_event(
    negative_breadth: float,
    severe_breadth: float,
    mean_return: float,
    anomaly_breadth: float,
    negative_anomalies: int,
    positive_anomalies: int,
    corr_z: Optional[float],
    stress_score: Optional[float],
) -> str:
    """Classify market condition according to operational decision rules."""
    # 1. Broad market downside shock override (even with zero IF anomalies)
    if (
        negative_breadth >= 0.90
        and severe_breadth >= 0.10
        and mean_return <= -0.02
    ):
        return "Broad Market Downside Shock"

    # 2. Broad downside shock based on stock anomalies
    if (
        anomaly_breadth >= 0.10
        and negative_anomalies >= 5
        and negative_anomalies > positive_anomalies
    ):
        return "Broad Market Downside Shock"

    # 3. Market-wide synchronization
    if corr_z is not None and corr_z >= 4.0:
        return "Market-Wide Synchronization"

    # 4. Elevated anomaly breadth
    if anomaly_breadth >= 0.05:
        return "Elevated Market Stress"

    # 5. High combined stress score
    if stress_score is not None and stress_score >= 40.0:
        return "High Market Stress"

    return "Normal"


def classify_severity(
    negative_breadth: float,
    severe_breadth: float,
    mean_return: float,
    anomaly_breadth: float,
    negative_anomalies: int,
    positive_anomalies: int,
    stress_score: Optional[float],
) -> str:
    """Determine event severity level (LOW, MEDIUM, HIGH, CRITICAL)."""
    # 1. Market-wide downside override
    if (
        negative_breadth >= 0.90
        and severe_breadth >= 0.10
        and mean_return <= -0.02
    ):
        return "CRITICAL"

    # 2. Broad downside anomaly override
    if (
        anomaly_breadth >= 0.10
        and negative_anomalies >= 5
        and negative_anomalies > positive_anomalies
    ):
        return "CRITICAL"

    # 3. Score-based severity
    if stress_score is not None:
        if stress_score >= 40.0:
            return "CRITICAL"
        if stress_score >= 25.0:
            return "HIGH"
        if stress_score >= 15.0:
            return "MEDIUM"
        return "LOW"

    # Fallback if stress score cannot be computed
    if anomaly_breadth >= 0.05:
        return "MEDIUM"
    return "LOW"


# -------------------------------------------------------------
# Market Data Provider Abstraction
# -------------------------------------------------------------
class BaseMarketDataProvider:
    """Abstract interface for market data ingestion."""

    def fetch_latest_observations(
        self, universe: List[str]
    ) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[str]]:
        """
        Fetch latest market observations.
        Returns: (dataframe, as_of_date_str, warning_or_error_message)
        """
        raise NotImplementedError


class YahooFinanceDailyProvider(BaseMarketDataProvider):
    """
    Live daily market data provider using Yahoo Finance daily bars.
    Provides latest closed daily session with 20-day rolling feature engineering.
    """

    def __init__(self, lookback_days: int = 60):
        self.lookback_days = lookback_days

    def fetch_latest_observations(
        self, universe: List[str]
    ) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[str]]:
        if not universe:
            return None, None, "Stock universe is empty."

        ticker_map = {stock: to_yahoo_symbol(stock) for stock in universe}
        tickers = list(ticker_map.values())

        try:
            logger.info(f"Downloading live daily data for {len(tickers)} tickers from Yahoo Finance...")
            data = yf.download(
                tickers=tickers,
                period="3mo",
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=True,
            )

            if data.empty or "Close" not in data:
                return None, None, "Yahoo Finance returned empty data or missing price bars."

            close_df = data["Close"]
            vol_df = data["Volume"]

            # MultiIndex columns handling
            if isinstance(close_df.columns, pd.MultiIndex):
                close_df.columns = close_df.columns.get_level_values(-1)
            if isinstance(vol_df.columns, pd.MultiIndex):
                vol_df.columns = vol_df.columns.get_level_values(-1)

            # Determine latest date across columns with valid data
            valid_dates = close_df.dropna(how="all").index
            if len(valid_dates) < 21:
                return None, None, f"Insufficient price history ({len(valid_dates)} sessions, need >= 21)."

            latest_date = valid_dates[-1]
            as_of_date_str = latest_date.strftime("%Y-%m-%d")

            rows = []
            for stock, ticker in ticker_map.items():
                if ticker not in close_df.columns or ticker not in vol_df.columns:
                    continue

                stock_close = close_df[ticker].dropna()
                stock_vol = vol_df[ticker].dropna()

                if len(stock_close) < 21:
                    continue

                stock_ret = stock_close.pct_change()
                stock_vol20 = stock_ret.rolling(20).std()
                vol_mean20 = stock_vol.rolling(20).mean()
                stock_vol_ratio = stock_vol / vol_mean20

                if (
                    latest_date not in stock_ret.index
                    or pd.isna(stock_ret.loc[latest_date])
                    or pd.isna(stock_vol20.loc[latest_date])
                    or pd.isna(stock_vol_ratio.loc[latest_date])
                ):
                    continue

                rows.append({
                    "CanonicalSymbol": stock,
                    "Date": as_of_date_str,
                    "Return": float(stock_ret.loc[latest_date]),
                    "Volatility_20": float(stock_vol20.loc[latest_date]),
                    "Volume_Ratio": float(stock_vol_ratio.loc[latest_date]),
                })

            if not rows:
                return None, as_of_date_str, "No valid stock observations survived feature engineering."

            result_df = pd.DataFrame(rows)
            return result_df, as_of_date_str, None

        except Exception as e:
            logger.error(f"Failed to fetch Yahoo Finance live data: {e}")
            return None, None, f"Live data provider error: {str(e)}"


# -------------------------------------------------------------
# Core MarketLens Service
# -------------------------------------------------------------
class MarketLensService:
    """Central engine providing market data, model inference, and explanations."""

    _instance = None

    def __init__(self):
        logger.info("Initializing MarketLensService...")
        self.model = joblib.load(MODEL_PATH)
        self.explainer = shap.TreeExplainer(self.model)

        # Load market stream
        self.stream_df = pd.read_csv(HISTORICAL_STREAM_PATH)
        self.stream_df["Date"] = pd.to_datetime(self.stream_df["Date"])
        self.stream_df["Date_Str"] = self.stream_df["Date"].dt.strftime("%Y-%m-%d")

        # Available dates
        self.min_date_str = self.stream_df["Date_Str"].min()
        self.max_date_str = self.stream_df["Date_Str"].max()
        self.unique_dates_set = set(self.stream_df["Date_Str"].unique())
        self.universe = sorted(self.stream_df["CanonicalSymbol"].dropna().unique().tolist())

        # Preloaded correlations
        self.corr_df = pd.read_csv(CORRELATION_PATH)
        self.corr_df["Date"] = pd.to_datetime(self.corr_df["Date"])
        self.corr_df["Date_Str"] = self.corr_df["Date"].dt.strftime("%Y-%m-%d")
        self.corr_lookup = self.corr_df.set_index("Date_Str").to_dict(orient="index")

        # Preloaded events
        self.events_df = pd.read_csv(MARKET_EVENTS_PATH)

        # Live provider
        self.live_provider = YahooFinanceDailyProvider()
        self._cached_live_result: Optional[Dict[str, Any]] = None
        self._cached_live_time: Optional[datetime.datetime] = None

    @classmethod
    def get_instance(cls) -> "MarketLensService":
        if cls._instance is None:
            cls._instance = MarketLensService()
        return cls._instance

    def get_stock_universe(self) -> List[str]:
        return self.universe

    def get_historical_date_range(self) -> Tuple[str, str, int]:
        return self.min_date_str, self.max_date_str, len(self.unique_dates_set)

    def is_trading_date(self, date_str: str) -> bool:
        return date_str in self.unique_dates_set

    # ---------------------------------------------------------
    # Events Operations (Preserving Existing Architecture)
    # ---------------------------------------------------------
    def load_events(
        self, severity: Optional[str] = None, event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        df = self.events_df.copy()
        if severity:
            df = df[df["Severity"].str.upper() == severity.upper()]
        if event_type:
            df = df[df["Event_Type"].str.lower() == event_type.lower()]

        records = []
        for _, row in df.iterrows():
            record = row.where(pd.notnull(row), None).to_dict()
            aff = record.get("Affected_Stocks")
            if pd.isna(aff) or aff == "":
                record["Affected_Stocks"] = []
            elif isinstance(aff, str):
                try:
                    record["Affected_Stocks"] = ast.literal_eval(aff)
                except Exception:
                    record["Affected_Stocks"] = []
            records.append(record)
        return records

    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        df = self.events_df
        match = df[df["Event_ID"] == event_id]
        if match.empty:
            return None
        record = match.iloc[0].where(pd.notnull(match.iloc[0]), None).to_dict()
        aff = record.get("Affected_Stocks")
        if pd.isna(aff) or aff == "":
            record["Affected_Stocks"] = []
        elif isinstance(aff, str):
            try:
                record["Affected_Stocks"] = ast.literal_eval(aff)
            except Exception:
                record["Affected_Stocks"] = []
        return record

    def get_event_explanation(self, event_id: str) -> Optional[Dict[str, Any]]:
        event = self.get_event_by_id(event_id)
        if not event:
            return None
        peak_date = str(event["Peak_Date"])
        return self.explain_date_anomalies(peak_date)

    def explain_date_anomalies(
        self, date_str: str, day_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """Generate SHAP explanations for all detected anomalies on a date."""
        if day_df is None:
            day_df = self.stream_df[self.stream_df["Date_Str"] == date_str].copy()

        if day_df.empty:
            return {
                "Event_Date": date_str,
                "Anomalies": 0,
                "Explanations": [],
                "Note": "No observations available for this date.",
            }

        valid_df = day_df.dropna(subset=FEATURES).copy()
        if valid_df.empty:
            return {
                "Event_Date": date_str,
                "Anomalies": 0,
                "Explanations": [],
                "Note": "No valid observations after feature checking.",
            }

        preds = self.model.predict(valid_df[FEATURES])
        valid_df["Anomaly"] = preds
        anomalies_df = valid_df[valid_df["Anomaly"] == -1].copy()

        if anomalies_df.empty:
            return {
                "Event_Date": date_str,
                "Anomalies": 0,
                "Explanations": [],
                "Note": "Zero stock-level anomalies detected. Model-based individual SHAP explanation not applicable.",
            }

        explanations = []
        for i, (_, row) in enumerate(anomalies_df.iterrows()):
            X_anomaly = anomalies_df.iloc[[i]][FEATURES]
            shap_values = self.explainer.shap_values(X_anomaly)[0]

            feat_records = [
                {
                    "Feature": feat,
                    "Value": clean_val(X_anomaly.iloc[0][feat]),
                    "SHAP": clean_val(shap_values[j]),
                }
                for j, feat in enumerate(FEATURES)
            ]
            # Sort by absolute SHAP contribution descending
            feat_records.sort(key=lambda x: abs(x["SHAP"]), reverse=True)

            explanations.append({
                "Symbol": row["CanonicalSymbol"],
                "Return": clean_val(row["Return"]),
                "Volatility_20": clean_val(row["Volatility_20"]),
                "Volume_Ratio": clean_val(row["Volume_Ratio"]),
                "Features": feat_records,
            })

        return {
            "Event_Date": date_str,
            "Anomalies": len(explanations),
            "Explanations": explanations,
        }

    # ---------------------------------------------------------
    # FEATURE ONE: Historical Date Analysis
    # ---------------------------------------------------------
    def analyze_historical_date(self, analysis_date: str) -> Dict[str, Any]:
        """
        Extract observations for any historical trading date, run anomaly detection,
        calculate market breadth and correlation, and classify event.
        """
        warnings = []

        # Validate date format
        try:
            target_dt = datetime.datetime.strptime(analysis_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid date format '{analysis_date}'. Expected YYYY-MM-DD.")

        # Check range bounds
        min_dt = datetime.datetime.strptime(self.min_date_str, "%Y-%m-%d").date()
        max_dt = datetime.datetime.strptime(self.max_date_str, "%Y-%m-%d").date()

        if target_dt < min_dt or target_dt > max_dt:
            return {
                "analysis_date": analysis_date,
                "data_source": "historical",
                "observations_available": False,
                "stocks_analyzed": 0,
                "anomalies_detected": 0,
                "anomaly_breadth": 0.0,
                "negative_breadth": 0.0,
                "severe_decline_breadth": 0.0,
                "mean_return": 0.0,
                "rolling_correlation": None,
                "correlation_z": None,
                "market_stress_score": None,
                "event_type": "Out of Range",
                "severity": "LOW",
                "affected_stocks": [],
                "stock_results": [],
                "explanations": [],
                "warnings": [
                    f"Selected date {analysis_date} is outside the historical dataset range "
                    f"({self.min_date_str} to {self.max_date_str})."
                ],
            }

        # Check trading calendar
        if analysis_date not in self.unique_dates_set:
            return {
                "analysis_date": analysis_date,
                "data_source": "historical",
                "observations_available": False,
                "stocks_analyzed": 0,
                "anomalies_detected": 0,
                "anomaly_breadth": 0.0,
                "negative_breadth": 0.0,
                "severe_decline_breadth": 0.0,
                "mean_return": 0.0,
                "rolling_correlation": None,
                "correlation_z": None,
                "market_stress_score": None,
                "event_type": "Non-Trading Day",
                "severity": "LOW",
                "affected_stocks": [],
                "stock_results": [],
                "explanations": [],
                "warnings": [
                    f"Date {analysis_date} is not a recorded trading day in the historical dataset "
                    "(weekend or official NSE market holiday)."
                ],
            }

        # Extract observations
        day_df = self.stream_df[self.stream_df["Date_Str"] == analysis_date].copy()
        day_df = day_df.dropna(subset=FEATURES)

        if day_df.empty:
            return {
                "analysis_date": analysis_date,
                "data_source": "historical",
                "observations_available": False,
                "stocks_analyzed": 0,
                "anomalies_detected": 0,
                "anomaly_breadth": 0.0,
                "negative_breadth": 0.0,
                "severe_decline_breadth": 0.0,
                "mean_return": 0.0,
                "rolling_correlation": None,
                "correlation_z": None,
                "market_stress_score": None,
                "event_type": "No Data",
                "severity": "LOW",
                "affected_stocks": [],
                "stock_results": [],
                "explanations": [],
                "warnings": [f"Observations for {analysis_date} contained incomplete feature columns."],
            }

        stocks_analyzed = len(day_df)

        # Anomaly Detection via trained Isolation Forest
        X = day_df[FEATURES]
        preds = self.model.predict(X)
        scores = self.model.decision_function(X)

        day_df["Anomaly"] = preds
        day_df["Anomaly_Score"] = scores

        anomalies_df = day_df[day_df["Anomaly"] == -1].copy()
        anomalies_detected = len(anomalies_df)
        anomaly_breadth = anomalies_detected / stocks_analyzed if stocks_analyzed > 0 else 0.0
        affected_stocks = sorted(anomalies_df["CanonicalSymbol"].tolist())

        negative_anomalies = int(((day_df["Anomaly"] == -1) & (day_df["Return"] < 0)).sum())
        positive_anomalies = int(((day_df["Anomaly"] == -1) & (day_df["Return"] > 0)).sum())

        # Market-wide Breadth Metrics
        negative_breadth = float((day_df["Return"] < 0).mean())
        severe_decline_breadth = float((day_df["Return"] <= -0.05).mean())
        mean_return = float(day_df["Return"].mean())

        anomaly_score = anomaly_breadth * 100.0
        breadth_stress_score = 100.0 * negative_breadth * min(max(severe_decline_breadth, 0.0), 1.0)

        # Correlation Analysis
        rolling_corr = None
        corr_z = None
        market_stress_score = None

        if analysis_date in self.corr_lookup:
            corr_entry = self.corr_lookup[analysis_date]
            rolling_corr = clean_val(corr_entry.get("Rolling_Correlation"))
            corr_z = clean_val(corr_entry.get("Correlation_Z"))
            if corr_z is not None:
                corr_score = (min(max(corr_z, 0.0), 6.0) / 6.0) * 100.0
                market_stress_score = clean_val(
                    0.30 * anomaly_score + 0.30 * corr_score + 0.40 * breadth_stress_score
                )
        else:
            # Dynamically compute rolling 60-day correlation if possible
            rolling_corr = self._compute_rolling_correlation_for_date(analysis_date)
            if rolling_corr is None:
                warnings.append(
                    "Rolling correlation could not be computed (insufficient preceding trading days)."
                )
            else:
                warnings.append(
                    "Rolling correlation Z-score and composite stress score require multi-month baseline not in precomputed stream; composite stress score omitted."
                )

        # Event Classification & Severity
        event_type = classify_event(
            negative_breadth=negative_breadth,
            severe_breadth=severe_decline_breadth,
            mean_return=mean_return,
            anomaly_breadth=anomaly_breadth,
            negative_anomalies=negative_anomalies,
            positive_anomalies=positive_anomalies,
            corr_z=corr_z,
            stress_score=market_stress_score,
        )

        severity = classify_severity(
            negative_breadth=negative_breadth,
            severe_breadth=severe_decline_breadth,
            mean_return=mean_return,
            anomaly_breadth=anomaly_breadth,
            negative_anomalies=negative_anomalies,
            positive_anomalies=positive_anomalies,
            stress_score=market_stress_score,
        )

        # Build individual stock results table
        stock_results = []
        for _, row in day_df.iterrows():
            stock_results.append({
                "Symbol": row["CanonicalSymbol"],
                "Return": clean_val(row["Return"]),
                "Volatility_20": clean_val(row["Volatility_20"]),
                "Volume_Ratio": clean_val(row["Volume_Ratio"]),
                "Anomaly": int(row["Anomaly"]),
                "Anomaly_Score": clean_val(row["Anomaly_Score"]),
                "Is_Anomaly": bool(row["Anomaly"] == -1),
            })
        stock_results.sort(key=lambda s: (not s["Is_Anomaly"], s["Anomaly_Score"]))

        # SHAP explanations
        shap_res = self.explain_date_anomalies(analysis_date, day_df=day_df)
        explanations = shap_res.get("Explanations", [])

        if anomalies_detected == 0 and severity == "CRITICAL":
            warnings.append(
                "CRITICAL market shock detected via breadth override (negative breadth >= 90%, severe decline >= 10%). Zero individual stocks breached the 1% multivariate contamination threshold."
            )

        return {
            "analysis_date": analysis_date,
            "data_source": "historical",
            "observations_available": True,
            "stocks_analyzed": stocks_analyzed,
            "anomalies_detected": anomalies_detected,
            "anomaly_breadth": clean_val(round(anomaly_breadth, 4)),
            "negative_breadth": clean_val(round(negative_breadth, 4)),
            "severe_decline_breadth": clean_val(round(severe_decline_breadth, 4)),
            "mean_return": clean_val(round(mean_return, 4)),
            "rolling_correlation": clean_val(round(rolling_corr, 4)) if rolling_corr is not None else None,
            "correlation_z": clean_val(round(corr_z, 2)) if corr_z is not None else None,
            "market_stress_score": clean_val(round(market_stress_score, 2)) if market_stress_score is not None else None,
            "event_type": event_type,
            "severity": severity,
            "affected_stocks": affected_stocks,
            "stock_results": stock_results,
            "explanations": explanations,
            "warnings": warnings,
        }

    def _compute_rolling_correlation_for_date(self, target_date_str: str) -> Optional[float]:
        """Compute 60-day average pairwise correlation from historical stream."""
        try:
            target_dt = pd.to_datetime(target_date_str)
            dates = self.stream_df["Date"].drop_duplicates().sort_values().reset_index(drop=True)
            matches = dates[dates == target_dt]
            if matches.empty:
                return None
            idx = matches.index[0]
            if idx < 39:  # Need minimum overlapping window
                return None
            window_dates = dates.iloc[max(0, idx - 59): idx + 1]
            sub = self.stream_df[self.stream_df["Date"].isin(window_dates)].pivot(
                index="Date", columns="CanonicalSymbol", values="Return"
            )
            corr = sub.corr(min_periods=40)
            vals = corr.values[~np.eye(corr.shape[0], dtype=bool)]
            vals = vals[~np.isnan(vals)]
            if len(vals) == 0:
                return None
            return float(vals.mean())
        except Exception as e:
            logger.debug(f"Rolling correlation computation skipped: {e}")
            return None

    # ---------------------------------------------------------
    # FEATURE TWO: Live Market Surveillance Mode
    # ---------------------------------------------------------
    def analyze_live_market(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetch latest available market observations, apply model,
        compute market-wide breadth and stress metrics.
        """
        now = datetime.datetime.now()
        # Cache for 5 minutes unless force_refresh
        if (
            not force_refresh
            and self._cached_live_result is not None
            and self._cached_live_time is not None
            and (now - self._cached_live_time).total_seconds() < 300
        ):
            return self._cached_live_result

        day_df, as_of_date, err = self.live_provider.fetch_latest_observations(self.universe)

        if err or day_df is None or day_df.empty:
            return {
                "analysis_date": as_of_date or now.strftime("%Y-%m-%d"),
                "data_source": "live_daily",
                "provider": "Yahoo Finance (Daily Bars)",
                "observation_frequency": "Daily Close (End-of-Day / Delayed)",
                "is_intraday": False,
                "observations_available": False,
                "stocks_analyzed": 0,
                "anomalies_detected": 0,
                "anomaly_breadth": 0.0,
                "negative_breadth": 0.0,
                "severe_decline_breadth": 0.0,
                "mean_return": 0.0,
                "rolling_correlation": None,
                "correlation_z": None,
                "market_stress_score": None,
                "event_type": "Service Unavailable",
                "severity": "LOW",
                "affected_stocks": [],
                "stock_results": [],
                "explanations": [],
                "last_updated": now.isoformat(),
                "warnings": [
                    err or "Live market data could not be retrieved from provider.",
                    "Live mode relies on Yahoo Finance daily bars. Network interruption, market holiday, or rate limits may prevent retrieval.",
                ],
            }

        stocks_analyzed = len(day_df)
        X = day_df[FEATURES]
        preds = self.model.predict(X)
        scores = self.model.decision_function(X)

        day_df["Anomaly"] = preds
        day_df["Anomaly_Score"] = scores

        anomalies_df = day_df[day_df["Anomaly"] == -1].copy()
        anomalies_detected = len(anomalies_df)
        anomaly_breadth = anomalies_detected / stocks_analyzed if stocks_analyzed > 0 else 0.0
        affected_stocks = sorted(anomalies_df["CanonicalSymbol"].tolist())

        negative_anomalies = int(((day_df["Anomaly"] == -1) & (day_df["Return"] < 0)).sum())
        positive_anomalies = int(((day_df["Anomaly"] == -1) & (day_df["Return"] > 0)).sum())

        negative_breadth = float((day_df["Return"] < 0).mean())
        severe_decline_breadth = float((day_df["Return"] <= -0.05).mean())
        mean_return = float(day_df["Return"].mean())

        # Live correlation
        # In live mode without 60-day tick matrix, correlation is marked unavailable
        rolling_corr = None
        corr_z = None
        market_stress_score = None

        event_type = classify_event(
            negative_breadth=negative_breadth,
            severe_breadth=severe_decline_breadth,
            mean_return=mean_return,
            anomaly_breadth=anomaly_breadth,
            negative_anomalies=negative_anomalies,
            positive_anomalies=positive_anomalies,
            corr_z=corr_z,
            stress_score=market_stress_score,
        )

        severity = classify_severity(
            negative_breadth=negative_breadth,
            severe_breadth=severe_decline_breadth,
            mean_return=mean_return,
            anomaly_breadth=anomaly_breadth,
            negative_anomalies=negative_anomalies,
            positive_anomalies=positive_anomalies,
            stress_score=market_stress_score,
        )

        stock_results = []
        for _, row in day_df.iterrows():
            stock_results.append({
                "Symbol": row["CanonicalSymbol"],
                "Return": clean_val(row["Return"]),
                "Volatility_20": clean_val(row["Volatility_20"]),
                "Volume_Ratio": clean_val(row["Volume_Ratio"]),
                "Anomaly": int(row["Anomaly"]),
                "Anomaly_Score": clean_val(row["Anomaly_Score"]),
                "Is_Anomaly": bool(row["Anomaly"] == -1),
            })
        stock_results.sort(key=lambda s: (not s["Is_Anomaly"], s["Anomaly_Score"]))

        # SHAP on live anomalies
        explanations = []
        if anomalies_detected > 0:
            for i, (_, row) in enumerate(anomalies_df.iterrows()):
                X_anom = anomalies_df.iloc[[i]][FEATURES]
                shap_vals = self.explainer.shap_values(X_anom)[0]
                feat_recs = [
                    {
                        "Feature": feat,
                        "Value": clean_val(X_anom.iloc[0][feat]),
                        "SHAP": clean_val(shap_vals[j]),
                    }
                    for j, feat in enumerate(FEATURES)
                ]
                feat_recs.sort(key=lambda x: abs(x["SHAP"]), reverse=True)
                explanations.append({
                    "Symbol": row["CanonicalSymbol"],
                    "Return": clean_val(row["Return"]),
                    "Volatility_20": clean_val(row["Volatility_20"]),
                    "Volume_Ratio": clean_val(row["Volume_Ratio"]),
                    "Features": feat_recs,
                })

        warnings = [
            f"Surveillance Mode: Daily Close observation frequency ({as_of_date}).",
            "This analysis operates on daily closing bars. Genuine sub-second intraday surveillance requires an enterprise tick feed connection.",
        ]

        result = {
            "analysis_date": as_of_date,
            "data_source": "live_daily",
            "provider": "Yahoo Finance (Daily Bars)",
            "observation_frequency": "Daily Close (End-of-Day / Delayed)",
            "is_intraday": False,
            "observations_available": True,
            "stocks_analyzed": stocks_analyzed,
            "anomalies_detected": anomalies_detected,
            "anomaly_breadth": clean_val(round(anomaly_breadth, 4)),
            "negative_breadth": clean_val(round(negative_breadth, 4)),
            "severe_decline_breadth": clean_val(round(severe_decline_breadth, 4)),
            "mean_return": clean_val(round(mean_return, 4)),
            "rolling_correlation": None,
            "correlation_z": None,
            "market_stress_score": None,
            "event_type": event_type,
            "severity": severity,
            "affected_stocks": affected_stocks,
            "stock_results": stock_results,
            "explanations": explanations,
            "last_updated": now.isoformat(),
            "warnings": warnings,
        }

        self._cached_live_result = result
        self._cached_live_time = now
        return result
