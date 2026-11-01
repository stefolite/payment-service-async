from faststream.rabbit import (
    RabbitBroker,
    RabbitExchange,
    RabbitQueue,
    ExchangeType,
)
from backend.core.config import Settings


settings = Settings()

broker = RabbitBroker(settings.rabbitmq_url)
payment_exchange = RabbitExchange(
    name="payments",
    type=ExchangeType.DIRECT,
    durable=True,
)
payment_queue = RabbitQueue(
    name="payment_processing",
    routing_key="payment.created",
    durable=True,
)
