import unittest
from fastapi import HTTPException
from api.routes import (
    root,
    get_system_status,
    get_events,
    get_event,
    get_event_explanation,
    analyze_date,
    analyze_live,
)
from api.services import MarketLensService

class TestMarketLens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = MarketLensService.get_instance()

    def test_01_root_endpoint(self):
        res = root()
        self.assertEqual(res["service"], "MarketLens")
        self.assertEqual(res["status"], "running")

    def test_02_status_endpoint(self):
        res = get_system_status()
        self.assertTrue(res.model_loaded)
        self.assertEqual(res.consolidated_events_count, 7)
        self.assertGreater(res.active_universe_size, 0)
        self.assertIn("start", res.historical_date_range)

    def test_03_get_all_events(self):
        events = get_events()
        self.assertEqual(len(events), 7)
        event_ids = [e["Event_ID"] if isinstance(e, dict) else e.Event_ID for e in events]
        self.assertIn("E20200312-03", event_ids)
        self.assertIn("E20200316-04", event_ids)
        self.assertIn("E20200323-07", event_ids)

    def test_04_get_event_filters(self):
        critical_events = get_events(severity="CRITICAL")
        self.assertGreaterEqual(len(critical_events), 5)
        for ev in critical_events:
            sev = ev["Severity"] if isinstance(ev, dict) else ev.Severity
            self.assertEqual(sev, "CRITICAL")

    def test_05_get_single_event_march23(self):
        ev = get_event("E20200323-07")
        peak_date = ev["Peak_Date"] if isinstance(ev, dict) else ev.Peak_Date
        sev = ev["Severity"] if isinstance(ev, dict) else ev.Severity
        aff = ev["Affected_Stocks"] if isinstance(ev, dict) else ev.Affected_Stocks
        self.assertEqual(peak_date, "2020-03-23")
        self.assertEqual(sev, "CRITICAL")
        self.assertEqual(len(aff), 7)
        self.assertIn("AXISBANK", aff)

    def test_06_get_single_event_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            get_event("E99999999-99")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_07_explanation_march23_with_anomalies(self):
        data = get_event_explanation("E20200323-07")
        anomalies = data["Anomalies"] if isinstance(data, dict) else data.Anomalies
        explanations = data["Explanations"] if isinstance(data, dict) else data.Explanations
        self.assertEqual(anomalies, 7)
        self.assertEqual(len(explanations), 7)
        first_stock = explanations[0]
        sym = first_stock["Symbol"] if isinstance(first_stock, dict) else first_stock.Symbol
        feats = first_stock["Features"] if isinstance(first_stock, dict) else first_stock.Features
        self.assertTrue(sym)
        self.assertEqual(len(feats), 3)
        feature_names = [f["Feature"] if isinstance(f, dict) else f.Feature for f in feats]
        self.assertIn("Return", feature_names)
        self.assertIn("Volatility_20", feature_names)
        self.assertIn("Volume_Ratio", feature_names)

    def test_08_explanation_march16_zero_anomalies(self):
        data = get_event_explanation("E20200316-04")
        anomalies = data["Anomalies"] if isinstance(data, dict) else data.Anomalies
        explanations = data["Explanations"] if isinstance(data, dict) else data.Explanations
        self.assertEqual(anomalies, 0)
        self.assertEqual(len(explanations), 0)

    def test_09_historical_date_analysis_march16(self):
        """Regression test: March 16 has 0 IF anomalies but CRITICAL severity via breadth override."""
        res = analyze_date("2020-03-16")
        self.assertEqual(res["analysis_date"], "2020-03-16")
        self.assertTrue(res["observations_available"])
        self.assertEqual(res["stocks_analyzed"], 47)
        self.assertEqual(res["anomalies_detected"], 0)
        self.assertEqual(res["negative_breadth"], 1.0)
        self.assertGreater(res["severe_decline_breadth"], 0.70)
        self.assertLess(res["mean_return"], -0.05)
        self.assertEqual(res["event_type"], "Broad Market Downside Shock")
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertEqual(res["affected_stocks"], [])

    def test_10_historical_date_analysis_march23(self):
        """Regression test: March 23 has 7 IF anomalies, high stress, CRITICAL severity."""
        res = analyze_date("2020-03-23")
        self.assertEqual(res["analysis_date"], "2020-03-23")
        self.assertEqual(res["stocks_analyzed"], 47)
        self.assertEqual(res["anomalies_detected"], 7)
        self.assertEqual(
            res["affected_stocks"],
            ["AXISBANK", "BAJAJFINSV", "BAJFINANCE", "INDUSINDBK", "ONGC", "VEDL", "ZEEL"]
        )
        self.assertEqual(res["event_type"], "Broad Market Downside Shock")
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertEqual(len(res["explanations"]), 7)

    def test_11_historical_date_analysis_march12(self):
        """Regression test: March 12 has 2 IF anomalies and highest stress ~65.14."""
        res = analyze_date("2020-03-12")
        self.assertEqual(res["stocks_analyzed"], 47)
        self.assertEqual(res["anomalies_detected"], 2)
        self.assertEqual(res["affected_stocks"], ["ONGC", "VEDL"])
        self.assertIsNotNone(res["market_stress_score"])
        self.assertEqual(round(res["market_stress_score"], 1), 65.1)
        self.assertEqual(res["severity"], "CRITICAL")

    def test_12_historical_date_unlisted_in_events_2008(self):
        """Test date analysis on a date not in market_events.csv (2008-10-24)."""
        res = analyze_date("2008-10-24")
        self.assertTrue(res["observations_available"])
        self.assertEqual(res["stocks_analyzed"], 45)
        self.assertEqual(res["anomalies_detected"], 10)
        self.assertEqual(res["negative_breadth"], 1.0)
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertEqual(len(res["affected_stocks"]), 10)

    def test_13_historical_date_weekend_or_holiday(self):
        """Test non-trading date (Sunday 2020-03-15)."""
        res = analyze_date("2020-03-15")
        self.assertFalse(res["observations_available"])
        self.assertEqual(res["event_type"], "Non-Trading Day")
        self.assertGreater(len(res["warnings"]), 0)

    def test_14_historical_date_out_of_bounds(self):
        """Test date before historical range."""
        res = analyze_date("1995-05-10")
        self.assertFalse(res["observations_available"])
        self.assertEqual(res["event_type"], "Out of Range")

    def test_15_historical_date_invalid_format(self):
        """Test invalid date format error."""
        with self.assertRaises(HTTPException) as ctx:
            analyze_date("invalid-format")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_16_live_analysis_endpoint(self):
        """Test live market endpoint response structure."""
        data = analyze_live(force_refresh=False)
        self.assertEqual(data["data_source"], "live_daily")
        self.assertIn("observation_frequency", data)
        self.assertFalse(data["is_intraday"])
        self.assertIn("last_updated", data)
        self.assertIsInstance(data["warnings"], list)

if __name__ == "__main__":
    unittest.main(verbosity=2)
