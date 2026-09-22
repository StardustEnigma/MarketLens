from kafka import KafkaConsumer

consumer = KafkaConsumer(
    "market-events",
    bootstrap_servers="localhost:9092",
    group_id="raw-test-999",
    auto_offset_reset="earliest"
)

print("CONNECTED")

for message in consumer:
    print("GOT:", message.value)
    break