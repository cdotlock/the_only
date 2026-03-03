FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .

RUN mkdir -p /app/data
ENV RELAY_DB_PATH=/app/data/mycelium.db

EXPOSE 8470
CMD ["python", "server.py"]
