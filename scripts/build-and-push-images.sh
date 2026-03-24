#!/usr/bin/env bash
set -euo pipefail

REGISTRY="${1:-examon-registry:5111}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Building and pushing ExaMon images to ${REGISTRY}"

echo "--- Building mosquitto ---"
docker build -t "${REGISTRY}/examon/mosquitto:latest" \
  -f "${REPO_ROOT}/deploy/docker/mosquitto/Dockerfile" \
  "${REPO_ROOT}/deploy/docker/mosquitto/"

echo "--- Building kairosdb ---"
docker build -t "${REGISTRY}/examon/kairosdb:1.3.0" \
  -f "${REPO_ROOT}/deploy/docker/kairosdb/Dockerfile" \
  "${REPO_ROOT}/deploy/docker/kairosdb/"

echo "--- Building mqtt2kairosdb ---"
docker build -t "${REGISTRY}/examon/mqtt2kairosdb:latest" \
  -f "${REPO_ROOT}/deploy/docker/mqtt2kairosdb/Dockerfile" \
  "${REPO_ROOT}/deploy/docker/mqtt2kairosdb/"

echo "--- Building random-pub ---"
docker build -t "${REGISTRY}/examon/random-pub:latest" \
  -f "${REPO_ROOT}/deploy/docker/random-pub/Dockerfile" \
  "${REPO_ROOT}"

echo "--- Building examon-server ---"
docker build -t "${REGISTRY}/examon/examon-server:latest" \
  -f "${REPO_ROOT}/deploy/docker/examon-server/Dockerfile" \
  "${REPO_ROOT}"

echo "==> Pushing images to ${REGISTRY}"
docker push "${REGISTRY}/examon/mosquitto:latest"
docker push "${REGISTRY}/examon/kairosdb:1.3.0"
docker push "${REGISTRY}/examon/mqtt2kairosdb:latest"
docker push "${REGISTRY}/examon/random-pub:latest"
docker push "${REGISTRY}/examon/examon-server:latest"

echo "==> All images built and pushed successfully."
