# Настройка ЮKassa — LearningPlatform

Кратко: как быстро подключить и тестировать ЮKassa в локальной и прод окружении.

1. Регистрация и ключи
- Зарегистрируйтесь в личном кабинете ЮKassa: https://yookassa.ru/developers/
- Получите shopId и secret key (отдельно для тестового и продакшн режимов).

2. Переменные окружения (.env)
Скопируйте `.env.example` в `.env` и заполните поля:

```env
YOOKASSA_SHOP_ID=ваш_shop_id
YOOKASSA_SECRET_KEY=ваш_secret_key
YOOKASSA_TEST_MODE=True
BASE_URL=http://localhost:8000
```

Не храните реальные секреты в репозитории.

3. Запуск и тестирование локально
- Примените миграции и загрузите demo-данные (опционально):

```bash
python manage.py migrate
python utils/clear_and_load_fixtures.py --yes
# или только пользователи:
python utils/scripts_for_demo/setup_users.py
```

- Запустите сервер и Redis/Celery (если нужны фоновые задачи):

```bash
python manage.py runserver
# Redis (docker):
docker run -d --name lp-redis -p 6379:6379 redis:alpine
python start_celery.py  # для разработки
```

- В проекте есть вспомогательные скрипты для проверки: `utils/scripts_for_demo/yookassa_demo.py` и `yookassa_demo_from_payments.py`.

4. Тестовые карты и данные
- Тестовая карта (пример): 5555555555554444, срок 12/26, CVC 123 — для успешной оплаты.
- Карта для отклонения: 4000000000000002

5. Webhook
- В продакшне webhook должен быть HTTPS и проверяться на подпись.
- Для локальной разработки используйте туннель (ngrok/Cloudflare Tunnel) и укажите публичный URL в личном кабинете ЮKassa:

```
https://<ваш-tunnel>.ngrok.io/api/payments/yookassa-webhook/
```

6. Как это используется в проекте
- API создания платежа: POST /api/payments/create_payment/ — возвращает confirmation_url для перенаправления пользователя (YooKassa) или client_secret (Stripe).
- Webhook endpoint: POST /api/payments/yookassa-webhook/ — приложение проверяет подпись и обрабатывает события payment.succeeded / payment.canceled.
- При завершении платежа сигнал Payments.signals.create_purchased_content_on_payment_completion создаёт PurchasedContent (идемпотентно через get_or_create).

7. Производство (prod)
- Убедитесь, что YOOKASSA_TEST_MODE=False и используете реальные ключи.
- Webhook: HTTPS + проверка подписи.
- Храните ключи в секретном хранилище (CI / hosting).

8. Отладка
- Для локальной отладки webhook используйте ngrok; проверяйте логи Django и ЮKassa.
- Скрипты в `utils/scripts_for_demo` помогут создать тестовый платеж и получить confirmation_url.

Если хотите, подготовлю готовые curl‑примеры для создания платежа и обработки webhook или краткий пример фронтенд‑флоу.