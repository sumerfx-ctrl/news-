FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT 8000

EXPOSE 8000

# تشغيل السيرفر + البوت معاً في نفس الحاوية (يمكن تعديل لاحقًا)
CMD ["sh", "-c", "python server.py & python bot.py"]
