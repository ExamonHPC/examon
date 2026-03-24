FROM python:3.12-slim

ARG EXAMON_COMMON_VERSION=v0.2.7

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "git+https://github.com/ExamonHPC/examon-common.git@${EXAMON_COMMON_VERSION}"

WORKDIR /app

COPY publishers/random_pub/ .

CMD ["python", "random_pub.py", "run"]
