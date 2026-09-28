#!/bin/sh
set -eu

echo "Starting TEST promotion..."
docker compose -f docker-compose.test.yml build
docker compose -f docker-compose.test.yml up -d

echo "Waiting for TEST service..."
for i in $(seq 1 10); do
  if curl -fsS http://localhost:5001/health; then
    echo
    echo "TEST promotion successful."
    exit 0
  fi
  sleep 2
done

echo "TEST promotion failed."
docker compose -f docker-compose.test.yml logs
exit 1
