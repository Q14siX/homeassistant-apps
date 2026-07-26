#!/usr/bin/with-contenv bashio
set -euo pipefail

bashio::log.info "Starte HACS Erweiterungsmanager ..."
exec gunicorn \
  --bind 0.0.0.0:8099 \
  --workers 1 \
  --threads 4 \
  --timeout 300 \
  --access-logfile - \
  --error-logfile - \
  app:app
