FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY web/examon-server/requirements.txt .
RUN CASS_DRIVER_BUILD_CONCURRENCY=8 pip install --no-cache-dir -r requirements.txt

COPY web/examon-server/ .

EXPOSE 5000

CMD ["python", "server.py"]
