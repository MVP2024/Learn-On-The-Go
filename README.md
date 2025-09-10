# LearningPlatform

LearningPlatform — образовательная платформа на Django + DRF. Позволяет создавать и проходить дисциплины, уроки и тесты; управлять пользователями, ролями, ценами и оплатой (YooKassa / Stripe). Проект ориентирован на локальную разработку и развёртывание через Docker Compose.

Цель этого README — показать быстрый, воспроизводимый путь "от клона репозитория до работающего окружения" и дать ссылки на дополнительные руководства.

Содержание
- Быстрый старт (локально и через Docker)
- Настройка .env и безопасность
- Команды для миграций, фикстур и тестов
- Краткое описание структуры репозитория
- Куда смотреть дальше (доп. доки)

---

## 1. Быстрый старт — Docker (рекомендуется)
1. Склонируйте репозиторий:

```bash
git clone <repo-url> && cd LearningPlatform
```

2. Скопируйте пример переменных окружения и отредактируйте `.env` (см. раздел ниже):

```bash
cp .env.example .env
# Windows (cmd): copy .env.example .env
```

3. Запуск через docker-compose:

```bash
docker-compose up -d --build
```

4. Примените миграции и загрузите demo-данные (в контейнере web):

```bash
docker-compose exec web python manage.py migrate
# опционально: загрузить fixtures (внимание: очищает данные)
docker-compose exec web python utils/clear_and_load_fixtures.py --yes
```

5. Создать суперпользователя (если нужно):

```bash
docker-compose exec web python manage.py createsuperuser
```

Доступы по умолчанию (после загрузки фикстур): admin@a.aa / Spirocheta77 и др.; см. fixtures/initial_data.json

Порты:
- Django: http://localhost:8000/
- Swagger API: http://localhost:8000/api/schema/swagger-ui/
- Flower (если включён): http://localhost:5555/

---

## 2. Быстрый старт — локально (без Docker)
1. Создайте виртуальное окружение и установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate  # или .venv\Scripts\activate на Windows
pip install -r requirements.txt
```

2. Создайте `.env` из `.env.example` и заполните значения.
3. Примените миграции и запустите сервер:

```bash
python manage.py migrate
python manage.py runserver
```

4. Запустите Redis/Celery отдельно, если используете фоновые задачи (см. CELERY_GUIDE.md).

---

## 3. Настройка `.env` и безопасность
- В репозитории есть `.env.example` с placeholder-значениями — используйте его как шаблон.
- Никогда не коммитьте реальный `.env` с секретами. `.gitignore` уже содержит `.env`.
- Секреты (SECRET_KEY, Stripe/YooKassa ключи, пароли БД) должны храниться в CI/секретном хранилище и в локальном `.env` только для разработки.
- `.coveragerc` должен быть в репозитории (унифицированный, без абсолютных путей). Локальные переопределения можно хранить в `.coveragerc.local` и добавить его в `.gitignore`.

---

## 4. Команды и полезные скрипты
- Применение миграций:
  - Локально: python manage.py migrate
  - В Docker: docker-compose exec web python manage.py migrate

- Загрузка demo-данных / очистка:
  - `python utils/clear_and_load_fixtures.py --yes` — безопасный скрипт; по умолчанию запрещён в production (DEBUG=False) без ALLOW_FIXTURE_CLEAR=1.

- Создание пользователей/примеров цен/платежей:
  - `python utils/scripts_for_demo/setup_users.py` — создаёт тестовых пользователей (admin, teacher, student, moderator) с паролем Spirocheta77
  - `python utils/scripts_for_demo/setup_prices.py [setup|free|discount]` — настройка цен/скидок
  - `python utils/scripts_for_demo/stripe_demo.py` / `yookassa_demo.py` — вспомогательные скрипты для тестирования платёжных интеграций

- Celery (dev): `python start_celery.py` — удобный скрипт-обёртка (для отладки). Для продакшена используйте systemd/supervisor/containers (см. CELERY_GUIDE.md).

- Тесты:
  - `pytest` (в проекте настроен pytest-django)
  - В тестах используется config.test_settings: in-memory SQLite и CELERY_ALWAYS_EAGER=True

---

## 5. Краткая структура проекта
- Admin/ — управление админ-ключами
- Users/ — кастомная модель пользователя, регистрация, профиль
- Disciplines/ — предметы (дисциплины), разделы
- Lessons/ — уроки и прогресс студентов
- Exercises/ — тесты/вопросы/прослушивания
- Payments/ — логика платежей, интеграция с YooKassa и Stripe
- utils/ — вспомогательные утилиты, tasks, скрипты для загрузки фикстур
- fixtures/ — initial_data.json (demo-данные)

---

## 6. Документы и подробные руководства
- API тестирование: API_TESTING_GUIDE.md
- Celery: CELERY_GUIDE.md
- Платежи: PAYMENTS_SUMMARY.md, Payments/QUICK_START.md, Payments/YOOKASSA_SETUP.md, Payments/STRIPE_SETUP.md, Payments/PAYMENT_SYSTEMS.md

---

## 7. Коротко про папку utils и utils/scripts_for_demo
- utils/ — вспомогательные модули, включая:
  - celery_tasks.py — реализация фоновых задач и обёрток TaskWrapper (поддержка запуска и в среде без Celery для тестов);
  - clear_and_load_fixtures.py — безопасный CLI для очистки БД и загрузки fixtures/initial_data.json; поддерживает dry-run, проверку, резервные обходы для auth.Permission;
  - diag_load_fixtures.py — инструмент для поэлементной диагностики fixtures (проверяет, какие записи могут вызвать ошибки при loaddata);
  - image_validators.py — валидатор изображений (Pillow) — проверяет формат и размер;
  - profanity_filter.py и mixins.py — базовая проверка запрещённых слов в сериализаторах;
  - services.py, paginators.py, common_mixins.py — общие сервисы, пагинаторы и миксины для ViewSet'ов.

- utils/scripts_for_demo — автономные скрипты для локальной разработки (запускаются как python file.py и настраивают окружение через django.setup()):
  - setup_users.py — создаёт набор тестовых пользователей и групп (используйте для локальной разработки/demo);
  - setup_prices.py — выставляет примерные цены или делает контент бесплатным;
  - stripe_demo.py / yookassa_demo.py — простые скрипты для проверки подключения к платёжным сервисам и создания тестовых платежей.

---
