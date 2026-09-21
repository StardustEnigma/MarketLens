import json
import pandas as pd
from kafka import KafkaProducer


producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

df = pd.read_csv("Dataset/market_stream.csv")

day = df[df["Date"] == "2020-03-23"]

print(f"Streaming {len(day)} stocks from 2020-03-23")

for _, row in day.iterrows():

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

print("Finished streaming test day.")