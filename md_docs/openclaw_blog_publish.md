# Инструкция для OpenClaw: публикация тестовой статьи в blog

Используй этот сценарий, когда нужно проверить публикацию статьи в `portfolio` через API.

## 1. Что нужно знать заранее

- Метод: `POST`
- Endpoint: `/api/openclaw/posts/`
- Полный URL на production: `https://roman-it.dev/api/openclaw/posts/`
- Авторизация: `Authorization: Bearer <OPENCLAW_BLOG_API_TOKEN>`
- Альтернативный заголовок авторизации: `X-API-Key: <OPENCLAW_BLOG_API_TOKEN>`
- Формат тела запроса: `application/json`

Если токен не задан на сервере, API вернет `503 OpenClaw publishing is not configured`.
Если токен неверный, API вернет `401 Unauthorized`.

## 2. Обязательные поля JSON

- `title`: заголовок статьи, непустая строка
- `content`: Markdown-содержимое статьи, непустая строка

## 3. Необязательные поля JSON

- `description`: короткое описание статьи
- `slug`: URL slug; если не передан, сервер соберет его из заголовка
- `language`: `ru` или `en`, по умолчанию `ru`
- `published_date`: ISO datetime, например `2026-05-13T12:00:00+03:00`; если не передан, сервер поставит текущее время
- `tags`: массив тегов

Допустимые форматы тегов:

- строка, например `"OpenClaw"`
- объект, например `{ "name_ru": "Автоматизация", "name_en": "Automation" }`

## 4. Готовый тестовый запрос

Отправь ровно такой запрос, подставив реальный токен:

```bash
curl -X POST "https://roman-it.dev/api/openclaw/posts/" \
  -H "Authorization: Bearer <OPENCLAW_BLOG_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Тестовая статья OpenClaw",
    "description": "Проверка публикации статьи через API OpenClaw.",
    "slug": "testovaya-statya-openclaw",
    "language": "ru",
    "tags": [
      "OpenClaw",
      {"name_ru": "Тест", "name_en": "Test"},
      {"name_ru": "Автоматизация", "name_en": "Automation"}
    ],
    "content": "# Тестовая статья OpenClaw\n\nЭто тестовая публикация, созданная через API.\n\n## Что проверить\n\n- статья появилась в списке блога;\n- карточка открывается без ошибок;\n- теги привязались к статье.\n\n## Техническая заметка\n\nЕсли этот текст виден на сайте, значит endpoint публикации работает корректно."
  }'
```

## 5. Ожидаемый успешный ответ

При успехе сервер вернет HTTP `201` и JSON такого вида:

```json
{
  "id": 123,
  "slug": "testovaya-statya-openclaw",
  "language": "ru",
  "url": "/ru/blog/post/testovaya-statya-openclaw/",
  "published_date": "2026-05-13T12:00:00+03:00"
}
```

`id` и `published_date` будут своими, а `url` можно использовать для проверки публикации.

## 6. Что сделать после ответа 201

1. Открой страницу статьи по домену сайта: `https://roman-it.dev` + значение поля `url` из ответа.
2. Убедись, что статья отображается в списке блога на соответствующем языке.
3. Проверь, что у статьи есть теги `OpenClaw`, `Тест` и `Автоматизация`.

## 7. Что делать при ошибках

- `400 Field "title" is required`: не передан заголовок
- `400 Field "content" is required`: не передан текст статьи
- `400 Unsupported language`: передан язык, отличный от `ru` или `en`
- `400 Field "tags" must be a list`: поле `tags` передано не массивом
- `401 Unauthorized`: неверный токен или заголовок авторизации не отправлен
- `503 OpenClaw publishing is not configured`: на сервере не задан `OPENCLAW_BLOG_API_TOKEN`

## 8. Короткая инструкция для самого бота

Если нужно передать задачу OpenClaw в одном блоке, используй этот текст:

```text
Опубликуй тестовую статью в blog через POST https://roman-it.dev/api/openclaw/posts/.
Передай заголовок Authorization: Bearer <OPENCLAW_BLOG_API_TOKEN> и Content-Type: application/json.
Тело запроса:
{
  "title": "Тестовая статья OpenClaw",
  "description": "Проверка публикации статьи через API OpenClaw.",
  "slug": "testovaya-statya-openclaw",
  "language": "ru",
  "tags": ["OpenClaw", {"name_ru": "Тест", "name_en": "Test"}, {"name_ru": "Автоматизация", "name_en": "Automation"}],
  "content": "# Тестовая статья OpenClaw\n\nЭто тестовая публикация, созданная через API.\n\n## Что проверить\n\n- статья появилась в списке блога;\n- карточка открывается без ошибок;\n- теги привязались к статье."
}
После ответа 201 верни JSON ответа и полный URL опубликованной статьи.
```