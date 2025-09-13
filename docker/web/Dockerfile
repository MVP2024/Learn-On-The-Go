FROM python:3.11-slim

# Устанавливаем зависимости системы, необходимые для psycopg2 и Pillow
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /code

# Копируем requirements.txt и устанавливаем Python-зависимости
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . /code/

# Создаем директории для staticfiles и media, если их еще нет
RUN mkdir -p /code/staticfiles && mkdir -p /code/media

# Открываем порт
EXPOSE 8000

# Команда по умолчанию (переопределяется в entrypoint.sh)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]