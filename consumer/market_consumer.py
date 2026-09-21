import json
import joblib
import pandas as pd
from kafka import KafkaConsumer


model = joblib.load("models/isolation_forest.joblib")

consumer = KafkaConsumer(
    "market-events",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="earliest",
    group_id="model-test-123",
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)

print("Waiting for market events...")

anomalies = 0
negative_anomalies = 0
positive_anomalies = 0
total = 0

for message in consumer:

    event = message.value

    features = pd.DataFrame([{
        "Return": event["return"],
        "Volatility_20": event["volatility_20"],
        "Volume_Ratio": event["volume_ratio"]
    }])

    prediction = model.predict(features)[0]
    score = model.decision_function(features)[0]

    total += 1

    if prediction == -1:
        if event["return"] < 0:
            negative_anomalies += 1
        else:
            positive_anomalies += 1
        anomalies += 1
        print(
            f"ANOMALY | {event['date']} | "
            f"{event['symbol']} | score={score:.4f}"
        )

    if total == 47:
        break

print("\n--- Daily Summary ---")
print(f"Stocks: {total}")
print(f"Anomalies: {anomalies}")
print(f"Anomaly Breadth: {anomalies / total:.2%}")
print(f"Negative Anomalies: {negative_anomalies}")
print(f"Positive Anomalies: {positive_anomalies}")

if anomalies > 0:
    print(f"Negative Ratio: {negative_anomalies / anomalies:.2%}")
    print(f"Positive Ratio: {positive_anomalies / anomalies:.2%}")