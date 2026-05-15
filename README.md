# MineSweeper.com

## Оглавление

- [Введение](#введение)
- [Скриншот](#скриншот)
- [Что сделано, для кого и зачем](#что-сделано-для-кого-и-зачем)
- [Установка](#установка)
- [Перенос данных SQLite → PostgreSQL](#перенос-данных-sqlite--postgresql)
- [Использование](#использование)
- [Настройка Google OAuth (вход через Google)](#настройка-google-oauth-вход-через-google)
- [Функционал](#функционал)
- [Зависимости](#зависимости)
- [Деплой на Railway](#деплой-на-railway)
- [Переменные окружения (.env)](#переменные-окружения-env)

## Введение

Этот проект - веб-приложение **«Сапёр»** на **Django**: игра в браузере, таблицы рекордов, отдельный режим **логических пазлов**, вход через логин или Google (django-allauth), подписка **Pro** через **Stripe** и текстовые **ИИ-подсказки** на базе **Google Gemini** (если задан API-ключ).

- **Мультиязычный интерфейс** - казахский, русский, английский,
- **Интеграция с Gemini** - пояснения к подсказке и разбор ошибки в пазле (с лимитами для бесплатных аккаунтов)
- **Pro** - оплата Stripe, дополнительные темы доски и безлимит ИИ-разборов в пазлах.
- **ВАЖНО**: для теста можно получить статус Pro совершенно бесплатно -  нажав на кнопку "Upgrade to Pro" в левом баре, пролистав ниже и нажав на кнопку "[Test] Activate Pro for free"
- **Профили** с аватаром, рекорды и пазлы с прогрессом

## Скриншот


![Игра](https://i.ibb.co.com/kssxxrPK/Screenshot-2026-05-15-200002.png)
![Профиль](https://i.ibb.co.com/QF8m6JDh/Screenshot-2026-05-15-201435.png)

## Что сделано, для кого и зачем

### Что сделано

Собрана полноценная игровая платформа вокруг классического сапёра: сервер хранит партию и состояние пазлов, начисляет рекорды, интегрирует оплату и опциональный ИИ-текст к подсказкам - без необходимости ставить отдельное приложение на устройство.

### Для кого это

- **Игрокам**, которым нужен быстрый «Сапёр» в браузере на ПК или телефоне.
- **Тем, кто любит чистую логику** - цепочка пазлов с одним выводимым ходом и объяснением после ошибки.
- **Пользователям, готовым поддержать проект** - подписка Pro открывает темы и снимает лимиты ИИ в пазлах.

### Почему это ценно

- **Ясные правила и честная логика** - подсказка и разбор опираются на состояние поля.
- **Доступность** - базовая игра и пазлы доступны без подписки; язык интерфейса выбирается в настройках.
- **Развитие навыка** - пазлы помогают замечать типовые конфигурации, а не только набирать скорость клика.

## Установка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/1nqi/Minesweeper.git
cd Minesweeper
```

2. Создайте виртуальное окружение и активируйте его:

```bash
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows
```

3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` в корне проекта (см. [полный список переменных](#переменные-окружения-env); для быстрого старта скопируйте `.env.example` в `.env` и откорректируйте значения).

5. Примените миграции:

```bash
python manage.py migrate
```

6. (Опционально) Создайте суперпользователя:

```bash
python manage.py createsuperuser
```

7. Запустите сервер разработки:

```bash
python manage.py runserver
```

## Использование

После запуска откройте в браузере **http://127.0.0.1:8000/** (или тот URL, который вы настроили в `ALLOWED_HOSTS`). Регистрация и вход - через форму или Google, если заданы `GOOGLE_OAUTH_CLIENT_ID` и `GOOGLE_OAUTH_SECRET` (иначе кнопки Google скрыты).

## Настройка Google OAuth (вход через Google)

1. В [Google Cloud Console](https://console.cloud.google.com/) создайте проект (или выберите существующий).
2. Включите API **Google+ API** не обязателен для базового OAuth; достаточно экрана согласия OAuth и учётных данных.
3. **Экран согласия OAuth** (OAuth consent screen): тип *External* для теста, добавьте тестовых пользователей при статусе *Testing*.
4. **Учётные данные** → *Create credentials* → **OAuth client ID** → тип **Web application**:
   - **Authorized JavaScript origins** (примеры):
     - `http://127.0.0.1:8000`
     - `http://localhost:8000`
     - `https://ваш-публичный-домен` (продакшен)
   - **Authorized redirect URIs** (обязательно точное совпадение пути allauth):
     - `http://127.0.0.1:8000/accounts/google/login/callback/`
     - `http://localhost:8000/accounts/google/login/callback/`
     - `https://ваш-домен/accounts/google/login/callback/`
5. Скопируйте **Client ID** и **Client secret** в `.env`: `GOOGLE_OAUTH_CLIENT_ID` и `GOOGLE_OAUTH_SECRET`.
6. В админке Django (**Sites** → сайт с `SITE_ID=1`) укажите **доменное имя** вашего сайта (для продакшена — публичный хост без `https://`). Это важно для корректных ссылок в письмах и части сценариев allauth.

Если пользователь уже зарегистрировался по паролю с тем же email, что у Google, соцаккаунт **привяжется к существующей учётной записи** (кастомный `SocialAccountAdapter` в `accounts/adapters.py`), вместо ошибки «email занят».

## Функционал

- **Аутентификация:** регистрация, вход, выход; вход через Google (при настройке OAuth)
- **Игра:** классический сапёр, режимы (в т.ч. ежедневный вызов), сложность, своя сетка, темы доски Classic, Ocean доступны бесплатно, остальная часть тем - с подпиской Pro
- **ИИ-подсказка в игре:** подсветка безопасной клетки и короткий текст от Gemini (лимит до 3 использований в день для Free trial)
- **Пазлы:** уровни с логически одним ходом; ИИ-разбор после ошибки (дневной лимит для бесплатных, безлимит для Pro)
- **Рекорды и профили:** сохранение результатов, лидерборды, аватар, язык интерфейса
- **Pro:** Stripe Checkout, вебхуки, тестовая кнопка активации в dev при `PRO_TEST_BUTTON=True`
- **Локализация:** ru / en / kk; сборка сообщений: `django-admin compilemessages`
- **ВАЖНО:** для теста можно получить статус Pro совершенно бесплатно - зайдя в нажав на кнопку "Upgrade to Pro" в левом баре, пролистав ниже и нажав на кнопку "[Test] Activate Pro for free"

## Зависимости

Основные пакеты задаются в `requirements.txt`, в том числе:

- **Django** (5.x, см. файл)
- **django-allauth** - учётные записи и Google
- **Pillow** - изображения (аватары и т.п.)
- **python-dotenv** - загрузка `.env`
- **stripe** - подписка Pro
- **google-generativeai** - Gemini для текстов подсказок и разборов
- **gunicorn**, **whitenoise**, **psycopg2-binary**, **dj-database-url** - продакшен-сервер, статика и PostgreSQL (в т.ч. Railway)
- **requests**, **PyJWT**, **cryptography** - вспомогательные зависимости (OAuth и др.)


## Переменные окружения (.env)

Ниже - **все** переменные, которые читает `config/settings.py`. Пустые или пропущенные значения там, где допустимо, подменяются разумными значениями по умолчанию (см. код).

| Переменная | Назначение |
|------------|------------|
| `SECRET_KEY` | Секретный ключ Django (**обязателен для работы приложения в проде**). Альтернатива: **`DJANGO_SECRET_KEY`**. |
| `DEBUG` | `true` / `false` - режим отладки. |
| `ALLOWED_HOSTS` | Список хостов через **запятую** (например `localhost,127.0.0.1`). Если пусто при `DEBUG=true`, разрешены все. |
| `CSRF_TRUSTED_ORIGINS` | Доверенные origin для CSRF через **запятую** (нужно при HTTPS и кастомном домене). |
| `SITE_ID` | ID сайта в `django.contrib.sites` (часто `1`). |
| `LANGUAGE_CODE` | Язык по умолчанию, например `ru`. |
| `TIME_ZONE` | Часовой пояс, например `UTC`. |
| `DATABASE_URL` | Строка подключения PostgreSQL (**Railway** подставляет при подключении плагина БД). Если задана, используется вместо SQLite и вместо блока `USE_POSTGRES` / `POSTGRES_*`. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Если **`DATABASE_URL`** пуст, из этих переменных собирается URL PostgreSQL. Не смешивайте **два разных** набора: при непустом `DATABASE_URL` поля `DB_*` не используются. |
| `DATABASE_SSL_REQUIRE` | `true` / `false` — требовать SSL к Postgres (по умолчанию `true`, когда `DEBUG=false`). |
| `COPY_FROM_SQLITE_PATH` | Путь к файлу **старой** SQLite только для разовой команды **`python manage.py sqlite_to_postgres`**. Работает, если `default` — PostgreSQL. После переноса можно удалить. |
| `USE_POSTGRES` | `true` — PostgreSQL по отдельным переменным `POSTGRES_*` (если **нет** `DATABASE_URL`). |
| `SQLITE_PATH` | Путь к файлу SQLite относительно корня проекта или абсолютный (по умолчанию `db.sqlite3`). |
| `POSTGRES_DB` | Имя БД PostgreSQL. |
| `POSTGRES_USER` | Пользователь PostgreSQL. |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL. |
| `POSTGRES_HOST` | Хост БД (по умолчанию `localhost`). |
| `POSTGRES_PORT` | Порт БД (по умолчанию `5432`). |
| `GOOGLE_OAUTH_CLIENT_ID` | Client ID Google OAuth для allauth. |
| `GOOGLE_OAUTH_SECRET` | Client Secret Google OAuth. |
| `STRIPE_PUBLIC_KEY` | Публичный ключ Stripe (`pk_…`). |
| `STRIPE_SECRET_KEY` | Секретный ключ Stripe (`sk_…`). |
| `STRIPE_WEBHOOK_SECRET` | Секрет вебхука Stripe (`whsec_…`). |
| `STRIPE_PRICE_PRO` | Price ID месячной подписки (`price_…`); запасной вариант, если не задан месячный ниже. |
| `STRIPE_PRICE_PRO_MONTHLY` | Price ID **месячного** Pro (`price_…`). |
| `STRIPE_PRICE_PRO_YEARLY` | Price ID **годового** Pro (`price_…`). |
| `PRO_TEST_BUTTON` | `true` / `false` - показывать кнопку тестовой активации Pro в dev (по умолчанию как `DEBUG`). |
| `GEMINI_API_KEY` | Ключ API Google Gemini для текстовых подсказок и разборов. |
| `GEMINI_MODEL` | ID модели (по умолчанию `gemini-2.0-flash`). |
| `GEMINI_HINT_EXPLAIN` | `true` / `false` - включить вызовы Gemini для пояснений. |
| `RAILWAY_ENVIRONMENT` | Выставляется платформой Railway (например `production`); при этом по умолчанию **`DEBUG`** выключается, если явно не задан. |
| `SECURE_SSL_REDIRECT` | `true` / `false` — редирект HTTP→HTTPS (по умолчанию `true` при `DEBUG=false`). |
| `LOG_LEVEL` | Уровень лога root-логгера в проде (по умолчанию `INFO`). |
| `DJANGO_LOG_LEVEL` | Уровень логгера `django` в проде (по умолчанию `INFO`). |

Пример заготовки (значения замените на свои):

```env
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=
SITE_ID=1
LANGUAGE_CODE=ru
TIME_ZONE=UTC

# Railway задаёт DATABASE_URL при подключении PostgreSQL; локально можно закомментировать
# DATABASE_URL=postgres://user:pass@host:5432/dbname
DATABASE_SSL_REQUIRE=True

USE_POSTGRES=False
SQLITE_PATH=db.sqlite3
POSTGRES_DB=minesweeper
POSTGRES_USER=minesweeper
POSTGRES_PASSWORD=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_SECRET=

STRIPE_PUBLIC_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_PRO_MONTHLY=
STRIPE_PRICE_PRO=
STRIPE_PRICE_PRO_YEARLY=
PRO_TEST_BUTTON=True

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
GEMINI_HINT_EXPLAIN=True

SECURE_SSL_REDIRECT=True
LOG_LEVEL=INFO
DJANGO_LOG_LEVEL=INFO
```
