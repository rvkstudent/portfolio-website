#!/bin/bash
# deploy.sh — загрузка изменений на сервер
# Запускать из корня проекта: bash scripts/deploy.sh
set -e

SERVER="target-srv"
REMOTE_PATH="/home/roman/portfolio-website"
CONTAINER="migration-web-1"
COMPOSE_PATH="/home/roman/migration"

echo "=== 1. Сборка статики ==="
cd "$(dirname "$0")/.."
python3 manage.py collectstatic --noinput 2>/dev/null || echo "  (static collection skipped - run in Docker)"

echo "=== 2. Копирование на сервер ==="
rsync -avz --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='.venv' \
    --exclude='media' \
    --exclude='staticfiles' \
    --exclude='data.json' \
    --exclude='service-account.json' \
    --exclude='.gitignore' \
    --exclude='.vscode' \
    --exclude='.idea' \
    -e ssh \
    ./ "${SERVER}:${REMOTE_PATH}/"

echo "=== 3. Копирование в Docker контейнер ==="
ssh "${SERVER}" "docker cp ${REMOTE_PATH}/. ${CONTAINER}:/app/"

echo "=== 4. Перезапуск web ==="
ssh "${SERVER}" "cd ${COMPOSE_PATH} && docker compose up -d web"

echo ""
echo "✅ Деплой завершён!"
