# Развёртывание и CI/CD

В этом документе — пошаговая инструкция по настройке сервера, CI/CD (GitHub Actions) и деплою проекта.

## 0. Предпосылки
- У вас есть VM (Linux, например Ubuntu 22.04 LTS).
- На VM установлены: Docker, Docker Compose, Git.
- Настроен доступ по SSH по ключу.
- В репозитории настроены Secrets для GitHub Actions.

## 1. Подготовка сервера (однократно)
1) Установите Docker и Compose (если ещё нет):
   - sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg
   - По инструкции docs.docker.com установите Docker Engine и docker compose plugin
2) Создайте директорию для приложения:
   - sudo mkdir -p /opt/learningplatform
   - sudo chown -R $USER:$USER /opt/learningplatform
   - sudo chmod 700 /opt/learningplatform
3) Скопируйте на сервер .env (боевой):
   - Через nano: nano /opt/learningplatform/.env
     - вставьте содержимое, сохранить: Ctrl+O, Enter; выйти: Ctrl+X
   - или по scp: scp "D:\\Project\\courses\\LearningPlatform\\.env" user@SERVER_IP:/opt/learningplatform/.env
   - права: chmod 600 /opt/learningplatform/.env
4) (Опционально) Откройте порт 80 (HTTP) в фаерволе: sudo ufw allow 80/tcp

Подсказки по nano
- открыть: nano /path/file
- сохранить: Ctrl+O, затем Enter
- выйти: Ctrl+X
- вставка в терминале: Shift+Insert или правый клик (зависит от клиента)

Полезные проверки
- Файл .env существует: ls -l /opt/learningplatform/.env
- Порт 80 слушает nginx: sudo ss -lntp | grep :80
- Контейнеры запущены: docker compose ps

## 2. Структура контейнеров
- db: Postgres
- redis: Redis
- web: Django (gunicorn в проде)
- celery: Celery worker
- celery-beat: Celery beat
- flower: мониторинг (опционально)
- nginx: reverse proxy и раздача статики

Для локальной разработки используется docker-compose.yaml. Для продакшена есть docker-compose.prod.yaml, который стартует gunicorn и nginx.

## 3. Ручной деплой (разово для проверки)
На сервере:
- git clone <repo-url> /opt/learningplatform
- cd /opt/learningplatform
- Убедитесь, что .env существует.
- docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d --build
- docker compose exec -T web python manage.py migrate --noinput
- docker compose exec -T web python manage.py collectstatic --noinput
- Откройте http://<SERVER_IP>

## 4. GitHub Actions (CI/CD)
Workflow .github/workflows/ci-cd.yml запускается на push/PR и состоит из трёх джоб:
- lint_and_test — black, isort, flake8 и pytest с DJANGO_SETTINGS_MODULE=config.test_settings
- docker_build — сборка образов web и nginx (валидирует Dockerfile)
- deploy — автодеплой на сервер по SSH при пуше в main

Секреты в GitHub (Settings → Secrets and variables → Actions)
- SSH_HOST — IP/домен сервера
- SSH_USER — пользователь для SSH
- SSH_KEY — приватный SSH ключ (BEGIN/END OPENSSH PRIVATE KEY)
- DEPLOY_PATH — путь на сервере, например /opt/learningplatform
- (Опционально) SSH_PORT — нестандартный порт SSH, если не 22

Примечания
- Если нет DEPLOY_PATH/.env — деплой прервётся с ошибкой (безопасность).
- Порт можно указать секретом SSH_PORT; по умолчанию 22.

## 5. Как работает deploy job
- Подключается по SSH к серверу (appleboy/ssh-action)
- Клонирует/обновляет репозиторий в $DEPLOY_PATH
- Проверяет наличие .env
- Запускает docker compose с прод-овэррайдом (gunicorn + nginx)
- Применяет миграции и collectstatic

## 6. Обновление
Достаточно пуша в main. После зелёных проверок Actions выполнит деплой.

## 7. Траблшутинг
- .env не найден — разместите файл в DEPLOY_PATH/.env и дайте права 600
- Порт 80 занят — освободите процесс, либо измените mapping в docker-compose.prod.yaml
- Ошибка миграций — проверьте переменные БД и доступность Postgres
- Nginx отдаёт 502 — проверьте логи web/nginx: docker compose logs web nginx
- ALLOWED_HOSTS — в проде читайте из .env: ALLOWED_HOSTS=SERVER_IP,localhost (DEBUG=False)

## 8. Безопасность
- Никогда не коммитьте .env
- Ограничьте SSH доступ (fail2ban, ufw, нестандартный порт SSH — секрет SSH_PORT)
- В проде используйте HTTPS (certbot + nginx)
