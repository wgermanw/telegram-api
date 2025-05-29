FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и ставим пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --timeout=300 -r requirements.txt

# Копируем весь код приложения
COPY . .

# Документируем порт (у Railway в любом случае проксируется $PORT)
EXPOSE 8000

# Запускаем приложение, подставляя порт из окружения Railway
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
