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

    explanations = []

    for i, (_, row) in enumerate(
        anomalies_today.iterrows()
    ):

        X_anomaly = anomalies_today.iloc[[i]][features]

        shap_values = explainer.shap_values(
            X_anomaly
        )[0]

        explanation = pd.DataFrame({
            "Feature": features,
            "Value": X_anomaly.iloc[0].values,
            "SHAP": shap_values
        })

        explanation["Abs_SHAP"] = (
            explanation["SHAP"].abs()
        )

        explanation = explanation.sort_values(
            "Abs_SHAP",
            ascending=False
        )

        explanations.append({
            "Symbol": row["CanonicalSymbol"],
            "Return": float(row["Return"]),
            "Volatility_20": float(row["Volatility_20"]),
            "Volume_Ratio": float(row["Volume_Ratio"]),
            "Features": [
                {
                    "Feature": feature,
                    "Value": float(value),
                    "SHAP": float(shap_value)
                }
                for feature, value, shap_value
                in zip(
                    explanation["Feature"],
                    explanation["Value"],
                    explanation["SHAP"]
                )
            ]
        })

    return {
        "Event_Date": event_date.strftime("%Y-%m-%d"),
        "Anomalies": len(explanations),
        "Explanations": explanations
    }
# Test