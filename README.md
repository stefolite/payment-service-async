# Payment Service Async

Асинхронный сервис имитации обработки платежей. Принимает запрос, обрабатывает платёж в фоне и отправляет результат на указанный webhook. Реальные списания не выполняются.

**Стек:** Python 3.13, FastAPI, SQLAlchemy 2 (async), PostgreSQL 18, Alembic, RabbitMQ 4, FastStream, httpx, Docker Compose, uv, pytest.

## Возможности

- Создание платежа (`202 Accepted`) и получение статуса (`pending`, `succeeded`, `failed`).
- Аутентификация через `X-API-Key` и идемпотентность через `Idempotency-Key`, включая параллельные запросы.
- **Transactional Outbox** для надёжной публикации событий; Publisher выбирает записи через `FOR UPDATE SKIP LOCKED`.
- Обработка платежа за 2–5 секунд (90% успех, 10% отказ).
- До трёх попыток доставки webhook с задержками 1 и 2 секунды; при неудаче сообщение отправляется в DLQ (`webhook_dlq`).

## Архитектура

```text
POST /payments
  → PostgreSQL (payment + payment.created в Outbox)
  → Outbox Publisher → RabbitMQ → Payment Worker
  → PostgreSQL (status + payment.completed в Outbox)
  → Outbox Publisher → RabbitMQ → Webhook Worker
  → HTTP webhook / DLQ
```

События сохраняются вместе с изменениями платежа в одной транзакции. Доставка **at-least-once**: дубликаты сообщений возможны, поэтому Payment Worker не обрабатывает уже завершённый платёж повторно.

## Запуск

Нужны Docker и Docker Compose.

```bash
git clone https://github.com/stefolite/payment-service-async.git
cd payment-service-async
cp .env.example .env
```

После копирования заполните `.env` значениями для локального запуска. Например:

```dotenv
POSTGRES_DB=payments
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
RABBITMQ_DEFAULT_USER=admin
RABBITMQ_DEFAULT_PASS=admin
API_KEY=dev-api-key
DATABASE_URL=postgresql+asyncpg://admin:admin@127.0.0.1:5433/payments
TEST_DATABASE_URL=postgresql+asyncpg://admin:admin@127.0.0.1:5433/payments_test
RABBITMQ_URL=amqp://admin:admin@127.0.0.1:5672/
```

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Запускаются `db`, `rabbitmq`, `api`, `publisher`, `payment-worker` и `webhook-worker`. Внутри Docker сервисы подключаются к БД и брокеру по адресам `db:5432` и `rabbitmq:5672`.

- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- RabbitMQ Management: http://127.0.0.1:15672

## API

Все маршруты `/api` требуют заголовок `X-API-Key`. Для создания платежа также нужен `Idempotency-Key`.

**Создание платежа:** `POST /api/v1/payments` → `202 Accepted`.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/payments \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-api-key' \
  -H 'Idempotency-Key: order-001' \
  -d '{"amount":"100.00","currency":"RUB","description":"Тест","webhook_url":"https://webhook.site/<your-uuid>"}'
```

**Получение статуса:** `GET /api/v1/payments/{payment_id}` → `200 OK`.

Повторный POST с тем же ключом и теми же данными возвращает существующий платёж; с другими данными → `409 Conflict`.

Webhook отправляется методом POST на `webhook_url`:

```json
{"payment_id":"<uuid>","status":"succeeded"}
```

Для проверки доставки можно получить уникальный URL на [webhook.site](https://webhook.site/) и подставить его в запрос.

## Тесты

Нужны Python 3.13, uv и запущенный PostgreSQL. **Тестовая база `payments_test` создаётся отдельно:** Docker Compose автоматически создаёт только основную БД.

```bash
docker compose up -d db
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" payments_test'
uv sync
uv run pytest -q
```

Базу достаточно создать один раз. Тестовые фикстуры применяют миграции автоматически. `TEST_DATABASE_URL` должен указывать на тестовую БД, а не на основную.

**Логи:** `docker compose logs -f api publisher payment-worker webhook-worker`  
**Остановка:** `docker compose down`
