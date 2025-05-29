#!/usr/bin/env python3
"""
Скрипт для локальной авторизации Telegram
Запустите ОДИН РАЗ на своем ПК, потом загрузите сессию на Railway
"""

from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import base64
import os

# Ваши данные API
api_id = 18575080
api_hash = 'e64524fb2aeb97f4bc2b33d0a4a89ef0'

def authorize_telegram():
    """Авторизация и сохранение сессии"""
    print("🔐 Локальная авторизация Telegram...")
    
    client = TelegramClient('session_name', api_id, api_hash)
    
    try:
        client.connect()
        
        if not client.is_user_authorized():
            phone = input("📱 Введите номер телефона (например, +79991112233): ")
            client.send_code_request(phone)
            
            try:
                code = input("💬 Введите код из Telegram: ")
                client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("🔒 Введите пароль двухфакторной аутентификации: ")
                client.sign_in(password=password)
        
        print("✅ Авторизация успешна!")
        
        # Проверяем что сессия создана
        if os.path.exists('session_name.session'):
            print(f"✅ Файл сессии создан: {os.path.getsize('session_name.session')} байт")
            
            # Кодируем сессию в base64 для переменной окружения
            with open('session_name.session', 'rb') as f:
                session_data = f.read()
                session_b64 = base64.b64encode(session_data).decode()
                
            print("\n" + "="*50)
            print("📋 СКОПИРУЙТЕ ЭТУ СТРОКУ В RAILWAY.APP:")
            print("Переменная: TELEGRAM_SESSION")
            print("Значение:")
            print(session_b64)
            print("="*50)
            
            # Сохраняем в файл для удобства
            with open('session_base64.txt', 'w') as f:
                f.write(session_b64)
            print("💾 Также сохранено в файл: session_base64.txt")
            
        else:
            print("❌ Ошибка: файл сессии не создан")
            
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    print("🚀 Авторизация Telegram для Railway.app")
    print("1. Запустите этот скрипт")
    print("2. Введите номер телефона и код")  
    print("3. Скопируйте base64 строку в Railway")
    print()
    
    authorize_telegram()
