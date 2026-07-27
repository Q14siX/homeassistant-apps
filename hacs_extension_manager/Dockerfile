FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION="dev"
ARG BUILD_ARCH="amd64"

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}" \
  org.opencontainers.image.title="HACS Erweiterungsmanager" \
  org.opencontainers.image.description="Sichern, löschen und Wiederherstellen von HACS-Erweiterungen" \
  org.opencontainers.image.source="https://github.com/Q14siX/homeassistant-apps" \
  org.opencontainers.image.documentation="https://github.com/Q14siX/homeassistant-apps/blob/main/hacs_extension_manager/DOCS.md" \
  org.opencontainers.image.licenses="MIT"

RUN apk add --no-cache python3 py3-pip && \
    python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir \
      Flask==3.1.1 \
      gunicorn==23.0.0 \
      requests==2.32.4 \
      websocket-client==1.8.0

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    HOMEASSISTANT_CONFIG=/homeassistant \
    APP_DATA=/data

WORKDIR /app
COPY app.py manager.py supervisor.py update_checker.py ./
COPY templates ./templates
COPY static ./static
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
