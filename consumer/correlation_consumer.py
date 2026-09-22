import json
import numpy as np
import pandas as pd
from collections import defaultdict
from kafka import KafkaConsumer


consumer = KafkaConsumer(
    "market-events",
    bootstrap_servers="localhost:9092",
    group_id="correlation-engine-004",
    auto_offset_reset="earliest",
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)


# ---------------------------------------
# Collect streamed market data
# ---------------------------------------

daily_data = defaultdict(dict)

print("Collecting market data...")

message_count = 0

for message in consumer:

    event = message.value

    date = event["date"]
    symbol = event["symbol"]

    daily_data[date][symbol] = event["return"]

    message_count += 1

    if message_count == 3713:
        break


consumer.close()


print("\nFinished!")
print(f"Messages: {message_count}")
print(f"Trading dates: {len(daily_data)}")


# ---------------------------------------
# Build Date × Stock return matrix
# ---------------------------------------

returns_matrix = pd.DataFrame.from_dict(
    daily_data,
    orient="index"
)

returns_matrix.index = pd.to_datetime(
    returns_matrix.index
)

returns_matrix = returns_matrix.sort_index()

print(f"Return matrix: {returns_matrix.shape}")


# ---------------------------------------
# Calculate rolling correlation
# ---------------------------------------

rolling_correlations = {}

dates = returns_matrix.index

for i in range(59, len(dates)):

    date = dates[i]

    window = returns_matrix.iloc[i - 59:i + 1]

    corr = window.corr(min_periods=40)

    values = corr.values

    # Remove diagonal
    mask = ~np.eye(
        values.shape[0],
        dtype=bool
    )

    values = values[mask]

    # Remove NaN correlations
    values = values[~np.isnan(values)]

    if len(values) > 0:

        average_correlation = values.mean()

        rolling_correlations[date] = average_correlation


# ---------------------------------------
# Calculate correlation Z-score
# ---------------------------------------

correlation_results = []

correlation_dates = list(
    rolling_correlations.keys()
)

for i, date in enumerate(correlation_dates):

    current_correlation = rolling_correlations[date]

    # Need previous observations for baseline
    previous = correlation_dates[:i]

    if len(previous) < 5:
        continue

    previous_values = [
        rolling_correlations[d]
        for d in previous
    ]

    mean = np.mean(previous_values)
    std = np.std(previous_values, ddof=1)

    if std == 0:
        z_score = 0.0
    else:
        z_score = (
            current_correlation - mean
        ) / std

    correlation_results.append({
        "Date": date,
        "Rolling_Correlation": current_correlation,
        "Correlation_Z": z_score
    })


# ---------------------------------------
# Print results
# ---------------------------------------

print("\nCorrelation results:")

for result in correlation_results:
    print(
        result["Date"].date(),
        f"| correlation={result['Rolling_Correlation']:.4f}",
        f"| z={result['Correlation_Z']:.2f}"
    )


# ---------------------------------------
# Save correlation results
# ---------------------------------------

correlation_df = pd.DataFrame(correlation_results)

correlation_df.to_csv(
    "Dataset/streamed_correlation.csv",
    index=False
)

print("\nSaved correlation results to:")
print("Dataset/streamed_correlation.csv")