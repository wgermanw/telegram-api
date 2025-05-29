#!/usr/bin/env python3
import os
import base64
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

def authorize_telegram():
    # Проверяем, что заданы API_ID и API_HASH
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        print("❌ Не заданы переменные окружения TELEGRAM_API_ID и/или TELEGRAM_API_HASH")
        return
    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ Переменная TELEGRAM_API_ID должна быть целым числом")
        return

    # Запрашиваем у пользователя номер телефона
    phone = input("Введите номер телефона (с префиксом, например +7 или +375): ")

    client = TelegramClient('session', api_id, api_hash)
    try:
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phone)
            code = input("Введите код из Telegram: ")
            try:
                client.sign_in(phone, code)
            except SessionPasswordNeededError:
                pwd = input("Введите пароль двухфакторной аутентификации: ")
                client.sign_in(password=pwd)

        # Читаем файл сессии и кодируем его в base64
        session_file = client.session.filename
        with open(session_file, "rb") as f:
            session_bytes = f.read()
        session_b64 = base64.b64encode(session_bytes).decode()

        print("\n🚀 Base64-строка сессии Telegram:")
        print(session_b64)
        print("\nСкопируйте её в переменную окружения TELEGRAM_SESSION в вашем Railway-проекте.")
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    print("🔐 Запуск авторизации Telegram для Railway")
    authorize_telegram()
