import os
import sys
import json
import subprocess
import base64

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from telethon.sync import TelegramClient

# ————— Configuration —————
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
API_SECRET = os.getenv("API_SECRET")
TELEGRAM_SESSION_ENV = os.getenv("TELEGRAM_SESSION")

SESSION_NAME = "session"
SESSION_FILE = f"{SESSION_NAME}.session"

# ————— FastAPI setup —————
app = FastAPI(
    title="Telegram API Bridge",
    description="Send messages via Telegram",
    version="1.0.0"
)
security = HTTPBearer()


# ————— Models & Auth —————
class MessageRequest(BaseModel):
    user: str
    text: str


async def verify_api_key(credentials=Depends(security)):
    """
    Проверка HTTP Bearer токена (API_SECRET).
    """
    if not API_SECRET or credentials.credentials != API_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ————— Session management —————
def restore_telegram_session() -> bool:
    """
    Если задана TELEGRAM_SESSION (base64), раскодировать её в файл сессии.
    """
    if TELEGRAM_SESSION_ENV:
        try:
            data = base64.b64decode(TELEGRAM_SESSION_ENV)
            with open(SESSION_FILE, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            print(f"Error restoring Telegram session: {e}")
    return False


def create_telegram_worker() -> str | None:
    """
    Генерирует скрипт для взаимодействия с Telethon,
    возвращает путь к нему или None, если не заданы API_ID/API_HASH.
    """
    if not API_ID or not API_HASH:
        return None

    # Восстанавливаем сессию (если есть в переменной)
    restore_telegram_session()

    script = f'''import sys
import os
import json
from telethon.sync import TelegramClient

api_id = {API_ID}
api_hash = "{API_HASH}"
session_name = "{SESSION_NAME}"

def main():
    if len(sys.argv) < 2:
        print(json.dumps({{"error":"No command provided"}}))
        sys.exit(1)
    command = sys.argv[1]
    args = sys.argv[2:]
    client = TelegramClient(session_name, api_id, api_hash)
    try:
        client.connect()
        if command == "send":
            if len(args) < 2:
                print(json.dumps({{"error":"Missing arguments"}}))
                sys.exit(1)
            user, text = args[0], args[1]
            client.send_message(user, text)
            print(json.dumps({{"status":"success","message":"Message sent to " + user}}))
        elif command == "status":
            auth = client.is_user_authorized()
            conn = client.is_connected()
            exists = os.path.exists(session_name + ".session")
            print(json.dumps({{"status":"ok","authorized":auth,"connected":conn,"session_exists":exists}}))
        else:
            print(json.dumps({{"error":"Unknown command: " + command}}))
    except Exception as e:
        print(json.dumps({{"error":str(e)}}))
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
'''
    path = "telegram_worker.py"
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    return path


def run_telegram_command(command: str, *args: str) -> dict:
    """
    Запускает сгенерированный скрипт с указанной командой и аргументами.
    """
    worker = create_telegram_worker()
    if not worker:
        return {"error": "Missing TELEGRAM_API_ID or TELEGRAM_API_HASH"}

    try:
        cmd = [sys.executable, worker, command, *args]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            return {
                "error": f"Process failed ({proc.returncode})",
                "stderr": proc.stderr.strip(),
                "stdout": proc.stdout.strip()
            }
        try:
            return json.loads(proc.stdout.strip())
        except json.JSONDecodeError as e:
            return {"error": f"JSON decode error: {e}", "raw": proc.stdout}
    except Exception as e:
        return {"error": f"Exception running command: {e}"}


# ————— Endpoints —————
@app.get("/")
async def root():
    return {
        "message": "Telegram API Bridge is running!",
        "docs": "/docs",
        "endpoints": ["/send_message", "/status", "/health", "/debug"]
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "telegram-api"}


@app.get("/debug")
async def debug():
    return {
        "api_secret_exists": bool(API_SECRET),
        "telegram_api_id_exists": bool(API_ID),
        "telegram_api_hash_exists": bool(API_HASH),
        "telegram_session_env_exists": bool(TELEGRAM_SESSION_ENV),
        "session_file_exists": os.path.exists(SESSION_FILE)
    }


@app.get("/status")
async def status(credentials=Depends(verify_api_key)):
    """Проверяет, подключён ли TelegramClient."""
    return run_telegram_command("status")


@app.post("/send_message")
async def send_message(payload: MessageRequest, credentials=Depends(verify_api_key)):
    """Отправка сообщения в Telegram."""
    if not payload.user or not payload.text.strip():
        raise HTTPException(status_code=400, detail="user and text are required")
    result = run_telegram_command("send", payload.user, payload.text)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {
        "status": "success",
        "message": f"Message sent to {payload.user}",
        "text": payload.text
    }


# ————— Launch —————
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
