FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Entrypoint เพื่อ log PORT และรัน uvicorn (ถ้า crash จะเห็นใน Cloud Run logs)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Cloud Run ส่ง PORT ผ่าน env (default 8080)
ENV PORT=8080
EXPOSE 8080
CMD ["/entrypoint.sh"]
