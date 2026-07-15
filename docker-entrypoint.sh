#!/bin/bash
set -e

# Проверка переменной USE_SQLITE
if [[ "${USE_SQLITE}" == "true" ]]; then
    echo "Using SQLite database..."
else
    # Ждем, пока PostgreSQL база данных будет доступна
    echo "Waiting for PostgreSQL database..."
    python -c "
import time
import psycopg2

while True:
    try:
        psycopg2.connect(
            dbname='${DB_NAME}',
            user='${DB_USER}',
            password='${DB_PASSWORD}',
            host='${DB_HOST}',
            port='${DB_PORT}'
        )
        break
    except psycopg2.OperationalError:
        print('Database not ready yet. Waiting...')
        time.sleep(1)
"
    echo "Database is ready!"
fi

# Применение миграций
echo "Applying migrations..."
python manage.py migrate

# Сборка статических файлов
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Создание директорий для медиа-файлов, если они не существуют
mkdir -p /app/media/markdownx
mkdir -p /app/media/uploads/$(date +%Y/%m/%d)

# Проверка существования суперпользователя и создание при необходимости
echo "Checking for superuser..."
python -c "
import os
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME}').exists():
    User.objects.create_superuser('${DJANGO_SUPERUSER_USERNAME}', '${DJANGO_SUPERUSER_EMAIL}', '${DJANGO_SUPERUSER_PASSWORD}')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"

# Запуск сервера в зависимости от MODE
if [[ "${MODE}" == "development" ]]; then
    echo "Starting development server..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "Starting Gunicorn server..."
    exec gunicorn mysite.wsgi:application --bind 0.0.0.0:8000 --workers=4 --threads=4 --worker-class=gthread --worker-tmp-dir=/dev/shm --timeout=120 --access-logfile=- --error-logfile=-
fi