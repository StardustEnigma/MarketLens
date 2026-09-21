import json
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

event = {
    "date": "2016-05-04",
    "symbol": "ADANIPORTS",
    "return": -0.115711,
    "volatility_20": 0.036622,
    "volume_ratio": 4.831902
}

producer.send("market-events", value=event)
producer.flush()
producer.close()

print("Anomaly test event sent!")