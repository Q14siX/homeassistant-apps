# Dokumentation

## Installation über den Home-Assistant-App-Store

1. In Home Assistant **Einstellungen → Apps → App-Store** öffnen.
2. Rechts oben das Menü öffnen und **Repositorys** auswählen.
3. Folgende Adresse hinzufügen:

   ```text
   https://github.com/Q14siX/hacs_extension_manager/
   ```

4. Den **HACS Erweiterungsmanager** auswählen und installieren.
5. Die App starten.
6. Optional **In Seitenleiste anzeigen** aktivieren.

Home Assistant baut die App aus dem im Repository enthaltenen `Dockerfile`. Während dieses ersten Builds muss die Home-Assistant-Installation auf die benötigten Alpine- und Python-Pakete zugreifen können.

## Alternative lokale Installation

1. Den Ordner `hacs_extension_manager` in das Home-Assistant-Verzeichnis `/addons/` kopieren.
2. Im App-Store **Nach Updates suchen** auswählen.
3. Die App unter **Lokale Apps** installieren und starten.

## Unterstützte Installationsarchive

Der automatische Installer erkennt insbesondere folgende Integrationsstrukturen:

- Repository-ZIP mit `custom_components/<domain>/manifest.json`
- ZIP mit einem obersten Integrationsordner `<domain>/manifest.json`
- direkte Integrations-ZIP mit `manifest.json` im Stammverzeichnis
- Sicherungs-ZIP des HACS Erweiterungsmanagers mit `hacs-extension-manager.json`

Mac-spezifische `__MACOSX`- und `.DS_Store`-Dateien werden entfernt. Entwicklungs- und Cacheordner wie `__pycache__`, `.git`, `.github`, `.idea` und `.vscode` werden nicht installiert oder gesichert.

## Sicherungsformat

Eine Sicherung enthält:

- `hacs-extension-manager.json` mit Kategorie, ursprünglichem Zielpfad, Version und SHA-256-Prüfsumme
- `payload/` mit den eigentlichen Erweiterungsdateien

Die Sicherung kann über die Upload-Funktion wiederhergestellt werden. Der Zielpfad wird aus den gesicherten Metadaten übernommen; vor der Installation wird die SHA-256-Prüfsumme kontrolliert.

## HACS-Status

Wenn HACS läuft, fragt die App die HACS-WebSocket-Funktion `hacs/repositories/list` ab. Beim Löschen einer HACS-verwalteten Erweiterung wird bevorzugt `hacs/repository/remove` verwendet, damit HACS seine Daten aktualisiert.

Eine aus einer lokalen ZIP oder Sicherung installierte Erweiterung wird technisch korrekt in den Home-Assistant-Konfigurationspfad kopiert. HACS bietet jedoch keine öffentliche Funktion, um eine beliebige lokale ZIP als von HACS heruntergeladen zu registrieren. Die App zeigt solche Installationen deshalb zusätzlich über ihren Dateisystem-Scan an. Für spätere HACS-Updates kann die betreffende Erweiterung in HACS erneut heruntergeladen werden.

## Sicherheitskopien

Bei Lösch- und Ersetzungsvorgängen kann die App vorab eine interne Sicherheitskopie unter `/data/safety_backups` anlegen. Diese Dateien gehören zum persistenten Datenbereich der App.

## Neustart

Nach Installation, Wiederherstellung oder Löschung zeigt die Weboberfläche einen Neustartdialog. **Jetzt neu starten** ruft den Supervisor-Endpunkt `/core/restart` auf. **Später** schließt den Dialog ohne Neustart.

## Optionen

- `max_upload_mb`: maximale Uploadgröße in MB
- `create_safety_backup`: interne Sicherung vor Löschen oder Ersetzen
- `prefer_hacs_uninstall`: HACS-WebSocket-Löschung bevorzugen

## Zugriffsrechte und Grenzen

Damit die App Erweiterungen sichern, installieren und entfernen kann, erhält sie schreibenden Zugriff auf den Home-Assistant-Konfigurationsordner. Installiere ausschließlich vertrauenswürdige ZIP-Dateien und bewahre zusätzlich eine vollständige Home-Assistant-Sicherung auf.

Die App ist für Home Assistant OS vorgesehen. Andere Installationsarten ohne Home-Assistant-App-Modell werden nicht unterstützt.
