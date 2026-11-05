# Payment Service Async

Асинхронный сервис имитации обработки платежей. Принимает запросы на создание платежей, обрабатывает их в фоне и отправляет результат на указанный webhook. Реальные списания не выполняются.

**Стек:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2 (async), PostgreSQL 18, Alembic, RabbitMQ 4, FastStream, httpx, Docker Compose, uv, pytest.

## Возможности

- Создание платежа (`202 Accepted`) и получение полной информации о нём. Статусы: `pending`, `succeeded`, `failed`.
- Аутентификация через `X-API-Key` и идемпотентность через `Idempotency-Key`, включая конкурентные запросы.
- **Transactional Outbox** для надёжной публикации событий. Publisher выбирает записи через `FOR UPDATE SKIP LOCKED`.
- Эмуляция обработки платежа за 2–5 секунд: 90% успеха, 10% отказов.
- До трёх попыток доставки webhook с задержками 1 и 2 секунды. При окончательной неудаче сообщение отправляется в DLQ (`webhook_dlq`).

## Архитектура

```text
POST /api/v1/payments
  → PostgreSQL (payment + payment.created в Outbox)
  → Outbox Publisher → RabbitMQ → Payment Worker
  → PostgreSQL (status + payment.completed в Outbox)
  → Outbox Publisher → RabbitMQ → Webhook Worker
  → HTTP webhook / DLQ
```

События сохраняются вместе с изменениями платежа в одной транзакции.

Используется модель доставки **at-least-once**: повторная доставка сообщений возможна. Payment Worker защищён от повторной обработки уже завершённых платежей.

## Запуск

Необходимы Docker и Docker Compose.

```bash
git clone https://github.com/stefolite/payment-service-async.git
cd payment-service-async
cp .env.example .env
```

В `.env.example` указаны значения для локального запуска. При необходимости измените их в `.env` перед запуском.

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Запускаются шесть сервисов: `db`, `rabbitmq`, `api`, `publisher`, `payment-worker` и `webhook-worker`.

Внутри Docker сервисы подключаются к PostgreSQL и RabbitMQ по адресам `db:5432` и `rabbitmq:5672`.

Доступные интерфейсы:

- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- RabbitMQ Management: http://127.0.0.1:15672

## API

Все маршруты `/api` требуют заголовок `X-API-Key`. Эндпоинт `/health` доступен без авторизации.

### Создание платежа

`POST /api/v1/payments` → `202 Accepted`

```bash
curl -X POST http://127.0.0.1:8000/api/v1/payments \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-api-key' \
  -H 'Idempotency-Key: order-001' \
  -d '{
    "amount": "100.00",
    "currency": "RUB",
    "description": "Тестовый платёж",
    "metadata": {},
    "webhook_url": "https://webhook.site/YOUR-UUID"
  }'
```

Замените `YOUR-UUID` на идентификатор, полученный на [webhook.site](https://webhook.site/). Значение `X-API-Key` должно совпадать с `API_KEY` в `.env`.

Повторный POST с тем же `Idempotency-Key` и идентичными данными возвращает существующий платёж, включая его текущий статус. При передаче других данных с тем же ключом возвращается `409 Conflict`.

### Получение информации о платеже

`GET /api/v1/payments/{payment_id}` → `200 OK`

```bash
curl http://127.0.0.1:8000/api/v1/payments/PAYMENT_ID \
  -H 'X-API-Key: dev-api-key'
```

Замените `PAYMENT_ID` на идентификатор из ответа POST.

Эндпоинт возвращает идентификатор платежа, сумму, валюту, описание, метаданные, webhook URL, idempotency key, текущий статус и даты создания/обработки.

При отсутствии платежа возвращается `404 Not Found`.

### Webhook

После обработки платежа сервис отправляет POST-запрос на указанный `webhook_url`.

Пример тела уведомления:

```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "succeeded"
}
```

При ошибке отправки выполняется до трёх HTTP-попыток. Если все попытки неуспешны, сообщение направляется в Dead Letter Queue (`webhook_dlq`).

Для проверки доставки можно использовать [webhook.site](https://webhook.site/).

## Тесты

Необходимы Python 3.13, uv и запущенный PostgreSQL.

Тесты используют отдельную базу `payments_test`. Docker Compose автоматически создаёт только основную БД.

```bash
docker compose up -d db
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" payments_test'

uv sync
uv run pytest -q
```

Базу `payments_test` достаточно создать один раз. Тестовые фикстуры автоматически применяют миграции Alembic.

Переменная `TEST_DATABASE_URL` должна указывать на тестовую базу, а не на основную.

## Полезные команды

**Просмотр логов:**

```bash
docker compose logs -f api publisher payment-worker webhook-worker
```

**Остановка контейнеров:**

```bash
docker compose down
```
