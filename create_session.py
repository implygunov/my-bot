from telethon import TelegramClient, events
from telethon.sessions import SQLiteSession  # Изменено на SQLiteSession
from telethon.network import ConnectionTcpFull
import socks
import os

# ====== НАСТРОЙКИ ====== #
API_ID =
API_HASH = ""
PHONE = ""
SESSION_FILE = "BRPIZZA.session"  # Имя файла сессии

# Настройки прокси
PROXY = (socks.SOCKS5, '46.146.210.123', 1080)  # Ваш прокси

# ====== КЛИЕНТ ====== #
client = TelegramClient(
    session=SQLiteSession(SESSION_FILE),  # Используем SQLiteSession
    api_id=API_ID,
    api_hash=API_HASH,
    proxy=PROXY,
    connection=ConnectionTcpFull,
    device_model="iPhone 12 Pro",
    system_version="16.5.4",
    app_version="10.12.0",
    lang_code="en",
    system_lang_code="en-US",
)


async def main():
    print("🔒 Подключение к Telegram...")

    try:
        await client.connect()

        if not await client.is_user_authorized():
            print("🔑 Авторизация...")
            await client.send_code_request(PHONE)
            code = input("✉️ Введите код из Telegram: ")
            await client.sign_in(PHONE, code)

        me = await client.get_me()
        print(f"✅ Вход выполнен как: {me.first_name}")
        print(f"📌 Сессия сохранена в файл: {SESSION_FILE}")

        @client.on(events.NewMessage(incoming=True))
        async def handler(event):
            print(f"💬 Новое сообщение: {event.message.text}")

        print("👂 Слушаем сообщения...")
        await client.run_until_disconnected()

    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())