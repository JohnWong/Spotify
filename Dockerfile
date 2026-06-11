FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080

# 1 worker is sufficient — Cloud Scheduler fires one request at a time.
# Timeout is 600 s (10 min) to cover the full Billboard sync.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "600", "main:app"]
