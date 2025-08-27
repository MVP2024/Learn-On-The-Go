# LearningPlatform

**LearningPlatform** - это образовательная платформа, разработанная на Django Rest Framework, позволяющая пользователям проходить курсы, уроки и тесты, а преподавателям и администраторам управлять контентом.

## 🚀 Быстрый старт

Для запуска проекта выполните следующие шаги:

### 📦 1. Установка зависимостей

Убедитесь, что у вас установлен Python 3.9+ и pip. Затем установите зависимости:

```bash
pip install -r requirements.txt
```

### ⚙️ 2. Настройка окружения

Создайте файл `.env` в корневой директории проекта на основе `.env.example` и заполните его необходимыми данными (настройки базы данных, ключи API, режим отладки и т.д.):

```dotenv
SECRET_KEY=ваш_секретный_ключ

# настройки БД (POSTGRESQL)
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

BASE_URL=http://localhost:8000

# Настройки redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

DEBUG=True

# Для отправки писем в консоль (для разработки)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Для реальной отправки писем (раскомментируйте и настройте)
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.example.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_USE_SSL=False
# EMAIL_HOST_USER=your_email@example.com
# EMAIL_HOST_PASSWORD=your_email_password

# Настройки Stripe (если используете)
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_TEST_MODE=True

# Настройки ЮKassa (если используете)
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
YOOKASSA_TEST_MODE=True
```

### 💾 3. Подготовка базы данных

Примените миграции для создания таблиц в базе данных:

```bash
python manage.py migrate
```

### 📊 4. Загрузка тестовых данных (опционально)

Для удобства тестирования вы можете загрузить преднастроенные тестовые данные (пользователи, дисциплины, уроки, тесты, платежи). Это очистит существующие данные в БД.

```bash
python utils/clear_and_load_fixtures.py
```

**Внимание:** Этот скрипт удалит все существующие данные из вашей базы данных перед загрузкой фикстур. Используйте его осторожно.

### 👤 5. Создание суперпользователя (если не использовали скрипт выше)

Если вы не использовали `utils/clear_and_load_fixtures.py`, создайте суперпользователя для доступа к Django Admin:

```bash
python manage.py createsuperuser
```

### 🚀 6. Запуск сервера и фоновых задач

#### Django Development Server

```bash
python manage.py runserver
```

Документация API будет доступна по адресу: [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)

#### Redis (брокер сообщений для Celery)

Убедитесь, что Redis запущен. Если у вас его нет, установите: [https://redis.io/download](https://redis.io/download)

**Для Windows:**

```bash
redis-server
```

**Для Linux/macOS:**

```bash
sudo systemctl start redis  # (если установлен через пакетный менеджер)
```

#### Celery Worker и Beat

Для асинхронной обработки задач (отправка email, обработка платежей, периодические задачи) используйте скрипт запуска Celery:

```bash
python start_celery.py
```

Этот скрипт предложит вам запустить Worker и Beat вместе или по отдельности.

## 🧩 Вспомогательные скрипты

В проекте есть несколько вспомогательных скриптов, которые упрощают разработку и тестирование:

*   `utils/clear_and_load_fixtures.py`:
    Очищает базу данных и загружает все тестовые фикстуры (пользователей, курсы, уроки и т.д.). Удобен для быстрого сброса состояния БД.

*   `utils/scripts_for_demo/setup_users.py`:
    Создает набор тестовых пользователей с разными ролями (админ, учитель, студент, модератор) и стандартным паролем. Полезен, если вам нужны только пользователи без полной загрузки данных.

*   `utils/scripts_for_demo/setup_test_prices.py`:
    Настраивает тестовые цены для всех дисциплин и уроков. Можно использовать для установки стандартных цен, сделать весь контент бесплатным или добавить скидки.

    **Использование:**
    ```bash
    python utils/scripts_for_demo/setup_test_prices.py setup    # Установить стандартные цены
    python utils/scripts_for_demo/setup_test_prices.py free     # Сделать весь контент бесплатным
    python utils/scripts_for_demo/setup_test_prices.py discount # Добавить примеры скидок
    ```

*   `utils/scripts_for_demo/test_yookassa.py`:
    Скрипт для тестирования интеграции с ЮKassa. Позволяет проверить подключение, создать тестовый платеж и узнать его статус.

*   `utils/admin_key_generator.py`:
    Скрипт для генерации и отправки административных ключей пользователям с ролями `admin` или `moderator`. Эти ключи требуются для первого входа пользователей с такими ролями.

## 📝 Дополнительная документация

*   [API_TESTING_GUIDE.md](API_TESTING_GUIDE.md) - Руководство по тестированию API.
*   [CELERY_GUIDE.md](CELERY_GUIDE.md) - Подробное руководство по использованию и настройке Celery.
*   [PAYMENTS_SUMMARY.md](PAYMENTS_SUMMARY.md) - Сводка по системе платежей.
*   [PAYMENT_SYSTEMS.md](Payments/PAYMENT_SYSTEMS.md) - Обзор доступных платежных систем (ЮKassa, Stripe).
*   [QUICK_START.md](Payments/QUICK_START.md) - Быстрый старт с ЮKassa.
*   [STRIPE_SETUP.md](Payments/STRIPE_SETUP.md) - Детальная настройка Stripe.
*   [YOOKASSA_SETUP.md](Payments/YOOKASSA_SETUP.md) - Детальная настройка ЮKassa.
*   [СТРУКТУРА_ДИСЦИПЛИН_И_УРОКОВ.md](СТРУКТУРА_ДИСЦИПЛИН_И_УРОКОВ.md) - Описание структуры дисциплин и уроков.
*   [СХЕМА_СТРУКТУРЫ.md](СХЕМА_СТРУКТУРЫ.md) - Визуальная схема структуры дисциплин и уроков.

## 👥 Пользователи для тестирования (после загрузки фикстур)

Все пользователи имеют пароль: `Spirocheta77`

*   **admin@a.aa** (Администратор) - имеет полный доступ к системе.
*   **teacher_1@a.aa** (Преподаватель) - может создавать и управлять своими курсами и уроками.
*   **student_1@a.aa** (Студент) - может проходить курсы и тесты, доступные ему.
*   **moderator_1@a.aa** (Модератор) - имеет права на управление контентом, но не является суперпользователем.
✨

