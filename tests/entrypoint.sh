#!/usr/bin/env bash
set -e

python /app/seed_mysql.py
exec "$@"
