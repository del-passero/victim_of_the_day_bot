# 1. Официальный минимальный Python-образ
FROM python:3.10-slim

# 2. Рабочая директория приложения
WORKDIR /app

# 3. Копируем файлы проекта
COPY . .

# 4. Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# 5. Создаем папку /data, если ее нет (важно для локального запуска, на Amvera монтирование автоматом)
RUN mkdir -p /data

# 6. Переменная окружения для python (чтобы не писать .pyc)
ENV PYTHONDONTWRITEBYTECODE=1

# 7. Запуск бота
CMD ["python", "victim_bot.py"]
