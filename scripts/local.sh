#!/bin/bash
set -e

IMAGE_NAME="${IMAGE_NAME:-locust-async-chat}"
IMAGE_TAG="${IMAGE_TAG:-local}"
ENV_FILE="${ENV_FILE:-.env}"

echo "==> Building image: ${IMAGE_NAME}:${IMAGE_TAG}"
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .

echo "==> Running container (env from ${ENV_FILE})"
echo "    Locust UI: http://localhost:8089"
echo "    Webhook:   http://localhost:44379"
docker run --rm --env-file "${ENV_FILE}" -p 8089:8089 -p 44379:44379 "${IMAGE_NAME}:${IMAGE_TAG}"
