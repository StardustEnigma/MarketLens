import json
from collections import defaultdict, deque

from kafka import KafkaConsumer


consumer = KafkaConsumer(
    "market-events",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="earliest",
    group_id="correlation-test-123",
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)

print("Waiting for market events...")

# Store recent returns for each stock
return_history = defaultdict(lambda: deque(maxlen=60))

current_date = None
daily_returns = {}


for message in consumer:

    event = message.value

    date = event["date"]
    symbol = event["symbol"]
    stock_return = event["return"]

    # Detect a new trading day
    if current_date is None:
        current_date = date

    if date != current_date:

        # Save the previous day's returns
        for symbol, stock_return in daily_returns.items():
            return_history[symbol].append(stock_return)

        print(
            f"Processed {current_date} | "
            f"Stocks: {len(daily_returns)}"
        )

        daily_returns = {}
        current_date = date

    daily_returns[symbol] = stock_return