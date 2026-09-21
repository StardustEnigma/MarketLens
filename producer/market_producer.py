import argparse
import json
import time

import pandas as pd
from kafka import KafkaProducer


parser = argparse.ArgumentParser()

parser.add_argument(
    "--limit",
    type=int,
    default=100,
    help="Number of market observations to stream"
)

parser.add_argument(
    "--delay",
    type=float,
    default=0.01,
    help="Delay between messages in seconds"
)

args = parser.parse_args()


producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

df = pd.read_csv("Dataset/market_stream.csv").head(args.limit)

for _, row in df.iterrows():

    event = {
        "date": row["Date"],
        "symbol": row["CanonicalSymbol"],
        "return": row["Return"],
        "volatility_20": row["Volatility_20"],
        "volume_ratio": row["Volume_Ratio"]
    }

    producer.send("market-events", value=event)

    print(event)

    time.sleep(args.delay)

producer.flush()
producer.close()

print(f"Finished streaming {len(df)} market observations.")