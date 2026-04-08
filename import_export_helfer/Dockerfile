# Dockerfile: Baut das Image
ARG BUILD_FROM
FROM $BUILD_FROM

# Korrigiertes ENV-Format
ENV LANG=C.UTF-8

# Installiert pip
RUN apk add --no-cache py3-pip

# Den App-Code kopieren
WORKDIR /app
COPY app/ /app

# Installieren der Python-Abhängigkeiten
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Kopiere das run.sh-Skript an die richtige Stelle und mache es ausführbar
# Das S6-Overlay (von Home Assistant) erwartet dieses Skript unter /
COPY run.sh /
RUN chmod a+x /run.sh

# === KORREKTUR ===
# Explizit angeben, welches Skript als Hauptprozess gestartet werden soll.
# Das ist es, was gefehlt hat.
CMD [ "/run.sh" ]

