# Телеграмм бот для поставщика Wildberries

Бот позволяет:

- Работать с поставками: создавать, закрывать (отгружать), редактировать, удалять
- Проверять новые заказы, добавлять их к поставкам
- Создавать стикеры для маркировки заказов. Бот автоматически создает штрих-коды для товаров, объединяет их с QR-кодами
  поставок в один pdf-файл.

### Необходимо установить следующие переменные окружения

- **TG_TOKEN** - токен телеграмм бота, полученный от [BotFather](https://t.me/BotFather)
- **WB_API_KEY** - API ключ Wildberries

## Как запустить

- Python3.10 должен быть уже установлен.

- Создайте виртуальное окружение командой `python3 -m venv venv`

- Активируйте его. На windows командой `venv\scripts\activate`\
  На linux - `source venv/bin/activate`

- Используйте `pip` для установки необходимых компонентов:`pip install -r requirements.txt`

- Запустите бота командой `python3 manage.py start_bot`