FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT 8000

EXPOSE 8000

# تشغيل السيرفر + البوت (main.py) معاً
CMD ["sh", "-c", "python server.py & python main.py"]
