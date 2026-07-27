# Dokumentation

## Installation über den Home-Assistant-App-Store

1. In Home Assistant **Einstellungen → Apps → App-Store** öffnen.
2. Rechts oben das Menü öffnen und **Repositorys** auswählen.
3. Folgende Adresse hinzufügen:

   ```text
   https://github.com/Q14siX/homeassistant-apps
   ```

4. Den **HACS Erweiterungsmanager** auswählen und installieren.
5. Die App starten.
6. Optional **In Seitenleiste anzeigen** aktivieren.

## Installierte Erweiterungen filtern

Oberhalb der Erweiterungsliste stehen drei kombinierbare Filter zur Verfügung:

- Suchfeld für Name, Domain, Repository und Installationspfad
- Kategoriefilter für Integrationen, Frontend, Themes, Python-Skripte, Templates, AppDaemon und NetDaemon
- Quellenfilter mit **Alle Quellen**, **Nur HACS** und **Nur lokal**

Als **HACS** gilt eine Erweiterung, die HACS in seiner Repository-Liste als installiert meldet. Aus ZIP-Dateien oder Sicherungen installierte Erweiterungen werden als **Lokal** angezeigt, solange sie nicht von HACS registriert sind.

## Unterstützte Installationsarchive

Der automatische Installer erkennt insbesondere:

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

Wenn HACS läuft, fragt die App `hacs/repositories/list` über die Home-Assistant-WebSocket-API ab. Beim Löschen einer HACS-verwalteten Erweiterung wird bevorzugt `hacs/repository/remove` verwendet, damit HACS seine Daten aktualisiert.

Eine aus einer lokalen ZIP oder Sicherung installierte Erweiterung wird technisch korrekt in den Home-Assistant-Konfigurationspfad kopiert. HACS stellt jedoch keine öffentliche Funktion bereit, um eine beliebige lokale ZIP nachträglich als von HACS heruntergeladene Installation zu registrieren. Solche Erweiterungen erscheinen deshalb als **Lokal**.

## Automatische Update-Prüfung

Die App fragt den Home-Assistant-Supervisor nach der installierten und der neuesten verfügbaren App-Version. Vor einer planmäßigen oder manuellen Prüfung wird der App-Store neu eingelesen, damit Änderungen im Sammel-Repository `https://github.com/Q14siX/homeassistant-apps` berücksichtigt werden.

Standardverhalten:

- erste Prüfung automatisch nach dem App-Start
- weitere Prüfungen alle 6 Stunden
- Statusanzeige direkt auf der Startseite
- auffälliger Hinweis bei verfügbarem Update
- manuelle Sofortprüfung über **Jetzt prüfen**

Konfigurationsoptionen:

- `automatic_update_check`: automatische Prüfung aktivieren oder deaktivieren
- `update_check_interval_hours`: Prüfintervall zwischen 1 und 168 Stunden

Die App installiert Updates nicht selbstständig. Die Aktualisierung erfolgt über **Einstellungen → Apps** oder über die automatische App-Aktualisierung des Supervisors.

## Sicherheitskopien

Bei Lösch- und Ersetzungsvorgängen kann die App vorab eine interne Sicherheitskopie unter `/data/safety_backups` anlegen. Diese Dateien gehören zum persistenten Datenbereich der App.

## Neustart

Nach Installation, Wiederherstellung oder Löschung zeigt die Weboberfläche einen Neustartdialog. **Jetzt neu starten** ruft den Supervisor-Endpunkt `/core/restart` auf. **Später** schließt den Dialog ohne Neustart.

## Optionen

- `max_upload_mb`: maximale Uploadgröße in MB
- `create_safety_backup`: interne Sicherung vor Löschen oder Ersetzen
- `prefer_hacs_uninstall`: HACS-WebSocket-Löschung bevorzugen
- `automatic_update_check`: automatische Prüfung auf neue App-Versionen
- `update_check_interval_hours`: Prüfintervall in Stunden

## Zugriffsrechte und Grenzen

Damit die App Erweiterungen sichern, installieren und entfernen kann, erhält sie schreibenden Zugriff auf den Home-Assistant-Konfigurationsordner. Installiere ausschließlich vertrauenswürdige ZIP-Dateien und bewahre zusätzlich eine vollständige Home-Assistant-Sicherung auf.

Die App ist für Home Assistant OS vorgesehen. Andere Installationsarten ohne Home-Assistant-App-Modell werden nicht unterstützt.
