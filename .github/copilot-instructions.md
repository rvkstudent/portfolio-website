# Portfolio Website — Django проект

## Структура проекта

```
portfolio-website/
├── anki/           # Приложение Anki (флеш-карточки)
│   ├── views.py    # API: due, stats, submit, search, add-to-queue
│   ├── models.py   # AnkiNote, CardProgress (SM-2)
│   ├── urls.py     # Маршруты /anki/api/*
│   └── static/anki/js/anki.js  # Фронтенд (SM-2 в браузере)
├── blog/           # Блог
├── portfolio/      # Портфолио проектов
├── mysite/         # Настройки Django
│   └── settings.py # Основной конфиг
├── templates/      # Глобальные шаблоны
│   └── anki/study.html  # Шаблон Anki
├── nginx/          # Конфиг nginx
├── scripts/        # Вспомогательные скрипты
│   └── deploy.sh   # Деплой на сервер
├── docker-compose.yml
├── Dockerfile
└── manage.py
```

## Anki App (флеш-карточки)

### API endpoints
| Метод | Путь | Описание |
|---|---|---|
| GET | `/anki/api/due/` | Карточки на сегодня (due + новые) |
| POST | `/anki/api/submit/` | Отправить оценку (`note_id`, `quality` 1-5) |
| GET | `/anki/api/stats/` | Статистика интервалов |
| GET | `/anki/api/search/?q=` | Поиск слов |
| POST | `/anki/api/add-to-queue/` | Добавить карточку в изучение |

### Алгоритм SM-2
Реализован в `anki/models.py` (метод `process_response`):
- `quality 1` — сброс (interval=0, ease_factor-=0.2)
- `quality 2-3` — пересмотр (interval не меняется, ease_factor-=0.1)
- `quality 4-5` — успех (interval *= ease_factor, ease_factor+=0.05)
- Новые карточки: max(0, 20 - due_count) случайных неповторённых

### Фронтенд (anki.js)
- Поиск через Ctrl+P или кнопку 🔍
- Добавление слов через кнопку "➕ Добавить" в результатах поиска
- На лицевой стороне карточки — только слово (без транскрипции/контекста)
- Горячие клавиши: Пробел (показать ответ), 1-5 (оценка)

## Сервер (target-srv)

**Rocky Linux 8.10**, пользователь `roman`
Путь: `/home/roman/migration/docker-compose.yml`
Код Django: внутри контейнера `migration-web-1` в `/app/`

### Деплой
```bash
bash scripts/deploy.sh
```
Что делает:
1. Копирует файлы на сервер через rsync
2. Копирует в Docker контейнер (`docker cp`)
3. Перезапускает web контейнер (`docker compose up -d web`)

### Docker Compose
```yaml
nginx → web (Django) → db (PostgreSQL 14)
xray: REALTITY 9443 + WS 8443
```
nginx проксирует: `/ → web:8000`, `/ws/ → xray:8443`

### Важные моменты
- Django settings в `/app/mysite/settings.py`
- БД: PostgreSQL (в Docker), дамп в `/home/roman/migration/pg_dump_anki_20260715.sql.gz`
- Для теста API: `ssh target-srv "curl -s 'https://roman-it.dev/anki/api/due/'"`
- Логи: `ssh target-srv "docker logs migration-web-1 --tail 20"`
- После изменений в шаблонах — нужен перезапуск web контейнера (Django кэширует шаблоны в production)

## Настройки Django (mysite/settings.py)
- DEBUG=False (production)
- SECURE_SSL_REDIRECT зависит от env
- ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'roman-it.dev', 'www.roman-it.dev', 'web']
- База: `db` (Docker hostname), порт 5432

## GitHub
Репозиторий: https://github.com/rvkstudent/portfolio-website
Ветка: `main`
