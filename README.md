# Code Interpreter Demo — Analytics

Демо-приложение для аналитического сценария использования Code Interpreter в Yandex Cloud AI Studio.

## Что это?

Веб-приложение, которое позволяет загрузить CSV-данные и задать аналитический вопрос на естественном языке. ИИ-модель автоматически генерирует Python-код, выполняет его в облачном контейнере и возвращает результат: текстовый анализ, графики и файлы.

Ключевые возможности:
- **Загрузка данных** — свои CSV-файлы или готовые датасеты
- **Аналитические запросы** — на естественном языке с примерами промптов
- **Стриминг результатов** — код, логи и ответ модели в реальном времени через SSE
- **Визуализации** — графики и диаграммы, сгенерированные моделью
- **Экспорт** — скачивание сгенерированных файлов (PNG, XLSX, CSV, PDF)

## Структура проекта

```
code_interpreter_demo_analytics/
├── .env.example             # Пример конфигурации
├── pyproject.toml           # Зависимости проекта
├── Dockerfile               # Docker конфигурация
├── docker-compose.yml       # Docker Compose конфигурация
├── main.py                  # FastAPI сервер
├── static/
│   ├── index.html           # Веб-интерфейс
│   ├── app.js               # Frontend логика
│   └── styles.css           # Стили
└── sample_data/
    ├── metadata.json        # Метаданные датасетов
    ├── imdb_movies.csv
    ├── sp500_top10_stocks_clean.csv
    ├── metacritic_games.csv
    ├── crypto50_combined.csv
    └── kindle_data-v2.csv
```

## Быстрый старт

### 1. Установка зависимостей

```bash
# Установить зависимости и создать виртуальное окружение
uv sync

# Активировать окружение
source .venv/bin/activate  # macOS/Linux
```

> **Примечание**:
> - Если у вас не установлен uv, установите его: `curl -LsSf https://astral.sh/uv/install.sh | sh`
> - Команда `uv sync` автоматически создает виртуальное окружение и устанавливает все зависимости из `pyproject.toml`

### 2. Настройка

Создайте файл `.env` в корне проекта:

```bash
# Скопировать образец
cp .env.example .env

# Отредактировать и добавить свои credentials
nano .env  # или vim .env
```

Содержимое `.env`:

```bash
YANDEX_API_KEY=your_api_key_here
YANDEX_FOLDER_ID=your_folder_id_here
YANDEX_CLOUD_MODEL=qwen3-235b-a22b-fp8/latest
```

### 3. Запуск

#### Вариант 1: Локальный запуск

```bash
uv run python main.py
```

Приложение будет доступно по адресу: **http://localhost:8000**

#### Вариант 2: Запуск через Docker Compose

```bash
# Убедитесь, что .env файл создан в корне проекта (см. шаг 2)

# Запустить приложение
docker compose up -d

# Просмотр логов
docker compose logs -f
```

Приложение будет доступно по адресу: **http://localhost:8000**

Для остановки:

```bash
docker compose down
```

## Использование

### Веб-интерфейс

1. **Откройте** http://localhost:8000 в браузере
2. **Загрузите CSV-файлы** или выберите из готовых датасетов
3. **Опишите аналитическую задачу** на естественном языке или выберите из примеров
4. **Наблюдайте** за генерацией и выполнением кода в реальном времени
5. **Получите результат**: текстовый анализ, графики, файлы для скачивания

### Готовые датасеты

| Датасет | Описание |
|---------|----------|
| IMDB Movies | Фильмы с рейтингами, жанрами, бюджетами и сборами |
| S&P 500 Top 10 | Дневные котировки топ-10 акций S&P 500 (2010–2026) |
| Metacritic Games | Видеоигры с метаскорами, жанрами, платформами |
| Crypto Top 50 | Дневные данные топ-50 криптовалют (2014–2026) |
| Amazon Kindle Books | 130K+ книг с рейтингами, ценами, категориями |

### Примеры аналитических запросов

- *«Проанализируй структуру данных. Покажи основные статистики и построй графики»*
- *«Найди корреляции между числовыми показателями. Построй тепловую карту»*
- *«Найди аномалии и выбросы в данных»*
- *«Построй тренды по основным показателям. Сделай прогноз»*

### API

```bash
# Загрузка файлов
curl -X POST http://localhost:8000/api/upload \
  -F "files=@data.csv"

# Запуск анализа (SSE-стрим)
curl "http://localhost:8000/api/analyze?query=Проанализируй+данные&file_ids=file_id_here"

# Список готовых датасетов
curl http://localhost:8000/api/sample-data

# Загрузка готового датасета
curl -X POST http://localhost:8000/api/upload-sample \
  -H "Content-Type: application/json" \
  -d '["imdb_movies.csv"]'

# Скачивание сгенерированного файла
curl "http://localhost:8000/api/files/{file_id}/download?filename=chart.png" -o chart.png

# Health check
curl http://localhost:8000/api/health
```

## Как это работает

### Архитектура

- **Backend**: FastAPI + AsyncOpenAI SDK для взаимодействия с Yandex Cloud API
- **Frontend**: Vanilla JS с SSE для стриминга результатов
- **Модель**: `qwen3-235b-a22b-fp8/latest` через Yandex Cloud AI Studio
- **Code Interpreter**: выполнение Python-кода в изолированном облачном контейнере

### Поток данных

1. Пользователь загружает CSV → файл сохраняется в Yandex Cloud Files API
2. Пользователь вводит запрос → отправляется в Responses API с инструментом `code_interpreter`
3. Модель генерирует Python-код → код выполняется в контейнере
4. Результаты стримятся через SSE: текст, код, логи, файлы
5. Сгенерированные файлы (графики, таблицы) доступны для скачивания

### Ключевой фрагмент кода

```python
stream = await client.responses.create(
    model=f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_CLOUD_MODEL}",
    input=query,
    tools=[{
        "type": "code_interpreter",
        "container": {"type": "auto", "file_ids": file_ids},
    }],
    stream=True,
)
```

## Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/upload` | Загрузка CSV-файлов |
| `GET` | `/api/analyze` | Запуск анализа (SSE-стрим) |
| `DELETE` | `/api/files/{file_id}` | Удаление загруженного файла |
| `GET` | `/api/files/{file_id}/download` | Скачивание сгенерированного файла |
| `GET` | `/api/sample-data` | Список готовых датасетов |
| `POST` | `/api/upload-sample` | Загрузка готового датасета |
| `GET` | `/api/health` | Health check |

## Документация

- [Yandex Cloud AI Studio](https://yandex.cloud/ru/docs/ai-studio/)
- [Code Interpreter](https://yandex.cloud/ru/docs/ai-studio/concepts/agents/tools/code-interpreter)
