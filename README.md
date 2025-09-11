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
1. Склонируйте репозиторий.

Выбор команды зависит от оболочки. && работает в Bash, Git Bash, WSL и в большинстве современных шеллов; для максимальной совместимости приведены варианты для разных сред.

Unix / macOS / Git Bash / WSL (однострочно):

```bash
git clone <repo-url> && cd LearningPlatform
```

Windows (cmd.exe) — безопасно для всех версий Windows:

```cmd
git clone <repo-url>
cd LearningPlatform
```

PowerShell (если && не поддерживается):

```powershell
git clone <repo-url>; Set-Location LearningPlatform
# или
git clone <repo-url>; cd LearningPlatform
```

Если хотите оставить одну строку в README — используйте Bash-версию и рядом укажите примечание о Windows.

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

## 6. Документы и подробные руководства
- API тестирование: API_TESTING_GUIDE.md
- Celery: CELERY_GUIDE.md
- Платежи: PAYMENTS_SUMMARY.md, Payments/QUICK_START.md, Payments/YOOKASSA_SETUP.md, Payments/STRIPE_SETUP.md, Payments/PAYMENT_SYSTEMS.md
- Развёртывание и CI/CD: DEPLOYMENT.md

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

## 8. Дальше — куда идти (рекомендуемая последовательность чтения)
README должен быть "входной картой". Ниже — простая логика переходов в зависимости от вашей цели. В README полезно оставить ссылку на следующий документ по логике: короткое описание + ссылка.

- Развернуть проект и начать разработку (Docker): сначала следуйте разделу 1 этого README, затем:
  - Если планируете работать с фоновой обработкой задач: далее — CELERY_GUIDE.md (запуск Celery, Flower, конфигурация)
  - Если нужно проверить платежи/симуляцию транзакций: далее — Payments/QUICK_START.md
  - Если нужно тестировать API вручную: далее — API_TESTING_GUIDE.md
  - Если нужен прод/CI/CD — откройте DEPLOYMENT.md

- Локальная разработка без Docker: после раздела 2 README — посмотрите:
  - CELERY_GUIDE.md — если используются фоновые задачи
  - Payments/QUICK_START.md — настройка тестовых платёжных сценариев

- Полезные детали и отладка:
  - Для загрузки/очистки demo-данных: utils/clear_and_load_fixtures.py (см. раздел 4)
  - Для быстрого создания пользователей/цен: utils/scripts_for_demo/*
## 9. Коротко про CI/CD и проверки
- GitHub Actions (.github/workflows/ci-cd.yml) запускается на пуши в ветки main/master/develop и в feature/*, bugfix/*, hotfix/*; а также на PR в develop и main/master.
- Джобы:
  - Lint & Test: black/isort/flake8 + pytest с тестовыми настройками (DJANGO_SETTINGS_MODULE=config.test_settings). Если тесты/линтеры падают — деплой не запустится.
  - Build Docker images: пробная сборка образов web и nginx.
  - Deploy: выполняется только при пуше в main. Заходит на сервер по SSH и запускает docker compose с прод-овэррайдом.
- Секреты, необходимые для деплоя: SSH_HOST, SSH_USER, SSH_KEY, DEPLOY_PATH. Опционально: SSH_PORT (если не 22). Подробности — [.github/README_CICD_SECRETS.md](.github/README_CICD_SECRETS.md) и [DEPLOYMENT.md](DEPLOYMENT.md).

Проверки локально (как повторить CI):
- Линтеры:
  - black --check .
  - isort --check-only .
  - flake8 .
- Тесты (варианты):
  - Без Docker (использует in‑memory SQLite):
    - Linux/macOS: DJANGO_SETTINGS_MODULE=config.test_settings pytest -q -o addopts=''
    - Windows PowerShell: $env:DJANGO_SETTINGS_MODULE="config.test_settings"; pytest -q -o addopts=''
  - Через Docker (разовый контейнер):
    docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.test_settings web python -m pytest -q -o addopts=''
  - Через Docker (поднять db/redis и гонять тесты в running web):
    make test-docker  # или python dev.py test-docker
- Покрытие (pytest-cov):
  - Локально: DJANGO_SETTINGS_MODULE=config.test_settings pytest --cov=. --cov-report=term-missing -q -o addopts=''
  - В Docker (разовый): docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.test_settings web python -m pytest --cov=. --cov-report=term-missing -q -o addopts=''

Swagger и документация API
- Swagger UI доступен по адресу:
  - Локально: http://localhost:8000/api/schema/swagger-ui/
  - На сервере: http://<SERVER_IP>/api/schema/swagger-ui/
- Redoc: http://<host>/api/schema/redoc/

Фикстуры / начальные данные
- Безопасный загрузчик: utils/clear_and_load_fixtures.py (подтверждение, проверки, обход проблем с auth.permission).
- Быстрый старт (в Docker):
  docker compose exec web python utils/clear_and_load_fixtures.py --yes
- В проде используйте аккуратно. Скрипт умеет блокироваться при DEBUG=False (см. флаги в скрипте).

Для преподавателя (проверка ДЗ)
- Достаточно оформить PR из своей ветки в develop. В пайплайне выполняются линтеры/тесты/сборка — их статус виден в PR.
- Деплой не обязателен. Если нужен демонстрационный деплой — мёрдж в main запустит джоб Deploy (при наличии секретов в репозитории).

---

## 10. Пошаговая «1 → 2 → 3» последовательность (от клона до работы и тестирования)

1) Клонирование и запуск (Quick Start — Docker)
   - Склонируйте репозиторий и перейдите в папку проекта.
   - Создайте .env из .env.example и заполните переменные. Для локали:
     - BASE_URL=http://127.0.0.1:8000
     - ALLOWED_HOSTS=127.0.0.1,localhost
   - Запустите: docker-compose up -d --build
   - Миграции и фикстуры: docker-compose exec web python manage.py migrate && docker-compose exec web python utils/clear_and_load_fixtures.py --yes

2) Полезные сервисы и отладка
   - Celery/Redis — см. CELERY_GUIDE.md
   - Swagger UI — http://localhost:8000/api/schema/swagger-ui/

3) Тесты/линтеры локально
   - См. раздел выше «Коротко про CI/CD и проверки».

← [Назад: «Документация проекта»](README.md) | **Далее:** [CELERY_GUIDE.md](CELERY_GUIDE.md) → | [Все руководства](README.md)

   - Создайте .env из .env.example и заполните значения.
   - Запустите: docker-compose up -d --build
   - Запустите миграции и (опционально) загрузите фикстуры: docker-compose exec web python manage.py migrate && docker-compose exec web python utils/clear_and_load_fixtures.py --yes

2) Настройка дополнительной инфраструктуры и сервисов
   - Redis/Celery (см. CELERY_GUIDE.md). Для локали можно запустить контейнер redis.
   - Настройка платёжных провайдеров: заполните ключи в .env и следуйте Payments/QUICK_START.md (YooKassa/Stripe).
   - Настройте webhook (ngrok / Cloudflare Tunnel) для локальной отладки платежей.

3) Тестирование и отладка
   - API: используйте API_TESTING_GUIDE.md для примеров curl и получения JWT токенов.
   - Скрипты для разработки: utils/scripts_for_demo/* (создать пользователей/цен/демо‑платежи).
   - Тесты: запустите pytest (локально или в контейнере через Makefile/dev.py). См. pytest.ini и config/test_settings.py.

Эта последовательность — минимальный путь от A до Z: клонирование → окружение и сервисы → тестирование и отладка.
Если нужно, могу превратить её в отдельный GETTING_STARTED.md с чек‑листом и командой копирования/вставки(Сообщите в ЛК.)

---

## Краткий чек‑лист (Copy & Paste для быстрого запуска)

# Docker (рекомендуется)
cp .env.example .env && docker-compose up -d --build && docker-compose exec web python manage.py migrate && docker-compose exec web python utils/clear_and_load_fixtures.py --yes

# Локально (без Docker)
python -m venv .venv && .venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python utils/clear_and_load_fixtures.py --yes

---

← [Назад: «Документация проекта»](README.md) | **Далее:** [CELERY_GUIDE.md](CELERY_GUIDE.md) → | [Все руководства](README.md)
