# Настройка Stripe — LearningPlatform

Коротко: минимальная инструкция по подключению Stripe (тестовый режим).

1. Регистрация
- Зарегистрируйтесь в https://stripe.com и получите доступ к Dashboard → Developers → API keys.
- Для тестов используйте тестовые ключи: Publishable (pk_test_...) и Secret (sk_test_...).

2. Переменные окружения (.env)
Скопируйте и заполните в корне проекта .env (используйте .env.example как шаблон):

```env
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_TEST_MODE=True
BASE_URL=http://localhost:8000
```

Не храните реальные ключи в репозитории. .env должен быть в .gitignore.

3. Webhook (локально и прод)
- В продакшне webhook должен быть HTTPS и защищён секретом (STRIPE_WEBHOOK_SECRET).
- Для локальной разработки используйте туннели (ngrok, Cloudflare Tunnel) и пробрасывайте публичный URL, например:

  https://abc123.ngrok.io/api/payments/stripe-webhook/

4. Тестовые карты (Stripe)
- Успешная оплата: 4242424242424242
- Отклонение: 4000000000000002
- Требует аутентификации (3DS): 4000002500003155

5. Как использовать из кода
- Серверный код создаёт PaymentIntent через Payments.stripe_service.StripeService.create_payment_intent(amount, description, transaction_id).
- API возвращает client_secret, который нужно передать на фронтенд для подтверждения оплаты через Stripe.js.

6. Frontend (коротко)
- Подключите Stripe.js (https://js.stripe.com/v3)
- Получите client_secret с /api/payments/create_payment/ и завершите оплату на клиенте через confirmPayment / confirmCardPayment.

7. Советы и безопасность
- Храните секреты в CI/секретном хранилище или в локальном .env (не коммитить).
- Проверяйте подписи webhook в продакшне, используйте STRIPE_WEBHOOK_SECRET.
- Для тестов используйте STRIPE_TEST_MODE=True.

Если нужно — подготовлю готовые curl/JS примеры интеграции или подробный пример webhook handler.