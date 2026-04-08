#!/usr/bin/with-contenv bashio
# run.sh: Startet die Web-Anwendung
set -e # Beendet das Skript sofort, wenn ein Befehl fehlschlägt

bashio::log.info "========================================="
bashio::log.info "Starte 'Import / Export Helfer' Add-on..."
bashio::log.info "Add-on gestartet am: $(date)" # <--- HIER IST IHR WUNSCH
bashio::log.info "Überprüfe Python-Version:"
python3 --version
bashio::log.info "Überprüfe Flask-Installation:"
pip3 show flask

bashio::log.info "Starte Python Web-Server (main.py)..."

# Führt Python im ungepufferten Modus aus (-u),
# damit Logs sofort im Add-on-Log erscheinen.
python3 -u /app/main.py

