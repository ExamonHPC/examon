FROM python:3.12-slim

ARG EXAMON_COMMON_VERSION=v0.2.7
ARG EXAMON_CONTAINER_REPO=https://github.com/ExamonHPC/examon-container.git
ARG EXAMON_CONTAINER_VERSION=master

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "git+https://github.com/ExamonHPC/examon-common.git@${EXAMON_COMMON_VERSION}"

WORKDIR /app

RUN git clone --depth 1 --branch "${EXAMON_CONTAINER_VERSION}" \
        "${EXAMON_CONTAINER_REPO}" /tmp/examon-container \
    && cp /tmp/examon-container/examon_deploy/examon/subscribers/mqtt2kairosdb_queue/mqtt2kairosdb.py . \
    && cp /tmp/examon-container/examon_deploy/examon/subscribers/mqtt2kairosdb_queue/requirements.txt . \
    && rm -rf /tmp/examon-container/.git /tmp/examon-container

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "mqtt2kairosdb.py", "run"]
