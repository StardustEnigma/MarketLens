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
    corr_z = row["Correlation_Z"]
    negative = row["Negative_Anomalies"]

    # Strong broad downside movement
    if breadth >= 0.10 and negative >= 5:
        return "Broad Market Downside Shock"

    # Strong market-wide synchronization
    if corr_z >= 4.0:
        return "Market-Wide Synchronization"

    # Significant anomaly breadth
    if breadth >= 0.05:
        return "Elevated Market Stress"

    # High combined stress
    if stress >= 40:
        return "High Market Stress"

    return "Normal"
# ---------------------------------------
# Apply event engine
# ---------------------------------------

events["Event_Type"] = events.apply(
    classify_event,
    axis=1
)
def classify_severity(score):
    if score >= 40:
        return "CRITICAL"
    elif score >= 25:
        return "HIGH"
    elif score >= 15:
        return "MEDIUM"
    else:
        return "LOW"

def calculate_event_duration(events, threshold=15):
    durations = []
    current_duration = 0

    for score in events["Market_Stress_Score"]:
        if score >= threshold:
            current_duration += 1
        else:
            current_duration = 0

        durations.append(current_duration)

    return durations

events["Severity"] = events["Market_Stress_Score"].apply(
    classify_severity
)
events["Event_Duration"] = calculate_event_duration(events)

# ---------------------------------------
# Final output
# ---------------------------------------


print("\nMarket Events:")
print(events[[
    "Date",
    "Market_Stress_Score",
    "Severity",
    "Event_Type",
    "Event_Duration"
]])
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