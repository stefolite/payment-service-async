from backend.core.broker import broker, payment_exchange, payment_queue
from faststream import FastStream


app = FastStream(broker)

# uv run faststream run backend.payments.worker:app


@broker.subscriber(queue=payment_queue, exchange=payment_exchange)
async def process_payment(data: dict):
    print(data["payment_id"])
