# Настройка ЮKassa для LearningPlatform

## 🚀 Быстрое подключение

### 1. Регистрация в ЮKassa

1. **Перейдите на сайт ЮKassa:**
   - Тестовый режим: https://yookassa.ru/developers/
   - Продакшен: https://yookassa.ru/

2. **Зарегистрируйтесь или войдите в аккаунт**

3. **Создайте магазин:**
   - Заполните основную информацию о вашем проекте
   - Укажите тип деятельности: "Образовательные услуги"
   - Добавьте описание платформы

### 2. Получение ключей доступа

В личном кабинете ЮKassa:

1. **Перейдите в раздел "Настройки" → "Интеграция"**

2. **Получите данные для подключения:**
   ```
   ID магазина (shopId): 123456
   Секретный ключ (secret key): live_abc123...
   ```

3. **Для тестирования используйте тестовые ключи:**
   ```
   Тестовый ID магазина: 123456  
   Тестовый секретный ключ: test_abc123...
   ```

### 3. Настройка webhook'а

1. **В разделе "HTTP-уведомления":**
   - URL для уведомлений: `https://ваш-домен.com/api/payments/yookassa-webhook/`
   - События: 
     - ✅ `payment.succeeded` - успешный платеж
     - ✅ `payment.canceled` - отмена платежа  
     - ✅ `refund.succeeded` - успешный возврат

2. **Для тестирования локально используйте ngrok:**
   ```
   # Устанавливаем ngrok
   npm install -g ngrok
   
   # Запускаем туннель
   ngrok http 8000
   
   # Используйте полученный URL:
   # https://abc123.ngrok.io/api/payments/yookassa-webhook/
   ```

## ⚙️ Конфигурация проекта

### 1. Переменные окружения (.env)

```env
# Настройки ЮKassa
YOOKASSA_SHOP_ID=ваш_shop_id
YOOKASSA_SECRET_KEY=ваш_секретный_ключ
YOOKASSA_TEST_MODE=True  # False для продакшена

# Базовый URL вашего сайта
BASE_URL=https://ваш-домен.com
```

### 2. Тестовые данные

**Тестовые номера карт:**
- ✅ Успешный платеж: `5555555555554444`
- ❌ Отклонение платежа: `4000000000000002`
- 🔄 Требует подтверждения: `4000000000000077`

**Тестовые данные карты:**
```
Номер: 5555555555554444
Месяц/год: 12/26
CVC: 123
Имя держателя: TEST TEST
```

## 🛠️ Использование в коде

### Создание платежа

```python
from Payments.services import PaymentService

# Создаем платеж
payment = PaymentService.create_payment(
    user=request.user,
    payment_type='discipline',
    discipline_id=1,
    payment_method='yookassa'
)

# Получаем URL для перенаправления на оплату
confirmation_url = payment.yookassa_confirmation_url
```

### Проверка статуса платежа

```python
from Payments.yookassa_service import YooKassaService

service = YooKassaService()
payment_info = service.get_payment_info(payment.yookassa_payment_id)

if payment_info['status'] == 'succeeded':
    print("Платеж успешно выполнен!")

## 📱 Frontend интеграция

### JavaScript пример

```javascript
// Создание платежа
const createPayment = async (disciplineId) => {
    const response = await fetch('/api/payments/create_payment/', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            payment_type: 'discipline',
            discipline_id: disciplineId,
            payment_method: 'yookassa'
        })
    });
    
    const payment = await response.json();
    
    // Перенаправляем пользователя на страницу оплаты ЮKassa
    if (payment.yookassa_confirmation_url) {
        window.location.href = payment.yookassa_confirmation_url;
    }
};

// Проверка статуса после возврата с оплаты
const checkPaymentStatus = async (transactionId) => {
    const response = await fetch(`/api/payments/check_status/?transaction_id=${transactionId}`, {
        headers: { 'Authorization': 'Bearer ' + token }
    });
    
    const payment = await response.json();
    
    if (payment.status === 'completed') {
        // Платеж успешен - показываем доступ к контенту
        showSuccessMessage('Оплата успешно завершена!');
        redirectToContent();
    } else if (payment.status === 'failed') {
        showErrorMessage('Оплата не удалась. Попробуйте еще раз.');
    }
};
```

## 🚨 Безопасность

### Важные моменты:

1. **Никогда не храните секретный ключ в коде!**
   - Используйте переменные окружения
   - Не коммитьте .env файлы

2. **Проверяйте подписи webhook'ов в продакшене:**
   ```python
   # В файле yookassa_service.py обновите метод validate_webhook_notification
   # для проверки подписи в продакшене
   ```

3. **Используйте HTTPS в продакшене:**
   - ЮKassa требует HTTPS для webhook'ов
   - Настройте SSL сертификат

## 🐛 Отладка

### Проверка логов

```bash
# Логи Django (в settings.py настройте LOGGING)
tail -f logs/payment.log

# Проверка webhook'ов в ЮKassa
# В личном кабинете → HTTP-уведомления → История
```

### Частые проблемы

1. **Webhook не работает:**
   - Проверьте URL доступности
   - Убедитесь, что порт открыт
   - Для локальной разработки используйте ngrok

2. **Платежи не создаются:**
   - Проверьте правильность ключей
   - Убедитесь в корректности суммы (больше 1 рубля)

3. **Ошибки аутентификации:**
   - Проверьте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY
   - Убедитесь, что ключи соответствуют режиму (тест/продакшен)

## 🎯 Переход в продакшен

1. **Смените режим:**
   ```env
   YOOKASSA_TEST_MODE=False
   ```

2. **Используйте продакшн ключи:**
   - Получите их в личном кабинете ЮKassa
   - Обновите .env файл

3. **Настройте реальный домен:**
   ```env
   BASE_URL=https://ваш-реальный-домен.com
   ```

4. **Обновите webhook URL в ЮKassa:**
   - Замените тестовый URL на продакшн

5. **Включите проверку подписей webhook'ов**

## 📞 Поддержка

- **Документация ЮKassa:** https://yookassa.ru/developers/
- **Техподдержка ЮKassa:** support@yookassa.ru
- **Сообщество разработчиков:** https://t.me/yookassa_api

Готово! Теперь ваша платформа интегрирована с ЮKassa 🎉