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

webhook_dlx = RabbitExchange(
    name="webhook.dlx",
    type=ExchangeType.DIRECT,
    durable=True,
)

payment_queue = RabbitQueue(
    name="payments.new",
    routing_key="payment.created",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "webhook.dlx",
        "x-dead-letter-routing-key": "webhook.failed",
    },
)

webhook_dlq = RabbitQueue(
    name="webhook_dlq",
    routing_key="webhook.failed",
    durable=True,
)
