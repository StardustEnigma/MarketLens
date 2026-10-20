import pandas as pd

breadth = pd.read_csv("Dataset/breadth_evaluation.csv")
anomalies = pd.read_csv("Dataset/daily_anomalies.csv")
correlation = pd.read_csv("Dataset/streamed_correlation.csv")

for df in (breadth, anomalies, correlation):
    df["Date"] = pd.to_datetime(df["Date"])

# Keep one row per date in each source before joining
anomalies = anomalies.drop_duplicates("Date")
correlation = correlation.drop_duplicates("Date")

comparison = (
    breadth.merge(anomalies, on="Date", how="left",
                  suffixes=("", "_anomaly"))
    .merge(correlation, on="Date", how="left",
           suffixes=("", "_correlation"))
)

flagged = comparison[comparison["Downside_Shock"]].copy()

print("Breadth flags:", len(flagged))
print("Dates overlapping anomaly data:",
      flagged["Anomaly_Breadth"].notna().sum())
print("Dates overlapping correlation data:",
      flagged["Correlation_Z"].notna().sum())

if "Anomaly_Breadth" in flagged.columns:
    has_anomaly = flagged["Anomaly_Breadth"].fillna(0) > 0
    print("Flags with IF anomaly breadth > 0:", has_anomaly.sum())
    print("Flags with no IF anomalies:", (~has_anomaly).sum())

if "Correlation_Z" in flagged.columns:
    print("Flags with correlation Z >= 4:",
          (flagged["Correlation_Z"].fillna(0) >= 4).sum())
