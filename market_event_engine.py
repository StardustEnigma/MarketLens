import pandas as pd
from event_explanations import (
    explain_event,
    get_affected_stocks
)

# ---------------------------------------
# Load data
# ---------------------------------------

anomalies = pd.read_csv(
    "Dataset/daily_anomalies.csv"
)

correlation = pd.read_csv(
    "Dataset/streamed_correlation.csv"
)

anomalies["Date"] = pd.to_datetime(
    anomalies["Date"]
)

correlation["Date"] = pd.to_datetime(
    correlation["Date"]
)


# ---------------------------------------
# Merge
# ---------------------------------------

events = anomalies.merge(
    correlation,
    on="Date",
    how="inner"
)

events = events.sort_values(
    "Date"
).reset_index(drop=True)

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

    breadth = row["Anomaly_Breadth"]
    corr_z = row["Correlation_Z"]
    negative = row["Negative_Anomalies"]
    positive = row["Positive_Anomalies"]
    stress = row["Market_Stress_Score"]

    # Broad downside shock
    if (
        breadth >= 0.10
        and negative >= 5
        and negative > positive
    ):
        return "Broad Market Downside Shock"

    # Market-wide synchronization
    if corr_z >= 4.0:
        return "Market-Wide Synchronization"

    # Elevated anomaly breadth
    if breadth >= 0.05:
        return "Elevated Market Stress"

    # High combined stress
    if stress >= 40:
        return "High Market Stress"

    return "Normal"


events["Event_Type"] = events.apply(
    classify_event,
    axis=1
)


# ---------------------------------------
# Severity
# ---------------------------------------

def classify_severity(row):

    score = row["Market_Stress_Score"]
    breadth = row["Anomaly_Breadth"]
    negative = row["Negative_Anomalies"]
    positive = row["Positive_Anomalies"]

    # Broad downside override
    if (
        breadth >= 0.10
        and negative >= 5
        and negative > positive
    ):
        return "CRITICAL"

    if score >= 40:
        return "CRITICAL"

    elif score >= 25:
        return "HIGH"

    elif score >= 15:
        return "MEDIUM"

    else:
        return "LOW"


events["Severity"] = events.apply(
    classify_severity,
    axis=1
)


# ---------------------------------------
# Get affected stocks
# ---------------------------------------

events["Affected_Stocks"] = events.apply(
    lambda row: (
        get_affected_stocks(row["Date"])
        if row["Event_Type"] != "Normal"
        else []
    ),
    axis=1
)


# ---------------------------------------
# Consolidate consecutive events
# ---------------------------------------

def consolidate_events(events):

    consolidated = []

    current_event = None
    event_counter = 0

    for _, row in events.iterrows():

        event_type = row["Event_Type"]

        # ---------------------------------------
        # Normal day
        # ---------------------------------------

        if event_type == "Normal":

            if current_event is not None:
                consolidated.append(current_event)
                current_event = None

            continue

        # ---------------------------------------
        # Start new event
        # ---------------------------------------

        if (
            current_event is None
            or current_event["Event_Type"] != event_type
        ):

            # Close previous event
            if current_event is not None:
                consolidated.append(current_event)

            event_counter += 1

            event_id = (
                f"E{row['Date'].strftime('%Y%m%d')}-"
                f"{event_counter:02d}"
            )

            current_event = {
                "Event_ID": event_id,
                "Start_Date": row["Date"],
                "End_Date": row["Date"],
                "Event_Type": event_type,
                "Duration": 1,
                "Peak_Stress": row["Market_Stress_Score"],
                "Peak_Date": row["Date"],
                "Severity": row["Severity"],
                "Affected_Stocks": set(
                    row["Affected_Stocks"]
                )
            }

        # ---------------------------------------
        # Continue existing event
        # ---------------------------------------

        else:

            current_event["End_Date"] = row["Date"]

            current_event["Duration"] += 1

            current_event["Affected_Stocks"].update(
                row["Affected_Stocks"]
            )

            # Keep highest severity
            severity_rank = {
                "LOW": 1,
                "MEDIUM": 2,
                "HIGH": 3,
                "CRITICAL": 4
            }

            if (
                severity_rank[row["Severity"]]
                > severity_rank[current_event["Severity"]]
            ):
                current_event["Severity"] = row["Severity"]

            # Update peak stress
            if (
                row["Market_Stress_Score"]
                > current_event["Peak_Stress"]
            ):

                current_event["Peak_Stress"] = (
                    row["Market_Stress_Score"]
                )

                current_event["Peak_Date"] = (
                    row["Date"]
                )

    # ---------------------------------------
    # Close final event
    # ---------------------------------------

    if current_event is not None:
        consolidated.append(current_event)

    # ---------------------------------------
    # Convert sets to sorted lists
    # ---------------------------------------

    for event in consolidated:

        event["Affected_Stocks"] = sorted(
            event["Affected_Stocks"]
        )

    return pd.DataFrame(consolidated)


# ---------------------------------------
# Build consolidated event table
# ---------------------------------------

market_events = consolidate_events(events)


# ---------------------------------------
# Display consolidated events
# ---------------------------------------

print("\nConsolidated Market Events:")

print(
    market_events[
        [
            "Event_ID",
            "Start_Date",
            "End_Date",
            "Duration",
            "Event_Type",
            "Severity",
            "Peak_Stress",
            "Peak_Date",
            "Affected_Stocks"
        ]
    ].to_string(index=False)
)


# ---------------------------------------
# SHAP explanation
# ---------------------------------------

if len(market_events) > 0:

    # Use peak stress date of latest event
    latest_event = market_events.iloc[-1]

    peak_date = latest_event["Peak_Date"]

    print("\nSHAP Event Explanation:")
    explain_event(peak_date)


# ---------------------------------------
# Save consolidated events
# ---------------------------------------

market_events.to_csv(
    "Dataset/market_events.csv",
    index=False
)

print(
    "\nSaved consolidated market events to:"
)

print(
    "Dataset/market_events.csv"
)

print(
    f"\nTotal consolidated events: "
    f"{len(market_events)}"
)