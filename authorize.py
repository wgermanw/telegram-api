from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import base64
import os

API_ID = int(os.environ.get("TELEGRAM_API_ID"))
API_HASH = os.environ.get("TELEGRAM_API_HASH")

def authorize_telegram():
    phone = input("Введите номер телефона (с +7 или +375): ")
    client = TelegramClient('session', API_ID, API_HASH)
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
        session_bytes = open(client.session.filename, 'rb').read()
        print("\nBase64-строка сессии, скопируйте её в SECRET_TELEGRAM_SESSION:\n")
        print(base64.b64encode(session_bytes).decode())
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    print("🚀 Авторизация Telegram для Railway.app")
    authorize_telegram()
