# Telegram AI Image Processing Bots

Этот репозиторий содержит два Telegram-бота на базе **aiogram 3.x**:

- `bot_main` — основной бот, обрабатывающий изображения через внешний AI API и предоставляющий платёжное меню (ЮKassa, CloudPayments, CryptoBot) с вебхуками на FastAPI.
- `bot_stars` — отдельный бот для приёма платежей в Telegram Stars, использующий общую базу данных с основным ботом.

## Возможности

- Приём и обработка фотографий через внешний AI API.
- Учёт лимитов генераций, премиум-статуса и пополнений.
- Обработка платежей через ЮKassa, CloudPayments, CryptoBot (USDT/TON) и отдельный бот для Telegram Stars.
- FastAPI вебхуки для подтверждения платежей и обновления базы данных.
- Админ-панель с командами `/stats`, `/broadcast`, управлением лимитами и премиум-статусом.
- Рассылка сообщений всем пользователям с прогрессом.
- Отдельный Stars-бот в режиме polling для минимизации рисков блокировки основного бота.

## Структура проекта

```
.
├── bot_main/
│   ├── main.py                # Точка входа основного бота
│   ├── config.py              # Загрузка настроек
│   ├── handlers/              # Хендлеры пользователей, админки и оплаты
│   ├── services/              # Работа с AI API и платёжными провайдерами
│   ├── database/              # Модели и CRUD для PostgreSQL
│   ├── middlewares/           # Throttling middleware
│   ├── keyboards/             # Инлайн-клавиатуры
│   └── webhook.py             # FastAPI приложение для вебхуков
├── bot_stars/                 # Минимальный бот для Telegram Stars
│   ├── main.py
│   ├── config.py
│   └── handlers/
├── requirements.txt
└── README.md
```

## Быстрый старт

1. **Создайте и заполните `.env`** согласно примеру из задания:

   ```env
   MAIN_BOT_TOKEN=...
   STARS_BOT_TOKEN=...
   AI_API_URL=...
   AI_API_KEY=...
   ADMIN_IDS=123456789
   YOOKASSA_SHOP_ID=...
   YOOKASSA_SECRET_KEY=...
   CLOUDPAYMENTS_PUBLIC_ID=...
   CLOUDPAYMENTS_API_SECRET=...
   CRYPTOBOT_API_TOKEN=...
   DATABASE_URL=postgresql+asyncpg://botuser:password@localhost:5432/botdb
   WEBHOOK_BASE_URL=https://your-domain.com
   WEBHOOK_SECRET=super_secret
   ```

2. **Установите зависимости** и выполните миграции базы данных:

   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt

   python -c "from bot_main.database.models import Base; from bot_main.database.session import engine; import asyncio; asyncio.run(Base.metadata.create_all(engine))"
   ```

3. **Запустите основного бота и вебхуки** (например, через systemd или напрямую):

   ```bash
   python bot_main/main.py
   ```

4. **Запустите Stars-бота** в отдельном процессе:

   ```bash
   python bot_stars/main.py
   ```

5. **Настройте вебхуки** платёжных систем на URL основного FastAPI приложения (`/yookassa_webhook`, `/cloudpayments_webhook`, `/cryptobot_webhook`).

## Дополнительно

- Основной бот работает в режиме webhook: Telegram отправляет обновления на FastAPI маршрут `/telegram-webhook`, а отдельные платёжные вебхуки обслуживаются на порту `8000`.
- Stars-бот запускается отдельно, не содержит обработчиков контента и взаимодействует с той же БД.
- Перед деплоем настройте логи, мониторинг и автоматический рестарт сервисов.

## Лицензия

Проект распространяется под лицензией MIT. Используйте и модифицируйте на своё усмотрение.
