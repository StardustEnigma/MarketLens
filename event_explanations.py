import pandas as pd
import joblib
import shap


# ---------------------------------------
# Load model
# ---------------------------------------

model = joblib.load(
    "models/isolation_forest.joblib"
)

explainer = shap.TreeExplainer(model)


# ---------------------------------------
# Load test data
# ---------------------------------------

df = pd.read_csv(
    "Dataset/market_stream.csv"
)

df["Date"] = pd.to_datetime(df["Date"])


# ---------------------------------------
# Load anomaly results
# ---------------------------------------

anomalies = pd.read_csv(
    "Dataset/daily_anomalies.csv"
)

anomalies["Date"] = pd.to_datetime(
    anomalies["Date"]
)


# ---------------------------------------
# Features used by Isolation Forest
# ---------------------------------------

features = [
    "Return",
    "Volatility_20",
    "Volume_Ratio"
]
def get_affected_stocks(event_date):

    event_date = pd.Timestamp(event_date)

    day = df[df["Date"] == event_date].copy()

    day = day.dropna(subset=features)

    predictions = model.predict(day[features])

    day["Anomaly"] = predictions

    return day.loc[
        day["Anomaly"] == -1,
        "CanonicalSymbol"
    ].tolist()



# ---------------------------------------
# Generate explanations
def explain_event(event_date):

    event_date = pd.Timestamp(event_date)

    day = df[df["Date"] == event_date].copy()

    day = day.dropna(subset=features)

    predictions = model.predict(day[features])

    day["Anomaly"] = predictions

    anomalies_today = day[
        day["Anomaly"] == -1
    ].copy()

    print(f"Event date: {event_date.date()}")
    print(f"Anomalies found: {len(anomalies_today)}")

    if len(anomalies_today) == 0:
        print("No anomalies found.")

        return {
            "Event_Date": str(event_date.date()),
            "Anomalies": 0,
            "Explanations": []
        }

    X_anomalies = anomalies_today[features]

    shap_values = explainer.shap_values(
        X_anomalies
    )

    explanations = []

    for i, (_, row) in enumerate(
        anomalies_today.iterrows()
    ):

        values = shap_values[i]

        explanation = pd.DataFrame({
            "Feature": features,
            "SHAP": values,
            "Value": X_anomalies.iloc[i].values
        })

        explanation["Abs_SHAP"] = (
            explanation["SHAP"].abs()
        )

        explanation = explanation.sort_values(
            "Abs_SHAP",
            ascending=False
        )

        print(
            f"\n{row['CanonicalSymbol']} | "
            f"Return={row['Return']:.4f} | "
            f"Volume_Ratio={row['Volume_Ratio']:.2f}"
        )

        print(
            explanation[
                ["Feature", "Value", "SHAP"]
            ].to_string(index=False)
        )

        feature_explanations = []

        for _, feature_row in explanation.iterrows():

            feature_explanations.append({
                "Feature": feature_row["Feature"],
                "Value": float(feature_row["Value"]),
                "SHAP": float(feature_row["SHAP"])
            })

        explanations.append({
            "Symbol": row["CanonicalSymbol"],
            "Return": float(row["Return"]),
            "Volatility_20": float(row["Volatility_20"]),
            "Volume_Ratio": float(row["Volume_Ratio"]),
            "Features": feature_explanations
        })

    return {
        "Event_Date": str(event_date.date()),
        "Anomalies": len(explanations),
        "Explanations": explanations
    }


# Test