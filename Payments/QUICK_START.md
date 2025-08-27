# 🚀 Быстрый старт с ЮKassa

## Что нужно для работы платежей

### 1. Регистрация в ЮKassa (5 минут)

1. Идите на https://yookassa.ru/developers/
2. Нажмите "Подключить ЮKassa"
3. Заполните форму регистрации
4. Подтвердите email

### 2. Создание тестового магазина

1. В личном кабинете нажмите "Добавить магазин"
2. Выберите "Тестовый магазин"
3. Заполните данные:
   - Название: "LearningPlatform Test"
   - Тип: "Образование"
   - Сайт: ваш домен или localhost

### 3. Получение ключей

В разделе "Настройки" → "Интеграция":
- **shopId** (ID магазина) - скопируйте
- **Секретный ключ** - создайте и скопируйте

### 4. Настройка проекта

В файле `.env` замените:
```env
YOOKASSA_SHOP_ID=ваш_реальный_shop_id
YOOKASSA_SECRET_KEY=ваш_реальный_secret_key  
YOOKASSA_TEST_MODE=True
```

### 5. Применение миграций

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Тестирование

```bash
python Payments/test_yookassa.py
```

## 🎯 Тестовые данные

**Тестовые карты:**
- ✅ Успешная оплата: `5555555555554444`
- ❌ Отклонение: `4000000000000002`
- Дата: `12/26`, CVC: `123`

## 🔧 Настройка Webhook (опционально для тестирования)

1. Установите ngrok: `npm install -g ngrok`
2. Запустите туннель: `ngrok http 8000`
3. Скопируйте URL типа: `https://abc123.ngrok.io`
4. В ЮKassa → HTTP-уведомления → добавьте:
   `https://abc123.ngrok.io/api/payments/yookassa-webhook/`

## 🎉 Готово!

Теперь можно создавать платежи через API:

```bash
curl -X POST http://localhost:8000/api/payments/create_payment/ \
  -H "Authorization: Bearer ваш_токен" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_type": "discipline",
    "discipline_id": 1,
    "payment_method": "yookassa"
  }'
```

**Ответ будет содержать `yookassa_confirmation_url` для перенаправления на оплату!**