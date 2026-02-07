#!/usr/bin/env bash
set -e

compose_args=("up" "-d")

if [[ "${1:-}" == "--build" ]]; then
  compose_args=("up" "--build" "-d")
fi

docker compose "${compose_args[@]}"

docker compose exec test-flex-schema bash
