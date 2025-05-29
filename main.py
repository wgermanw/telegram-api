from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import subprocess
import json
import os
import sys
import base64
from telethon.sync import TelegramClient

# Создаем приложение FastAPI
app = FastAPI(
    title="Telegram API Bridge",
    description="Отправка сообщений в Telegram через API",
    version="1.0.0"
)

# Безопасность
security = HTTPBearer()

# Модель данных для запроса
class MessageRequest(BaseModel):
    user: str
    text: str

# Проверка API ключа
async def verify_api_key(credentials = Depends(security)):
    api_secret = os.getenv("API_SECRET", "default-secret-change-me")
    if credentials.credentials != api_secret:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials

def restore_telegram_session():
    """Восстанавливает сессию Telegram из переменной окружения"""
    session_data = os.getenv("TELEGRAM_SESSION")
    if session_data:
        try:
            # Декодируем base64 обратно в файл
            session_bytes = base64.b64decode(session_data)
            with open('session_name.session', 'wb') as f:
                f.write(session_bytes)
            return True
        except Exception as e:
            print(f"Error restoring session: {e}")
            return False
    return False

def create_telegram_worker():
    """Создает скрипт для работы с Telegram"""
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        return None
    
    # Восстанавливаем сессию перед каждым использованием
    restore_telegram_session()
    
    script_content = f'''
import sys
import json
import os

try:
    from telethon.sync import TelegramClient
    from telethon.errors import SessionPasswordNeededError
except ImportError as e:
    print(json.dumps({{"error": f"Telethon not installed: {{str(e)}}"}}))
    sys.exit(1)

api_id = {api_id}
api_hash = "{api_hash}"

def send_message(user, text):
    client = None
    try:
        client = TelegramClient('session_name', api_id, api_hash)
        client.connect()
        
        if not client.is_user_authorized():
            return {{"error": "Not authorized. Please authorize first."}}
        
        client.send_message(user, text)
        return {{"status": "success", "message": f"Message sent to {{user}}"}}
        
    except Exception as e:
        return {{"error": f"Send error: {{str(e)}}"}}
    finally:
        if client:
            try:
                client.disconnect()
            except:
                pass

def check_status():
    client = None
    try:
        client = TelegramClient('session_name', api_id, api_hash)
        client.connect()
        
        is_authorized = client.is_user_authorized()
        is_connected = client.is_connected()
        
        return {{
            "status": "ok",
            "authorized": is_authorized,
            "connected": is_connected,
            "session_exists": os.path.exists('session_name.session')
        }}
        
    except Exception as e:
        return {{"status": "error", "error": str(e)}}
    finally:
        if client:
            try:
                client.disconnect()
            except:
                pass

def main():
    if len(sys.argv) < 2:
        print(json.dumps({{"error": "No command specified"}}))
        return
    
    command = sys.argv[1]
    
    if command == "send":
        if len(sys.argv) < 4:
            print(json.dumps({{"error": "Usage: send <user> <text>"}}))
            return
        
        user = sys.argv[2]
        text = " ".join(sys.argv[3:])
        result = send_message(user, text)
        print(json.dumps(result))
        
    elif command == "status":
        result = check_status()
        print(json.dumps(result))
        
    else:
        print(json.dumps({{"error": f"Unknown command: {{command}}"}}))

if __name__ == "__main__":
    main()
'''
    
    script_path = 'telegram_worker.py'
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    return script_path

def run_telegram_command(command, *args):
    """Выполняет команду Telegram"""
    script_path = create_telegram_worker()
    
    if not script_path:
        return {'error': 'Missing TELEGRAM_API_ID or TELEGRAM_API_HASH environment variables'}
    
    try:
        cmd = [sys.executable, script_path, command] + list(args)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.getcwd(),
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            try:
                output = result.stdout.strip()
                if output:
                    return json.loads(output)
                else:
                    return {'error': 'No output from script'}
            except json.JSONDecodeError as e:
                return {'error': f'JSON decode error: {e}', 'raw_output': result.stdout}
        else:
            return {
                'error': f'Process failed with code {result.returncode}',
                'stderr': result.stderr,
                'stdout': result.stdout
            }
    
    except subprocess.TimeoutExpired:
        return {'error': 'Command timeout (60 seconds)'}
    except Exception as e:
        return {'error': f'Subprocess error: {str(e)}'}
    finally:
        try:
            if script_path and os.path.exists(script_path):
                os.remove(script_path)
        except:
            pass

# API Endpoints
@app.get("/")
async def root():
    """Главная страница"""
    return {
        "message": "Telegram API Bridge is running!",
        "docs": "/docs",
        "endpoints": ["/send_message", "/status", "/health", "/debug"]
    }

@app.get("/health")
async def health():
    """Проверка здоровья сервера (без авторизации)"""
    return {"status": "healthy", "service": "telegram-api"}

@app.get("/debug")
async def debug():
    """Временный endpoint для отладки - УДАЛИТЕ В ПРОДАКШЕНЕ!"""
    api_secret = os.getenv("API_SECRET")
    return {
        "api_secret_exists": bool(api_secret),
        "api_secret_length": len(api_secret) if api_secret else 0,
        "api_secret_first_3": api_secret[:3] + "..." if api_secret else None,
        "api_key_exists": bool(os.getenv("API_KEY")),
        "telegram_api_id_exists": bool(os.getenv("TELEGRAM_API_ID")),
        "telegram_api_hash_exists": bool(os.getenv("TELEGRAM_API_HASH")),
        "telegram_session_exists": bool(os.getenv("TELEGRAM_SESSION")),
        "all_env_vars": list(os.environ.keys())
    }

@app.get("/status")
async def status(credentials = Depends(verify_api_key)):
    """Статус Telegram подключения"""
    result = run_telegram_command('status')
    return result

@app.post("/send_message")
async def send_message(
    message: MessageRequest,
    credentials = Depends(verify_api_key)
):
    """Отправка сообщения в Telegram"""
    
    if not message.user or not message.text:
        raise HTTPException(status_code=400, detail="user and text are required")
    
    if len(message.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Empty message")
    
    try:
        result = run_telegram_command('send', message.user, message.text)
        
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        
        return {
            "status": "success",
            "message": f"Message sent to {message.user}",
            "text": message.text
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# Для Railway.app нужно указать порт
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    print(f"API_SECRET exists: {bool(os.getenv('API_SECRET'))}")
    uvicorn.run(app, host="0.0.0.0", port=port)
