import pandas as pd

stream = pd.read_csv("Dataset/market_stream.csv")
stream["Date"] = pd.to_datetime(stream["Date"])

# Calculate market-wide metrics for every historical trading date
daily = (
    stream.groupby("Date")
    .agg(
        Stock_Count=("CanonicalSymbol", "nunique"),
        Negative_Breadth=("Return", lambda s: (s < 0).mean()),
        Severe_Decline_Breadth=("Return", lambda s: (s <= -0.05).mean()),
        Mean_Return=("Return", "mean"),
    )
    .reset_index()
)

# Candidate rule — evaluate, don't finalize yet
daily["Downside_Shock"] = (
    (daily["Negative_Breadth"] >= 0.90)
    & (daily["Severe_Decline_Breadth"] >= 0.10)
    & (daily["Mean_Return"] <= -0.02)
)

print("\n=== HISTORICAL BREADTH EVALUATION ===")
print(f"Trading dates: {len(daily):,}")
print(f"Date range: {daily['Date'].min().date()} to "
      f"{daily['Date'].max().date()}")
print(f"Dates flagged: {daily['Downside_Shock'].sum():,}")
print(f"Flag rate: {daily['Downside_Shock'].mean():.2%}")

print("\n=== FLAGGED DATES BY YEAR ===")
flagged = daily[daily["Downside_Shock"]]
print(flagged.groupby(flagged["Date"].dt.year).size().to_string())

print("\n=== 20 MOST SEVERE FLAGGED DATES ===")
print(
    flagged.sort_values("Mean_Return")
    [["Date", "Stock_Count", "Negative_Breadth",
      "Severe_Decline_Breadth", "Mean_Return"]]
    .head(20)
    .to_string(index=False, formatters={
        "Negative_Breadth": "{:.2%}".format,
        "Severe_Decline_Breadth": "{:.2%}".format,
        "Mean_Return": "{:.2%}".format,
    })
)

print("\n=== KNOWN HISTORICAL CHECK ===")
for date in ["2020-03-23", "2020-03-09", "2020-03-12"]:
    row = daily[daily["Date"] == date]
    if row.empty:
        print(f"{date}: date not found")
    else:
        print(row.to_string(index=False))

daily.to_csv("Dataset/breadth_evaluation.csv", index=False)
print("\nSaved full evaluation to Dataset/breadth_evaluation.csv")
