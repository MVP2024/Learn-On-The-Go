# Быстрый старт — Платежи (YooKassa)

Коротко: как быстро настроить и протестировать платежи через YooKassa в локальной разработке.

1. Зарегистрируйтесь и создайте тестовый магазин в YooKassa
- Документация: https://yookassa.ru/developers/
- Получите shopId и secret key для тестового режима.

2. Настройте переменные окружения
- Скопируйте корневой .env.example в .env и заполните данные для YooKassa:

```env
YOOKASSA_SHOP_ID=ваш_shop_id
YOOKASSA_SECRET_KEY=ваш_secret_key
YOOKASSA_TEST_MODE=True
BASE_URL=http://localhost:8000
```

Не храните реальные секреты в репозитории.

3. Примените миграции и загрузите demo-данные (опционально)

```bash
python manage.py migrate
python utils/clear_and_load_fixtures.py --yes
# или только пользователи:
python utils/scripts_for_demo/setup_users.py
```

4. Запустите сервисы
- Запуск локально: python manage.py runserver
- Запуск Redis (брокер) — можно через Docker:

```bash
docker run -d --name lp-redis -p 6379:6379 redis:alpine
```

- Запустите Celery (dev): python start_celery.py

5. Тестирование платежа
- В скриптах есть utils/scripts_for_demo/yookassa_demo.py для быстрой проверки подключения и создания тестового платежа.
- Пример запуска:

```bash
python utils/scripts_for_demo/yookassa_demo.py
```

- Скрипт выведет confirmation_url — откройте его в браузере, используйте тестовую карту.
- Тестовая карта (пример): 5555555555554444, срок/сvv — 12/26, 123.

6. Webhook (локально)
- WooKassa требует публичный HTTPS URL для webhook.
- Для локали используйте ngrok/Cloudflare Tunnel и настройте webhook в личном кабинете YooKassa на:

```
https://<ваш-tunnel>.ngrok.io/api/payments/yookassa-webhook/
```

7. В продакшне
- Webhook должен быть HTTPS и проверяться на подпись.
- Храните ключи в секретном хранилище CI/hosting.
- Для продакшна отключите тестовый режим (YOOKASSA_TEST_MODE=False) и проверьте права доступа.

Если нужно, подготовлю curl-примеры для создания платежа и обработки webhook или интеграцию с фронтендом.

---

← [← В PAYMENTS_SUMMARY](../PAYMENTS_SUMMARY.md) | [← В README](../README.md) | **Далее:** [YOOKASSA_SETUP.md](YOOKASSA_SETUP.md) → | [Все руководства](../README.md#6-документы-и-подробные-руководства)
