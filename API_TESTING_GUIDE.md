# Руководство по тестированию API — LearningPlatform

Коротко: как подготовиться к тестированию и часто используемые запросы.

1. Подготовка окружения
- Создайте `.env` из `.env.example` и заполните значения (локально можно оставить тестовые значения из фикстур).
- Для тестовой локальной базы удобно использовать fixtures: `python utils/clear_and_load_fixtures.py --yes` (внимание: очищает данные).
- Для создания только пользователей используйте: `python utils/scripts_for_demo/setup_users.py`.

2. Получение токена (JWT)
- Endpoint: POST /api/token/
- Пример curl:

```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "teacher_1@a.aa", "password": "Spirocheta77"}'
```

Ответ: {"access": "...", "refresh": "..."}

3. Проверка аутентификации (debug)
- GET /api/debug-auth/ с заголовком Authorization: Bearer <ACCESS_TOKEN>
- Используйте для быстрой проверки прав и заголовков.

4. Общие правила по полям и форматам
- Поле `discipline` в создании/обновлении урока принимает slug (строку) или числовой id. Не передавайте human-readable title.
- Для платежей: Stripe ожидает суммы в копейках при работе со сторонним SDK; внутри проекта используется Decimal (рубли) — сервисы переводят при необходимости.

5. Примеры запросов
- Получить все дисциплины:

```bash
curl -X GET http://localhost:8000/api/disciplines/ \
  -H "Authorization: Bearer <TOKEN>"
```

- Получить дисциплину по id:

```bash
curl -X GET http://localhost:8000/api/disciplines/1/ \
  -H "Authorization: Bearer <TOKEN>"
```

- Создать урок (пример):

```bash
curl -X POST http://localhost:8000/api/lessons/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Интегралы.", "discipline":"matematika_7", "video_url":"https://...", "lesson_order":1}'
```

- Проверка платежа (создание):

```bash
curl -X POST http://localhost:8000/api/payments/create_payment/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"payment_type":"discipline","discipline_id":1,"payment_method":"yookassa"}'
```

6. Частые ошибки и быстрое решение
- 401 Unauthorized — проверьте access токен и заголовок Authorization
- 400 Bad Request — проверьте JSON и обязательные поля (см. сериализаторы в коде)
- 404 Not Found — проверьте, существует ли объект (id/slug) и корректен ли путь

7. Тестовые пользователи (fixture)
- admin@a.aa / Spirocheta77 (админ)
- teacher_1@a.aa / Spirocheta77 (учитель)
- student_1@a.aa / Spirocheta77 (студент)
- moderator_1@a.aa / Spirocheta77 (модератор)

8. Советы
- Используйте Swagger UI: http://localhost:8000/api/schema/swagger-ui/ — там видно схемы и примеры
- Для локального тестирования webhook используйте ngrok/Cloudflare Tunnel и укажите публичный HTTPS URL

Если нужно, могу подготовить набор curl/HTTPie команд для наиболее часто используемых сценариев (мигрции, загрузка фикстур, создание пользователей, покупка контента).

---

← [Назад: PAYMENTS_SUMMARY](PAYMENTS_SUMMARY.md) | [← В README](README.md) | **Далее:** [CELERY_GUIDE.md](CELERY_GUIDE.md) → | [Все руководства](README.md#6-документы-и-подробные-руководства)
