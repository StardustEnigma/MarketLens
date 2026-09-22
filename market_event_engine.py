import pandas as pd

from event_explanations import explain_event
# ---------------------------------------
# Load data
# ---------------------------------------

anomalies = pd.read_csv("Dataset/daily_anomalies.csv")
correlation = pd.read_csv("Dataset/streamed_correlation.csv")

anomalies["Date"] = pd.to_datetime(anomalies["Date"])
correlation["Date"] = pd.to_datetime(correlation["Date"])


# ---------------------------------------
# Merge
# ---------------------------------------

events = anomalies.merge(
    correlation,
    on="Date",
    how="inner"
)

print("Combined event data:")
print(events.tail(10))


# ---------------------------------------
# Calculate market stress
# ---------------------------------------

events["Anomaly_Score"] = (
    events["Anomaly_Breadth"] * 100
)

events["Correlation_Score"] = (
    events["Correlation_Z"]
    .clip(lower=0, upper=6)
    / 6
    * 100
)

events["Market_Stress_Score"] = (
    0.5 * events["Anomaly_Score"]
    + 0.5 * events["Correlation_Score"]
)


# ---------------------------------------
# Classify market event
# ---------------------------------------

def classify_event(row):

    stress = row["Market_Stress_Score"]
    breadth = row["Anomaly_Breadth"]

    total_anomalies = (
        row["Negative_Anomalies"]
        + row["Positive_Anomalies"]
    )

    if total_anomalies == 0:
        negative_ratio = 0
        positive_ratio = 0
    else:
        negative_ratio = (
            row["Negative_Anomalies"] / total_anomalies
        )

        positive_ratio = (
            row["Positive_Anomalies"] / total_anomalies
        )

    correlation_score = (
        min(max(row["Correlation_Z"], 0), 6)
        / 6
        * 100
    )

    if stress >= 40 and breadth >= 0.10:

        if negative_ratio >= 0.75:
            return "Broad Market Downside Shock"

        elif positive_ratio >= 0.75:
            return "Broad Market Upside Shock"

    if correlation_score >= 80 and breadth < 0.10:
        return "Market-Wide Synchronization"

    if stress >= 25:
        return "Elevated Market Stress"

    return "Normal"


# ---------------------------------------
# Apply event engine
# ---------------------------------------

events["Event_Type"] = events.apply(
    classify_event,
    axis=1
)


# ---------------------------------------
# Final output
# ---------------------------------------

print("\nMarket Events:")

print(
    events[
        [
            "Date",
            "Market_Stress_Score",
            "Event_Type"
        ]
    ].tail(10)
)
# ---------------------------------------
# Explain detected event
# ---------------------------------------

event_date = events.iloc[-1]["Date"]

print("\nSHAP Event Explanation:")
explain_event(event_date)
# ---------------------------------------
# Save market events
# ---------------------------------------

events.to_csv(
    "Dataset/market_events.csv",
    index=False
)

print("\nSaved market events to:")
print("Dataset/market_events.csv")
print(f"\nTotal events generated: {len(events)}")