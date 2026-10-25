import json
import sys
import pandas as pd
from kafka import KafkaProducer

try:
    producer = KafkaProducer(
        bootstrap_servers="localhost:9092",
        request_timeout_ms=5000,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
except Exception as e:
    print(f"\n[ERROR] Unable to connect to Kafka broker at localhost:9092.")
    print("Ensure Kafka is running (e.g. via `docker compose up -d`).")
    print(f"Details: {e}")
    sys.exit(1)

df = pd.read_csv("Dataset/market_stream.csv")

df = df[
    (df["Date"] >= "2019-11-01") &
    (df["Date"] <= "2020-03-23")
]

print(f"Streaming {len(df)} observations")

for _, row in df.iterrows():
    event = {
        "date": row["Date"],
        "symbol": row["CanonicalSymbol"],
        "return": row["Return"],
        "volatility_20": row["Volatility_20"],
        "volume_ratio": row["Volume_Ratio"]
    }

    producer.send("market-events", value=event)

producer.flush()
producer.close()

print("Finished streaming historical range.")