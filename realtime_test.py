import argparse
import pandas as pd
import joblib
import yfinance as yf


# ---------------------------------------
# Configuration
# ---------------------------------------

MODEL_PATH = "models/isolation_forest.joblib"
HISTORICAL_DATA = "Dataset/market_stream.csv"

FEATURES = [
    "Return",
    "Volatility_20",
    "Volume_Ratio"
]


# ---------------------------------------
# Load model
# ---------------------------------------

def load_model():

    model = joblib.load(MODEL_PATH)

    print("Isolation Forest loaded.")

    return model


# ---------------------------------------
# Load stock universe
# ---------------------------------------

def load_stock_universe():

    historical = pd.read_csv(
        HISTORICAL_DATA
    )

    stocks = (
        historical["CanonicalSymbol"]
        .dropna()
        .unique()
        .tolist()
    )

    print(
        f"Stock universe: {len(stocks)} stocks"
    )

    return stocks


# ---------------------------------------
# Convert NSE -> Yahoo symbols
# ---------------------------------------

def yahoo_symbol(symbol):

    if symbol == "M&M":
        return "M&M.NS"

    if symbol == "BAJAJ-AUTO":
        return "BAJAJ-AUTO.NS"

    return f"{symbol}.NS"


# ---------------------------------------
# Feature engineering
# ---------------------------------------

def engineer_features(stock_data):

    stock_data = stock_data.copy()

    stock_data = stock_data.dropna(
        subset=["Close", "Volume"]
    )

    if len(stock_data) < 21:
        return None

    stock_data["Return"] = (
        stock_data["Close"]
        .pct_change()
    )

    stock_data["Volatility_20"] = (
        stock_data["Return"]
        .rolling(20)
        .std()
    )

    stock_data["Volume_Ratio"] = (
        stock_data["Volume"]
        /
        stock_data["Volume"]
        .rolling(20)
        .mean()
    )

    return stock_data


# ---------------------------------------
# Download market data
# ---------------------------------------

def download_market_data(
    stocks,
    target_date=None
):

    print("\nDownloading market data...")

    rows = []

    for stock in stocks:

        yahoo = yahoo_symbol(stock)

        try:

            if target_date:

                target = pd.Timestamp(
                    target_date
                )

                start = (
                    target
                    - pd.Timedelta(days=45)
                )

                end = (
                    target
                    + pd.Timedelta(days=1)
                )

                stock_data = yf.download(
                    yahoo,
                    start=start,
                    end=end,
                    interval="1d",
                    auto_adjust=False,
                    progress=False,
                    threads=False
                )

            else:

                stock_data = yf.download(
                    yahoo,
                    period="3mo",
                    interval="1d",
                    auto_adjust=False,
                    progress=False,
                    threads=False
                )

            if stock_data.empty:
                continue

            # Handle yfinance MultiIndex
            if isinstance(
                stock_data.columns,
                pd.MultiIndex
            ):

                stock_data.columns = (
                    stock_data
                    .columns
                    .get_level_values(0)
                )

            stock_data = engineer_features(
                stock_data
            )

            if stock_data is None:
                continue

            # -----------------------------------
            # Select target/latest date
            # -----------------------------------

            if target_date:

                target = pd.Timestamp(
                    target_date
                )

                matching = stock_data[
                    stock_data.index.normalize()
                    == target.normalize()
                ]

                if matching.empty:
                    continue

                latest = matching.iloc[-1]

                actual_date = matching.index[-1]

            else:

                latest = stock_data.iloc[-1]

                actual_date = (
                    stock_data.index[-1]
                )

            # -----------------------------------
            # Validate features
            # -----------------------------------

            if latest[FEATURES].isna().any():
                continue

            rows.append({

                "CanonicalSymbol": stock,

                "Date": actual_date,

                "Return": float(
                    latest["Return"]
                ),

                "Volatility_20": float(
                    latest["Volatility_20"]
                ),

                "Volume_Ratio": float(
                    latest["Volume_Ratio"]
                )
            })

        except Exception as e:

            print(
                f"Skipping {stock}: {e}"
            )

    return pd.DataFrame(
        rows,
        columns=[
            "CanonicalSymbol",
            "Date",
            "Return",
            "Volatility_20",
            "Volume_Ratio"
        ]
    )


# ---------------------------------------
# Detect anomalies
# ---------------------------------------

def detect_anomalies(
    model,
    market_data
):

    if market_data.empty:
        return market_data

    result = market_data.copy()

    result["Anomaly_Score"] = (
        model.decision_function(
            result[FEATURES]
        )
    )

    result["Anomaly"] = (
        model.predict(
            result[FEATURES]
        )
    )

    print("\nLowest anomaly scores — April 7 diagnostic:")
    print(
        result.sort_values("Anomaly_Score")
        [["CanonicalSymbol", "Return",
          "Volatility_20", "Volume_Ratio", "Anomaly_Score"]]
        .head(10)
        .to_string(index=False)
    )

    return result


# ---------------------------------------
# Build market event
# ---------------------------------------

def build_market_event(
    market_data
):

    if market_data.empty:
        return None

    anomalies = market_data[
        market_data["Anomaly"] == -1
    ].copy()

    latest_date = (
        market_data["Date"]
        .max()
    )

    breadth = (
        len(anomalies)
        /
        len(market_data)
    )

    event = {

        "Event_Date":
            latest_date.strftime("%Y-%m-%d"),

        "Stocks_Analyzed":
            len(market_data),

        "Anomalies":
            len(anomalies),

        "Anomaly_Breadth":
            round(breadth, 4),

        "Affected_Stocks":
            anomalies[
                "CanonicalSymbol"
            ].tolist(),

        "Is_Event":
            len(anomalies) > 0
    }

    return event


# ---------------------------------------
# Run complete detection pipeline
# ---------------------------------------

def run_detection(
    target_date=None
):

    model = load_model()

    stocks = load_stock_universe()

    market_data = download_market_data(
        stocks,
        target_date
    )

    if market_data.empty:

        print(
            "\nNo valid market data found."
        )

        return None, None

    market_data = detect_anomalies(
        model,
        market_data
    )

    event = build_market_event(
        market_data
    )

    return market_data, event


# ---------------------------------------
# Display results
# ---------------------------------------

def display_results(
    market_data,
    event,
    target_date=None
):

    print("\n" + "=" * 60)

    if target_date:

        print(
            "MARKETLENS — "
            "HISTORICAL MARKET ANOMALY TEST"
        )

    else:

        print(
            "MARKETLENS — "
            "CURRENT MARKET ANOMALY TEST"
        )

    print("=" * 60)

    print(
        f"\nTrading date: "
        f"{event['Event_Date']}"
    )

    print(
        f"Stocks analyzed: "
        f"{event['Stocks_Analyzed']}"
    )

    negative_breadth = (market_data["Return"] < 0).mean()
    severe_decline_breadth = (market_data["Return"] <= -0.05).mean()
    market_return = market_data["Return"].mean()
    print(f"Negative breadth: {negative_breadth:.2%}")
    print(f"Severe-decline breadth: {severe_decline_breadth:.2%}")
    print(f"Mean stock return: {market_return:.2%}")

    print(
        f"Anomalies detected: "
        f"{event['Anomalies']}"
    )

    print(
        f"Anomaly breadth: "
        f"{event['Anomaly_Breadth']:.2%}"
    )

    print("\nAnomalous stocks:")

    anomalies = market_data[
        market_data["Anomaly"] == -1
    ].copy()

    if anomalies.empty:

        print("None")

    else:

        output = anomalies[
            [
                "CanonicalSymbol",
                "Return",
                "Volatility_20",
                "Volume_Ratio",
                "Anomaly_Score"
            ]
        ].sort_values(
            "Anomaly_Score"
        )

        print(
            output.to_string(
                index=False
            )
        )

    print("\nTest complete.")


# ---------------------------------------
# CLI
# ---------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Test a specific trading date YYYY-MM-DD"
    )

    args = parser.parse_args()

    if args.date:

        print(
            f"Testing MarketLens on: "
            f"{args.date}"
        )

    market_data, event = run_detection(
        args.date
    )

    if market_data is not None:

        display_results(
            market_data,
            event,
            args.date
        )