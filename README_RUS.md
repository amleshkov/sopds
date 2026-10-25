#### SimpleOPDS Catalog - Простой OPDS Каталог
#### Автор: Dmitry V.Shelepnev
#### Модернизированный форк: Python 3.12, Django 5.2 LTS

OPDS-сервер каталога домашней библиотеки: сканирует каталог с книгами
(россыпью и в zip-архивах, поддержка INPX-коллекций), отдает каталог через
OPDS-фиды и веб-интерфейс, выполняет регулярное пересканирование.

- Стек: Python 3.12, Django 5.2 LTS, PostgreSQL (или sqlite3), gunicorn, WhiteNoise
- Качество: 117 юнит-тестов, docker e2e в CI (скан, API, web, побайтовая сверка скачиваний), ruff-clean, гейт покрытия
- Удалено относительно оригинальной версии 0.47: Telegram-бот, конвертеры fb2 в epub/mobi, вендорная django-constance, вендорный форк zipfile

[English instructions: README.md](README.md)

#### 1. Быстрый старт (без docker)

1.1 Получите код и соберите окружение (требуется [uv](https://docs.astral.sh/uv/)):

    git clone <этот репозиторий> sopds
    cd sopds
    uv sync

1.2 Задайте переменные окружения (полный список в разделе 2). Минимум:

    export SOPDS_SECRET_KEY="$(openssl rand -base64 50)"
    export SOPDS_ALLOWED_HOSTS="localhost,ваш-хост"
    export SOPDS_DEBUG=True

При `SOPDS_DEBUG=True` включается девелоперская раздача статики;
для продакшена используйте gunicorn + WhiteNoise (systemd/docker ниже делают это сами).

1.3 Инициализируйте базу (по умолчанию sqlite3; PostgreSQL — через `SOPDS_DB_HOST`):

    uv run manage.py migrate
    uv run manage.py loaddata genre.json
    uv run manage.py createsuperuser

1.4 Укажите путь к библиотеке и просканируйте ее:

    uv run manage.py sopds_util setconf SOPDS_ROOT_LIB /путь/к/книгам
    uv run manage.py sopds_scanner scan

1.5 Запустите сервер (gunicorn, в foreground-режиме):

    uv run manage.py sopds_server start --host 0.0.0.0 --port 8001

Доступ:

>     OPDS-фид:  http://localhost:8001/opds/
>     Веб-морда: http://localhost:8001/web/
>     Админка:   http://localhost:8001/admin/

Включите аутентификацию (настройка `SOPDS_AUTH`), чтобы доступ к каталогу
требовал логина (web) и HTTP Basic auth (OPDS).

#### 2. Переменные окружения

    SOPDS_SECRET_KEY      обязательна, секретный ключ Django
    SOPDS_DEBUG           True/False, по умолчанию False
    SOPDS_ALLOWED_HOSTS   список разрешенных хостов через запятую
    SOPDS_DB_HOST         хост PostgreSQL; если задан, используется PostgreSQL вместо sqlite3
    SOPDS_DB_NAME         имя базы PostgreSQL (по умолчанию: sopds)
    SOPDS_DB_USER         пользователь PostgreSQL (по умолчанию: sopds)
    SOPDS_DB_PASSWORD     пароль PostgreSQL (по умолчанию: sopds)
    SOPDS_DB_PORT         порт PostgreSQL (по умолчанию: 5432)
    SOPDS_STATIC_ROOT     каталог вывода collectstatic (по умолчанию: <проект>/staticroot)
    SOPDS_WEB_WORKERS     число воркеров gunicorn (по умолчанию: 2)

Остальные настройки хранятся в базе (django-constance) и меняются через
интерфейс администратора (`/admin/`) или `manage.py sopds_util setconf` — см. раздел 5.

#### 3. Docker

    python scripts/make_testbooks.py testdata     # необязательная демо-библиотека
    docker compose up -d --build

Сервисы: `postgres` (16), `sopds-server` (gunicorn, порт 8001),
`sopds-scanner` (сканирование по расписанию). Каталог с книгами монтируется в `/data`
(переменная `SOPDS_LIB_DIR` указывает на вашу коллекцию).

Разовое сканирование:

    docker compose run --rm sopds-scanner scanner scan

#### 4. Запуск под systemd

`sopds_server start` запускает gunicorn в foreground-режиме — управлением процессом
занимается systemd (или docker). Готовые юнит-файлы для эталонного layout
(проект в `/opt/sopds/sopds`, uv-окружение в `/opt/sopds/sopds/.venv`, переменные в
`/opt/sopds/sopds-env.sh`) лежат в `deploy/`:

    cp deploy/*.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable --now sopds.service sopds-scanner.service

Юниты выполняют `migrate` и `collectstatic` перед стартом и перезапускаются при сбоях.

#### 5. Настройки каталога (django-constance)

Настройки хранятся в базе и меняются через `/admin/` или:

    python manage.py sopds_util setconf КЛЮЧ ЗНАЧЕНИЕ
    python manage.py sopds_util getconf [КЛЮЧ]

Основные настройки:

**SOPDS_ROOT_LIB** - абсолютный путь к каталогу с книгами.
**SOPDS_AUTH** - требовать аутентификацию для OPDS/web (по умолчанию True).
**SOPDS_LANGUAGE** - язык интерфейса, ru-RU или en-US.
**SOPDS_BOOK_EXTENSIONS** - обрабатываемые расширения файлов книг (по умолчанию ".pdf .djvu .fb2 .epub .mobi").
**SOPDS_MAXITEMS** - элементов на страницу (по умолчанию 60).
**SOPDS_DOUBLES_HIDE** - скрывать дубликаты книг в выдачах (по умолчанию True).
**SOPDS_ZIPSCAN** - сканировать книги внутри zip-архивов (по умолчанию True).
**SOPDS_ZIPCODEPAGE** - кодировка имен файлов внутри zip-архивов (по умолчанию cp866).
**SOPDS_INPX_ENABLE** - читать метаданные из .inpx-коллекций (по умолчанию False).
**SOPDS_DELETE_LOGICAL** - помечать пропавшие книги недоступными вместо удаления записей (по умолчанию False).
**SOPDS_SCAN_SHED_MIN/HOUR/DAY/DOW** - cron-расписание сканера.
**SOPDS_SCAN_START_DIRECTLY** - установите True, чтобы запустить внеплановое сканирование при следующей проверке планировщика.
**SOPDS_CACHE_TIME** - время кэширования обложек в секундах (по умолчанию 1200).
**SOPDS_TITLE_AS_FILENAME** - строить имена скачиваемых файлов из названий книг (по умолчанию True).

#### 6. Консольные команды

    python manage.py sopds_scanner scan              # одно полное сканирование
    python manage.py sopds_scanner start             # сканирование по расписанию
    python manage.py sopds_util info                 # статистика коллекции
    python manage.py sopds_util clear [--nogenres]   # очистить каталог (по умолчанию перезагружает жанры)
    python manage.py sopds_util save_mygenres        # сохранить текущие жанры в fixtures
    python manage.py sopds_util load_mygenres        # загрузить жанры из fixtures
    python manage.py sopds_util pg_optimize          # оптимизация таблиц PostgreSQL

#### 7. Обновление с оригинальной версии SimpleOPDS 0.47-devel

Обновление переводит проект на Python 3.12 и Django 5.2 LTS. Данные базы (книги, авторы,
настройки, измененные через веб-интерфейс администратора) сохраняются.

7.1 Остановите работающие сервисы:

    python3 manage.py sopds_server stop
    python3 manage.py sopds_scanner stop

Если использовался Telegram-бот (`sopds_telebot`), остановите и удалите его сервис — бот
и конвертеры fb2 в epub/mobi больше не входят в состав проекта.

7.2 Сделайте резервную копию базы данных (обязательно):

    pg_dump -U sopds sopds > sopds_backup.sql        # PostgreSQL
    cp db.sqlite3 db.sqlite3.bak                     # sqlite3

7.3 Обновите код проекта (git pull или замените каталог).

7.4 Соберите новое окружение Python 3.12 с помощью uv
(старое окружение Python 3.9 несовместимо):

    uv sync

7.5 Настройте приложение через переменные окружения (ранее параметры БД правились
напрямую в файле sopds/settings.py):

    SOPDS_SECRET_KEY=<сгенерируйте: openssl rand -base64 50>   # обязательна
    SOPDS_DB_HOST=<хост> SOPDS_DB_NAME=sopds SOPDS_DB_USER=sopds SOPDS_DB_PASSWORD=...   # только для PostgreSQL
    SOPDS_ALLOWED_HOSTS=<список хостов через запятую>
    SOPDS_DEBUG=True|False

Для systemd-установок добавьте эти переменные в EnvironmentFile (например /opt/sopds/sopds-env.sh).

7.6 Подготовьте и выполните миграции. Старая таблица настроек вендорной версии constance требует
однократного запуска вспомогательного скрипта перед миграциями Django (поддерживаются PostgreSQL и sqlite3):

    uv run python scripts/migrate_constance_legacy.py
    uv run manage.py migrate

Все настройки, измененные через интерфейс администратора, переносятся автоматически.

7.7 Запустите сервисы и проверьте:

    uv run manage.py sopds_server start
    uv run manage.py sopds_scanner start

    curl http://localhost:8001/opds/

#### 8. Разработка

    uv sync                                        # включая dev-группу
    uv run manage.py test                          # юнит-тесты
    uv run coverage run manage.py test && uv run coverage report   # покрытие (гейт: 72%)
    uv run ruff check .                            # линтер
    docker compose up -d --build && docker compose run --rm sopds-scanner scanner scan   # e2e локально

CI (GitHub Actions): линтер (ruff), юнит-тесты с гейтом покрытия,
docker e2e (сгенерированная демо-библиотека, скан, проверки OPDS/web, побайтовая сверка скачиваний).
