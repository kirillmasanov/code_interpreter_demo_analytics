# Code Interpreter Demo Analytics — Yandex Cloud Blueprint

## 1. Введение

**Название проекта:** Code Interpreter Demo — Analytics

**Описание задачи:**

Code Interpreter Demo Analytics — это демонстрационное веб-приложение для аналитического сценария использования Code Interpreter в Yandex Cloud AI Studio. Пользователь загружает CSV-данные, задаёт аналитический вопрос на естественном языке, а ИИ-модель автоматически генерирует Python-код, выполняет его в облачном контейнере и возвращает результат: текстовый анализ, графики и файлы.

**Основные сервисы Yandex Cloud:**
- **Yandex Cloud AI Studio** — платформа для работы с AI-моделями и инструментами, включающая:
  - **Responses API** — генерация текста, вызов инструментов, стриминг ответов
  - **Code Interpreter** — выполнение Python-кода в изолированном облачном контейнере
  - **Files API** — загрузка, хранение и работа с файлами
  - **Model Gallery** — доступ к языковым моделям (в проекте используется qwen3-235b-a22b-fp8/latest)

**Цель и ожидаемый результат:**

После выполнения инструкций из этого документа вы получите работающее веб-приложение, которое:
- Демонстрирует аналитический сценарий использования Code Interpreter
- Позволяет загружать CSV-данные и задавать вопросы на естественном языке
- Выполняет Python-код в облаке и возвращает результаты в реальном времени
- Генерирует визуализации, текстовые выводы и файлы для скачивания

---

## 2. Архитектура решения

### Описание архитектуры

Приложение построено на основе FastAPI и работает как веб-сервис с простой архитектурой. Пользователь взаимодействует с приложением через веб-интерфейс:

1. **Загрузка данных**: Пользователь загружает CSV-файлы или выбирает из готовых датасетов
2. **Аналитический запрос**: Пользователь описывает задачу на естественном языке
3. **Генерация кода**: Модель генерирует Python-код для анализа данных
4. **Выполнение кода**: Код выполняется в изолированном облачном контейнере с доступом к загруженным файлам
5. **Стриминг результатов**: Через SSE (Server-Sent Events) в реальном времени передаются код, логи выполнения и текстовый ответ
6. **Результат**: Отображение текстового анализа, графиков и файлов для скачивания

### Компоненты системы

```
┌──────────────────────────────────────────────────────┐
│              Пользователь (Browser)                  │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP / SSE
                        ▼
┌──────────────────────────────────────────────────────┐
│     Frontend (HTML/CSS/JavaScript + Marked.js)       │
│  • Загрузка CSV-файлов / выбор датасетов             │
│  • Ввод аналитического запроса                       │
│  • Отображение кода, результатов, графиков           │
│  • SSE-клиент для стриминга                          │
└───────────────────────┬──────────────────────────────┘
                        │ REST API + SSE
                        ▼
┌──────────────────────────────────────────────────────┐
│           Backend (FastAPI + Python)                  │
│  • Загрузка файлов в Files API                       │
│  • Запуск анализа через Responses API                │
│  • Стриминг событий Code Interpreter                 │
│  • Скачивание сгенерированных файлов                 │
└───────────────────────┬──────────────────────────────┘
                        │ OpenAI SDK (AsyncOpenAI)
                        ▼
┌──────────────────────────────────────────────────────┐
│          Yandex Cloud AI Studio                      │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ Files API                                      │  │
│  │ • Загрузка CSV-файлов                          │  │
│  │ • Хранение сгенерированных файлов (графики)    │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ Responses API + Code Interpreter               │  │
│  │ • Генерация Python-кода для анализа            │  │
│  │ • Выполнение кода в контейнере                 │  │
│  │ • Стриминг результатов                         │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ Model Gallery                                  │  │
│  │ • LLM-модель (qwen3-235b-a22b-fp8/latest)     │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Используемые сервисы Yandex Cloud

**Основной сервис:** Yandex Cloud AI Studio

**Компоненты AI Studio, используемые в проекте:**

| Компонент | Назначение | Необходимые роли |
|-----------|------------|------------------|
| **Files API** | Загрузка CSV-файлов и скачивание сгенерированных файлов | `ai.assistants.editor` |
| **Responses API** | Генерация кода и текстовых ответов с инструментом Code Interpreter | `ai.assistants.editor` |
| **Code Interpreter** | Выполнение Python-кода в изолированном контейнере | `ai.assistants.editor` |
| **Model Gallery** | Доступ к языковым моделям | `ai.languageModels.user` |

**Итоговые роли для сервисного аккаунта:**
- `ai.assistants.editor` — для работы с Files API, Responses API и Code Interpreter
- `ai.languageModels.user` — для использования моделей из Model Gallery

### Особенности реализации

- Монолитная архитектура (один файл `main.py`)
- Асинхронная обработка запросов (AsyncOpenAI)
- SSE (Server-Sent Events) для стриминга результатов в реальном времени
- Готовые датасеты для быстрого старта
- Готовая Docker-конфигурация

---

## 3. Подготовка окружения

### Системные требования

- **Python 3.11+**
- **uv** (менеджер пакетов Python)
- **Docker и Docker Compose** (опционально, для контейнеризации)

### Установка зависимостей

#### Вариант 1: Локальная установка с uv

```bash
# Установка uv (менеджер пакетов Python)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Добавление uv в PATH
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Клонирование репозитория
git clone https://github.com/kirillmasanov/code_interpreter_demo_analytics
cd code_interpreter_demo_analytics

# Установка зависимостей и создание виртуального окружения
uv sync

# Активация окружения
source .venv/bin/activate  # macOS/Linux
```

#### Вариант 2: Docker

```bash
# Клонирование репозитория
git clone https://github.com/kirillmasanov/code_interpreter_demo_analytics
cd code_interpreter_demo_analytics

# Docker автоматически установит все зависимости при сборке
```

#### Установка Docker (Ubuntu)

Если Docker еще не установлен на вашей системе Ubuntu, выполните следующие команды:

```bash
# Обновление списка пакетов
sudo apt-get update

# Установка необходимых пакетов
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавление официального GPG ключа Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавление репозитория Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Обновление списка пакетов
sudo apt-get update

# Установка Docker Engine, containerd и Docker Compose
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Добавление текущего пользователя в группу docker (чтобы не использовать sudo)
sudo usermod -aG docker $USER

# Применение изменений в группах (требуется перелогиниться или выполнить)
newgrp docker

# Проверка установки
docker --version
docker compose version
```

### Настройка Yandex Cloud CLI (опционально)

Для автоматизации создания ресурсов установите Yandex Cloud CLI:

```bash
# Установка yc CLI
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash

# Инициализация и конфигурация
yc init
```

---

## 4. Развёртывание инфраструктуры

### 4.1. Создание сервисного аккаунта

#### Через веб-консоль:

1. Перейдите в [консоль Yandex Cloud](https://console.cloud.yandex.ru/)
2. Выберите ваш каталог
3. Перейдите в раздел "Сервисные аккаунты"
4. Нажмите "Создать сервисный аккаунт"
5. Укажите имя, например, `code-interpreter-demo-sa`
6. Добавьте описание, например, "Service account for Code Interpreter Analytics Demo"

#### Через CLI:

```bash
# Создание сервисного аккаунта
yc iam service-account create \
  --name code-interpreter-demo-sa \
  --description "Service account for Code Interpreter Analytics Demo"

# Получение ID созданного аккаунта
SA_ID=$(yc iam service-account get code-interpreter-demo-sa --format json | jq -r '.id')
echo "Service Account ID: $SA_ID"
```

### 4.2. Назначение ролей

Сервисному аккаунту необходимы роли для работы с AI Studio:

#### Через веб-консоль:

1. Откройте страницу каталога
2. Перейдите на вкладку "Права доступа"
3. Нажмите "Назначить роли"
4. Выберите сервисный аккаунт `code-interpreter-demo-sa`
5. Добавьте роли:
   - `ai.assistants.editor`
   - `ai.languageModels.user`

#### Через CLI:

```bash
# Получение FOLDER_ID
FOLDER_ID=$(yc config get folder-id)

# Назначение ролей для работы с AI Studio
yc resource-manager folder add-access-binding $FOLDER_ID \
  --role ai.assistants.editor \
  --service-account-id $SA_ID

yc resource-manager folder add-access-binding $FOLDER_ID \
  --role ai.languageModels.user \
  --service-account-id $SA_ID
```

### 4.3. Создание API ключа

#### Через веб-консоль:

1. Откройте страницу сервисного аккаунта
2. Перейдите на вкладку "API-ключи"
3. Нажмите "Создать API-ключ"
4. Укажите область действия: `yc.ai.foundationModels.execute`
5. **Важно:** Скопируйте ключ (он показывается только один раз!)

#### Через CLI:

```bash
# Создание API-ключа с областью действия для Foundation Models
API_KEY=$(yc iam api-key create \
  --service-account-id $SA_ID \
  --scopes yc.ai.foundationModels.execute \
  --format json | jq -r '.secret')
echo "API Key: $API_KEY"
```

### 4.4. Настройка переменных окружения

Создайте файл `.env` в корне проекта на основе `.env.example`:

```bash
# Скопировать образец
cp .env.example .env

# Отредактировать файл и заменить значения
nano .env  # или vim .env
```

**Автоматическое создание через CLI:**

```bash
FOLDER_ID=$(yc config get folder-id)
SA_ID=$(yc iam service-account get code-interpreter-demo-sa --format json | jq -r '.id')
API_KEY=$(yc iam api-key create \
  --service-account-id $SA_ID \
  --scopes yc.ai.foundationModels.execute \
  --format json | jq -r '.secret')

# Создать .env в корне проекта
cat > .env << EOF
YANDEX_API_KEY=$API_KEY
YANDEX_FOLDER_ID=$FOLDER_ID
YANDEX_CLOUD_MODEL=qwen3-235b-a22b-fp8/latest
EOF

echo "Файл .env создан успешно"
```

---

## 5. Запуск приложения

### Вариант 1: Запуск с использованием Python

```bash
# Из корня проекта
uv run python main.py
```

Приложение будет доступно на порту **8000**.

### Вариант 2: Запуск с использованием Docker

**Важно:** Перед запуском Docker убедитесь, что вы создали `.env` файл в корне проекта (см. раздел 4.4 "Настройка переменных окружения").

```bash
# Сборка и запуск контейнера
docker compose up -d

# Просмотр логов
docker compose logs -f

# Проверка статуса
docker compose ps
```

**Перезапуск после изменений:**

```bash
# Остановить контейнер
docker compose down

# Пересобрать образ без использования кэша
docker compose build --no-cache

# Запустить контейнер
docker compose up -d

# Или короткая версия (пересборка и запуск одной командой)
docker compose up -d --build --force-recreate
```

Приложение будет доступно на порту **8000**.

### Проверка работоспособности

Откройте в браузере:
- **При локальном запуске:** `http://localhost:8000`
- **При запуске на виртуальной машине:** `http://<публичный_IP>:8000`

Health check:
```bash
curl http://localhost:8000/api/health
```

**Примечание:** При развертывании на виртуальной машине в Yandex Cloud убедитесь, что:
- В группе безопасности открыт порт 8000
- У виртуальной машины есть публичный IP-адрес (если требуется доступ из интернета)

---

## 6. Тестирование решения

### 6.1. Загрузка данных

1. Откройте приложение в браузере
2. Загрузите свой CSV-файл перетаскиванием или выбором через диалог
3. Или выберите один из готовых датасетов:
   - **IMDB Movies** — фильмы с рейтингами, жанрами, бюджетами
   - **S&P 500 Top 10** — дневные котировки акций (2010–2026)
   - **Metacritic Games** — видеоигры с метаскорами
   - **Crypto Top 50** — данные топ-50 криптовалют (2014–2026)
   - **Amazon Kindle Books** — 130K+ книг с рейтингами и ценами
4. Нажмите «Продолжить»

### 6.2. Запуск анализа

1. Введите аналитический запрос, например:
   - *«Проанализируй структуру данных. Покажи основные статистики и построй графики»*
   - *«Найди корреляции между числовыми показателями. Построй тепловую карту»*
   - *«Найди аномалии и выбросы в данных»*
   - *«Построй тренды по основным показателям. Сделай прогноз»*
2. Или выберите один из готовых примеров
3. Нажмите «Запустить анализ»

### 6.3. Просмотр результатов

В процессе анализа вы увидите:
- **Генерация кода** — Python-код, сгенерированный моделью
- **Выполнение кода** — логи выполнения в контейнере
- **Текстовый анализ** — выводы и интерпретация результатов
- **Графики** — визуализации, созданные моделью
- **Файлы для скачивания** — экспорт результатов (PNG, XLSX, CSV, PDF)

---

## 7. Результаты и выводы

### Ожидаемый результат

После успешного тестирования вы получите:
- Автоматически сгенерированный Python-код для анализа загруженных данных
- Текстовый отчёт с выводами и интерпретацией
- Визуализации (графики, диаграммы, тепловые карты)
- Файлы для скачивания

### Возможности Code Interpreter для аналитики

- **Автоматический анализ данных**: Модель сама определяет подходящие методы анализа
- **Генерация визуализаций**: Графики matplotlib, seaborn и другие библиотеки
- **Статистический анализ**: Корреляции, распределения, выбросы, тренды
- **Прогнозирование**: Модель может строить простые прогнозы на основе данных
- **Экспорт результатов**: Сохранение в различных форматах

### Применение в реальных проектах

Code Interpreter для аналитики полезен в задачах:

1. **Бизнес-аналитика**: Анализ продаж, метрик, KPI
2. **Финансовый анализ**: Анализ котировок, портфелей, рисков
3. **Маркетинг**: Анализ кампаний, когорт, воронок
4. **Data Science**: Exploratory Data Analysis (EDA) и предобработка данных
5. **Отчётность**: Автоматическая генерация отчётов с графиками

---

## 8. Очистка ресурсов

### Остановка приложения

**Локальный запуск:**
```bash
# Остановка приложения (Ctrl+C в терминале)
```

**Docker:**
```bash
# Остановка контейнера
docker compose down

# Полная очистка (включая volumes)
docker compose down -v
```

### Удаление сервисного аккаунта (опционально)

```bash
# Получение ID сервисного аккаунта
SA_ID=$(yc iam service-account get code-interpreter-demo-sa --format json | jq -r '.id')

# Удаление API ключей
yc iam api-key list --service-account-id $SA_ID --format json | \
  jq -r '.[].id' | \
  xargs -I {} yc iam api-key delete {}

# Удаление сервисного аккаунта
yc iam service-account delete $SA_ID
```

---

## 9. Полезные ссылки

### Документация Yandex Cloud

- [Yandex Cloud AI Studio](https://yandex.cloud/ru/docs/ai-studio/)
- [Code Interpreter](https://yandex.cloud/ru/docs/ai-studio/concepts/agents/tools/code-interpreter)
- [Управление доступом в Yandex Cloud](https://cloud.yandex.ru/docs/iam/)
- [Сервисные аккаунты](https://cloud.yandex.ru/docs/iam/concepts/users/service-accounts)

### Репозиторий проекта

- [GitHub: code_interpreter_demo_analytics](https://github.com/kirillmasanov/code_interpreter_demo_analytics)

### Дополнительная документация

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [OpenAI SDK Documentation](https://platform.openai.com/docs/api-reference)

---

## Примечания

### Рекомендации

- Используйте готовые датасеты для быстрого тестирования
- Для больших файлов анализ может занять несколько минут
- Модель лучше работает с конкретными и детальными запросами
- Для сложных задач можно указать конкретные библиотеки или методы анализа

### Стоимость использования

Стоимость использования зависит от:
- Количества запросов к модели
- Объёма загруженных файлов
- Времени выполнения кода в контейнере

Актуальные цены см. на странице тарифов [Yandex Cloud AI Studio](https://yandex.cloud/ru/docs/ai-studio/pricing).
