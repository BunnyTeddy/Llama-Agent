FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run in direct mode via HTTP server for cloud deployment
EXPOSE 8080

CMD ["python", "main.py", "--help"]
