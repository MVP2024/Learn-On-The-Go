# 🚀 Настройка Stripe для LearningPlatform

## Почему Stripe?
- ✅ Намного проще чем ЮKassa
- ✅ Лучшая документация
- ✅ Проще интеграция
- ✅ Меньше кода

## 🏦 Быстрая настройка (5 минут!)

### 1. Регистрация в Stripe
1. Идите на https://stripe.com/
2. Нажмите "Start now" 
3. Заполните простую форму
4. Подтвердите email

### 2. Получение ключей
1. В дашборде Stripe перейдите в "Developers" → "API keys"
2. Скопируйте:
   - **Publishable key**: `pk_test_...` 
   - **Secret key**: `sk_test_...`

### 3. Настройка проекта
Обновите `.env`:
```env
STRIPE_PUBLISHABLE_KEY=pk_test_ваш_ключ
STRIPE_SECRET_KEY=sk_test_ваш_секретный_ключ
STRIPE_TEST_MODE=True
```

### 4. Настройка webhook (опционально)
1. В Stripe перейдите "Developers" → "Webhooks"
2. Добавьте endpoint: `https://ваш-домен.com/api/payments/stripe-webhook/`
3. Выберите события: `payment_intent.succeeded`, `payment_intent.payment_failed`
4. Скопируйте webhook secret в `.env`

## 💳 Тестовые карты
- ✅ Успешная оплата: `4242424242424242`
- ❌ Отклонение: `4000000000000002`
- 🔒 Требует аутентификации: `4000002500003155`

## 🎯 Использование в коде

### Создание платежа
```python
from decimal import Decimal
from Payments.stripe_service import StripeService

service = StripeService()
payment = service.create_payment_intent(
    amount=Decimal('100.00'),
    description="Покупка курса Python",
    transaction_id="order_123"
)

# Отправляем client_secret на фронтенд для завершения оплаты
client_secret = payment['client_secret']
```

### Frontend интеграция (простая!)
```javascript
// 1. Подключаем Stripe.js
<script src="https://js.stripe.com/v3/"></script>

// 2. Создаем платежный интент
const response = await fetch('/api/payments/create_payment/', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        payment_type: 'discipline',
        discipline_id: 1,
        payment_method: 'stripe'
    })
});

const {client_secret} = await response.json();

// 3. Завершаем оплату
const stripe = Stripe('ваш_publishable_key');
const {error} = await stripe.confirmPayment({
    elements,
    clientSecret: client_secret,
    confirmParams: {
        return_url: 'https://ваш-сайт.com/success'
    }
});
```

## 🎉 Готово!
Stripe настроен и готов к использованию! Намного проще чем ЮKassa 😊

## 💡 Полезные ссылки
- 📖 Документация: https://stripe.com/docs
- 🎮 Тестирование: https://stripe.com/docs/testing
- 💬 Поддержка: отличная!

## 🔄 Переход с ЮKassa
Если у вас уже была настроена ЮKassa, просто:
1. Обновите `.env` с ключами Stripe
2. Код автоматически будет использовать Stripe
3. Намного меньше головной боли! 🎯