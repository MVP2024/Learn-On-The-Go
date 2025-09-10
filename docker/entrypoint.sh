#!/bin/bash
set -euo pipefail

# Простая точка входа, используемая сервисами docker-compose для:
# - установки зависимостей Python
# - ожидания доступа к TCP-порту базы данных
# - запуска выбранного сервиса (web / celery / celery-beat / flower)

# Установить зависимости (быстро для разработчиков; используйте встроенный образ для prod)
# Установить зависимости (быстро для разработчиков; используйте встроенный образ для prod)
if [ -f "/code/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install --no-cache-dir -r /code/requirements.txt
fi


# Ждём, пока БД примет TCP-соединения
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}

python - <<'PY'
import socket, os, time, sys
host = os.getenv('DB_HOST', 'db')
port = int(os.getenv('DB_PORT', '5432'))
print('Waiting for DB at %s:%s' % (host, port))
for i in range(120):
    try:
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        print('DB reachable')
        sys.exit(0)
    except Exception as e:
        if i % 5 == 0:
            print('still waiting for db...', e)
        time.sleep(1)
print('Timed out waiting for DB', file=sys.stderr)
sys.exit(1)
PY

echo "db ready"

# Выбираем службу для запуска
SERVICE=${1:-}
shift || true
case "$SERVICE" in
  web)
    echo "Running Django web server"
    python /code/manage.py migrate --noinput || true
    exec python /code/manage.py runserver 0.0.0.0:8000
    ;;
  celery)
    echo "Starting Celery worker"
    exec celery -A config worker --loglevel=info --concurrency=2
    ;;
  celery-beat)
    echo "Starting Celery beat"
    exec celery -A config beat --loglevel=info
    ;;
  flower)
    echo "Starting Flower"
    exec celery -A config flower --port=5555
    ;;
  *)
    echo "Executing passed command: $SERVICE $@"
    exec "$SERVICE" "$@"
    ;;
esac
