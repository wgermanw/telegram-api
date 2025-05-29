FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --timeout=300 -r requirements.txt

# Копируем код приложения
COPY . .

# Открываем порт
EXPOSE $PORT

# Запускаем приложение
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
