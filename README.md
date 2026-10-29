# Luvvix — учёт ТМЦ (Kivy + FastAPI + SQLAlchemy)

Мобильное приложение на **Kivy** для ведения справочника товарно-материальных ценностей.
Все действия выполняются через **REST API на FastAPI**, данные хранятся в БД через **SQLAlchemy ORM**.

```
luvvix/
├── backend/                     # Сервер (FastAPI)
│   ├── app/
│   │   ├── main.py              # приложение, middleware, обработчики ошибок, Swagger
│   │   ├── core/                # config, security (JWT/bcrypt), errors, email, middleware
│   │   ├── db/                  # DeclarativeBase, Session, transaction (commit/rollback), init_db
│   │   ├── models/              # ORM-модели (Mapped, mapped_column, ForeignKey, relationship)
│   │   ├── schemas/             # Pydantic-схемы запросов/ответов
│   │   ├── repositories/        # доступ к данным (select через ORM)
│   │   ├── services/            # бизнес-логика (не знает про HTTP)
│   │   └── api/                 # роутеры, зависимости, проверка прав
│   ├── tests/test_api.py        # 12 автотестов API
│   ├── requirements.txt
│   └── .env.example
└── mobile/                      # Клиент (Kivy, MVVM)
    ├── main.py                  # App, навигация, сборка слоёв
    ├── buildozer.spec           # сборка APK
    └── app/
        ├── services/            # api_client.py (единственная точка связи с API), runner, session_store
        ├── viewmodels/          # состояние и логика экранов
        └── views/               # экраны (screens.py) и разметка (kv/*.kv)
```

## Запуск

### 1. Сервер
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows   (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Linux/macOS: cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
* Swagger: http://localhost:8000/docs, ReDoc: http://localhost:8000/redoc
* При первом запуске создаются таблицы, роли, права, категории и администратор
  **admin / Admin12345!**
* Если SMTP в `.env` не заполнен, **код 2FA печатается в консоли сервера** (`[DEV EMAIL]`).
  Чтобы коды приходили на почту — заполните `SMTP_*` (для Gmail/Яндекса нужен «пароль приложения»).

Тесты: `cd backend && pytest -q`

### 2. Клиент на компьютере
```bash
cd mobile
pip install kivy==2.3.1
python main.py
```
Адрес сервера меняется кнопкой «Сервер: …» на экране входа.

### 3. APK для Android
Собирается на Linux или в WSL (Windows):
```bash
pip install buildozer cython
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses-dev libffi-dev libssl-dev
cd mobile
buildozer -v android debug       # первый раз долго: скачивает SDK/NDK
# готовый файл: mobile/bin/luvvix-1.0-arm64-v8a_armeabi-v7a-debug.apk
```
На телефоне в «Сервер» укажите `http://<IP компьютера>:8000` (телефон и ПК в одной Wi-Fi сети,
сервер запущен с `--host 0.0.0.0`). Для эмулятора — `http://10.0.2.2:8000`.

## Соответствие требованиям

### UI (Kivy)
| Требование | Где |
|---|---|
| Экран авторизации | `LoginScreen` + экран кода `CodeScreen` (2FA) |
| Экран регистрации | `RegisterScreen` (клиентская валидация + ошибки сервера) |
| Главный экран | `HomeScreen` — ФИО, роль, пункты меню по правам |
| Навигация | `Navigator` в `main.py`: стек экранов, «‹ Назад», аппаратная кнопка Android |
| Список данных | `ItemsScreen` — RecycleView, пагинация «Загрузить ещё» |
| Просмотр записи | `ItemDetailScreen` + история изменений |
| Создание / редактирование | `ItemFormScreen` (режимы create/edit, PATCH только изменённых полей) |
| Удаление с подтверждением | `ConfirmPopup` → `DELETE /items/{id}` |
| Поиск и фильтрация | поиск (с задержкой 0.5 с), фильтр по категории, сортировка |
| Кнопка выхода | в верхней панели и на главном экране (с подтверждением) |
| Всё через API | `app/services/api_client.py`; клиент не обращается к БД |

### API (FastAPI)
Префикс `/api/v1`. Все ответы — JSON, ошибки — `{"detail", "code", "errors?"}`.

| Метод | Путь | Назначение | Право |
|---|---|---|---|
| GET | `/items` | список (search, category_id, responsible_id, sort, order, skip, limit) | items:read |
| GET | `/items/{id}` | одна запись | items:read |
| POST | `/items` | создание | items:create |
| PATCH | `/items/{id}` | частичное изменение | items:update / items:update_fact |
| DELETE | `/items/{id}` | удаление (204) | items:delete |
| GET | `/items/{id}/history` | журнал изменений | history:read |
| GET/POST | `/categories` | категории | items:read / categories:manage |
| POST | `/auth/register`, `/auth/login`, `/auth/verify`, `/auth/resend` | регистрация, вход, 2FA | — |
| POST | `/auth/refresh`, `/auth/logout`, `/auth/logout-all` | токены и выход | — |
| GET | `/auth/me` | текущий пользователь | авторизация |
| POST | `/auth/token` | OAuth2 password grant (кнопка Authorize в Swagger) | — |
| GET/PATCH | `/users`, `/users/{id}` | пользователи, смена роли, блокировка | users:manage |
| GET | `/users/short`, `/roles` | справочники | users:read |

Коды ошибок: **400** (валидация, неверные ссылки, недопустимая сортировка), **401** (нет/истёк токен,
неверный пароль или код), **403** (нет прав), **404**, **409** (дубликат инв. номера/логина),
**423** (блокировка после 5 неверных паролей), **429** (rate limit), **500** (JSON с id запроса).

### БД / ORM
`DeclarativeBase` (`db/base.py`), `Mapped` + `mapped_column` во всех моделях, `ForeignKey`
(items→categories/users, users→roles, токены→users), `relationship` (в т.ч. многие-ко-многим
Role↔Permission), `Session` через `Depends(get_db)`, `select()` в репозиториях,
`commit`/`rollback` в `db/uow.py → transaction()`. Прямого SQL в логике нет.

Таблицы: `users`, `roles`, `permissions`, `role_permissions`, `inventory_items`, `categories`,
`item_history`, `refresh_tokens`, `verification_codes`.

### Архитектура
* **Сервер** — слои: роутеры (HTTP) → сервисы (бизнес-логика, доменные исключения) →
  репозитории (ORM) → модели. Сервисы не знают про HTTP: исключения `NotFoundError` и т.п.
  превращаются в коды ответов в `main.py`. Отправка почты — отдельный адаптер (`core/email.py`).
* **Клиент** — MVVM (как в Software Architecture Document): View (`views/`) только отображает
  и передаёт действия; ViewModel (`viewmodels/`) хранит состояние (busy, error, данные) и логику;
  Model — `ApiClient`. Запросы выполняются в фоновом потоке, UI не зависает.

### Безопасность
* **OAuth2**: схема `OAuth2PasswordBearer` со **scopes = права**, эндпоинт `/auth/token`
  (password grant), Bearer-токены. Права проверяются по БД на каждом запросе — смена роли
  действует сразу.
* **2FA по почте**: после пароля на email отправляется 6-значный код (5 мин, не более 5 попыток,
  в БД хранится только хэш). Регистрация тоже подтверждается кодом.
* **Ролевая модель**: 4 роли × 9 прав (таблицы roles/permissions/role_permissions) + права
  на уровне полей: кладовщик (`items:update_fact`) может менять только количество, место, описание.

  | Роль | Права |
  |---|---|
  | Администратор | все, включая управление пользователями |
  | Бухгалтер | ТМЦ: чтение, создание, изменение, удаление; категории; история |
  | Кладовщик | чтение; изменение фактических данных; история |
  | Руководитель | только чтение и история |
* **Refresh token**: access JWT живёт 15 минут, refresh — 7 дней, одноразовый (ротация).
  Повторное использование старого refresh-токена = кража → отзывается вся цепочка сессии.
  Выход и блокировка пользователем отзывают токены. Клиент обновляет токен автоматически.
* **Защита инфраструктуры**: bcrypt для паролей, блокировка учётной записи после 5 неверных
  паролей, rate limit на `/auth/*`, одинаковое время ответа для существующего/несуществующего
  логина, заголовки безопасности (CSP, X-Frame-Options, nosniff, no-store), лимит размера
  запроса, TrustedHost, CORS, X-Request-ID в логах, ошибки 500 без утечки трейсбека.
  Для продакшена: HTTPS через nginx + `ALLOWED_HOSTS` и длинный `SECRET_KEY`.

## Сценарий демонстрации
1. Запустить сервер, открыть `/docs` — показать схемы и коды ошибок.
2. В приложении: «Зарегистрироваться» → код из письма/консоли → главный экран (роль Кладовщик).
3. Выйти, войти как **admin** → «Пользователи и роли» → назначить новому пользователю «Бухгалтер».
4. «Справочник ТМЦ» → «+» → создать запись → карточка → «Изменить» → «Удалить» (подтверждение).
5. Поиск, фильтр по категории, сортировка.
6. Войти кладовщиком — нет кнопок «Добавить»/«Удалить», в форме доступны только 3 поля.
