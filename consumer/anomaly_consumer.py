import argparse
import json
import os
import sys
from collections import defaultdict
import joblib
import numpy as np
import pandas as pd

MODEL_PATH = "models/isolation_forest.joblib"
HISTORICAL_STREAM = "Dataset/market_stream.csv"
FEATURES = ["Return", "Volatility_20", "Volume_Ratio"]


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model artifact not found at {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


def validate_message(event):
    required = ["date", "symbol", "return", "volatility_20", "volume_ratio"]
    for field in required:
        if field not in event:
            return False, f"Missing required field '{field}'"
        if event[field] is None:
            return False, f"Null value in field '{field}'"
    return True, None


def run_kafka_consumer():
    try:
        from kafka import KafkaConsumer
        from kafka.errors import NoBrokersAvailable
    except ImportError:
        print("[ERROR] kafka-python is not installed.")
        sys.exit(1)

    print("Connecting to Kafka broker at localhost:9092...")
    try:
        consumer = KafkaConsumer(
            "market-events",
            bootstrap_servers="localhost:9092",
            auto_offset_reset="earliest",
            group_id="marketlens-anomaly-consumer",
            consumer_timeout_ms=10000,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )
    except NoBrokersAvailable:
        print("\n[ERROR] Kafka broker at localhost:9092 is not reachable.")
        print("To start Kafka via Docker:")
        print("    docker compose up -d")
        print("\nTo run the deterministic streaming pipeline in offline simulation mode:")
        print("    python consumer/anomaly_consumer.py --simulate\n")
        sys.exit(1)

    model = load_model()
    print("Kafka consumer connected. Listening to topic 'market-events'...")

    daily_buffer = defaultdict(list)
    total_messages = 0

    for message in consumer:
        event = message.value
        is_valid, err = validate_message(event)
        if not is_valid:
            print(f"[WARN] Invalid message skipped: {err}")
            continue

        daily_buffer[event["date"]].append(event)
        total_messages += 1

    consumer.close()
    print(f"\nFinished receiving {total_messages} messages across {len(daily_buffer)} dates.")
    process_daily_batches(daily_buffer, model)


def run_simulation_replay(target_date="2020-03-23"):
    """
    Offline deterministic replay: serializes historical stream rows to JSON messages,
    deserializes, validates schema, and runs consumer anomaly detection pipeline.
    """
    print(f"\n=== RUNNING STREAMING REPLAY SIMULATION (Target: {target_date}) ===")
    model = load_model()

    df = pd.read_csv(HISTORICAL_STREAM)
    df = df[df["Date"] == target_date]

    if df.empty:
        print(f"[ERROR] No historical records found for {target_date}")
        return

    # Simulate Producer -> JSON Serialization
    messages = []
    for _, row in df.iterrows():
        payload = json.dumps({
            "date": str(row["Date"]),
            "symbol": str(row["CanonicalSymbol"]),
            "return": float(row["Return"]),
            "volatility_20": float(row["Volatility_20"]),
            "volume_ratio": float(row["Volume_Ratio"]),
        }).encode("utf-8")
        messages.append(payload)

    print(f"Producer published: {len(messages)} serialized JSON events")

    # Simulate Consumer -> Deserialization & Processing
    daily_buffer = defaultdict(list)
    for msg in messages:
        event = json.loads(msg.decode("utf-8"))
        is_valid, err = validate_message(event)
        assert is_valid, f"Validation error: {err}"
        daily_buffer[event["date"]].append(event)

    process_daily_batches(daily_buffer, model)


def process_daily_batches(daily_buffer, model):
    for date_str, records in sorted(daily_buffer.items()):
        batch_df = pd.DataFrame(records)
        batch_df.rename(columns={
            "symbol": "CanonicalSymbol",
            "return": "Return",
            "volatility_20": "Volatility_20",
            "volume_ratio": "Volume_Ratio",
        }, inplace=True)

        X = batch_df[FEATURES]
        preds = model.predict(X)
        scores = model.decision_function(X)

        batch_df["Anomaly"] = preds
        batch_df["Anomaly_Score"] = scores

        stocks_count = len(batch_df)
        anomalies_df = batch_df[batch_df["Anomaly"] == -1]
        anomalies_count = len(anomalies_df)
        breadth = anomalies_count / stocks_count if stocks_count > 0 else 0.0

        negative_anomalies = int(((batch_df["Anomaly"] == -1) & (batch_df["Return"] < 0)).sum())
        positive_anomalies = int(((batch_df["Anomaly"] == -1) & (batch_df["Return"] > 0)).sum())

        negative_breadth = float((batch_df["Return"] < 0).mean())
        severe_decline_breadth = float((batch_df["Return"] <= -0.05).mean())
        mean_return = float(batch_df["Return"].mean())

        print(f"\n------------------------------------------------------------")
        print(f"REPLAY DATE: {date_str}")
        print(f"------------------------------------------------------------")
        print(f"Stocks Analyzed:          {stocks_count}")
        print(f"Anomalies Detected:       {anomalies_count}")
        print(f"Anomaly Breadth:          {breadth:.2%}")
        print(f"Negative Anomalies:       {negative_anomalies}")
        print(f"Positive Anomalies:       {positive_anomalies}")
        print(f"Negative Breadth:         {negative_breadth:.2%}")
        print(f"Severe Decline Breadth:   {severe_decline_breadth:.2%}")
        print(f"Mean Stock Return:        {mean_return:.2%}")

        if anomalies_count > 0:
            print("\nAnomalous Stocks Detail:")
            print(
                anomalies_df[[
                    "CanonicalSymbol", "Return", "Volatility_20", "Volume_Ratio", "Anomaly_Score"
                ]].sort_values("Anomaly_Score").to_string(index=False)
            )

        # Regression checkpoint assertion for 2020-03-23
        if date_str == "2020-03-23":
            print("\n[VERIFICATION: 2020-03-23 CHECKPOINT]")
            assert stocks_count == 47, f"Expected 47 stocks, got {stocks_count}"
            assert anomalies_count == 7, f"Expected 7 anomalies, got {anomalies_count}"
            assert abs(breadth - 0.1489) < 0.001, f"Expected ~14.89% breadth, got {breadth:.4f}"
            assert negative_anomalies == 7, f"Expected 7 negative anomalies, got {negative_anomalies}"
            assert positive_anomalies == 0, f"Expected 0 positive anomalies, got {positive_anomalies}"
            print("[PASS] Checkpoint 2020-03-23 VERIFIED: 47 stocks, 7 anomalies (14.89%), 7 negative, 0 positive.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MarketLens Kafka Anomaly Consumer & Replay Processor")
    parser.add_argument("--simulate", action="store_true", help="Run deterministic offline replay simulation")
    parser.add_argument("--date", type=str, default="2020-03-23", help="Replay date (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.simulate:
        run_simulation_replay(args.date)
    else:
        run_kafka_consumer()
