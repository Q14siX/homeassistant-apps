<p align="center">
  <img src="https://raw.githubusercontent.com/Q14siX/homeassistant-apps/main/hacs_extension_manager/logo.png" alt="HACS Erweiterungsmanager" />
</p>

# HACS Erweiterungsmanager

[![Home Assistant App](https://img.shields.io/badge/Home%20Assistant-App-41BDF5?logo=home-assistant&logoColor=white)](https://www.home-assistant.io/apps/)
[![Version](https://img.shields.io/badge/Version-20260726.190947-blue)](https://github.com/Q14siX/homeassistant-apps/tree/main/hacs_extension_manager)
[![Architektur](https://img.shields.io/badge/Architektur-amd64%20%7C%20aarch64-informational)](https://github.com/Q14siX/homeassistant-apps)
[![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green)](LICENSE)

Home-Assistant-App zur Sicherung, Entfernung, Installation und Wiederherstellung von HACS- und lokal installierten Erweiterungen. Die App verwendet eine responsive Ingress-Weboberfläche und ist ausschließlich für Home-Assistant-Administratoren sichtbar.

> Diese Anwendung ist eine **Home-Assistant-App** und ausdrücklich **keine Home-Assistant-Integration**.

## Installation über das Sammel-Repository

Füge im Home-Assistant-App-Store dieses Repository hinzu:

```text
https://github.com/Q14siX/homeassistant-apps
```

Danach kann der **HACS Erweiterungsmanager** direkt aus dem App-Store installiert werden.

## Funktionen

- installierte HACS-Erweiterungen über die HACS-WebSocket-Schnittstelle erkennen
- zusätzliche manuell oder aus ZIP-Dateien installierte Erweiterungen über das Dateisystem erkennen
- Erweiterungen nach **Alle Quellen**, **Nur HACS** oder **Nur lokal** filtern
- zusätzlich nach Kategorie filtern und über Name, Domain, Repository oder Pfad suchen
- Integrationen, Frontend-Erweiterungen, Themes, Python-Skripte, Jinja-Templates sowie AppDaemon- und NetDaemon-Anwendungen verwalten
- einzelne Erweiterungen als portable ZIP-Sicherung herunterladen
- Erweiterungen sichern und anschließend löschen
- neue Erweiterungen aus ZIP-Dateien installieren
- Sicherungsarchive wiederherstellen
- vorhandene Erweiterungen kontrolliert ersetzen
- nach Installation, Wiederherstellung oder Löschung einen Home-Assistant-Neustart anbieten
- beim Start und regelmäßig automatisch auf eine neue App-Version prüfen
- installierte und verfügbare App-Version direkt in der Oberfläche anzeigen
- App-Store-Status über **Jetzt prüfen** manuell aktualisieren
- Schutz vor ZIP-Path-Traversal, symbolischen Links und auffälligen ZIP-Bombs

## Installationsquelle HACS oder lokal

Eine Erweiterung wird als **HACS** angezeigt, wenn HACS sie in seiner Repository-Liste als installiert führt. Erweiterungen, die aus einer ZIP-Datei oder einer Sicherung eingespielt wurden und nicht von HACS registriert sind, werden als **Lokal** angezeigt. Der Quellenfilter arbeitet unabhängig vom Kategorie- und Suchfilter.

## Automatische Versionsprüfung

Die App fragt den Home-Assistant-Supervisor nach `version_latest` und `update_available`. Standardmäßig erfolgt die erste Prüfung beim Start und anschließend alle sechs Stunden. Vor der Prüfung wird der App-Store neu eingelesen, damit Änderungen im Sammel-Repository berücksichtigt werden.

Die App installiert Updates nicht eigenständig. Die Aktualisierung erfolgt weiterhin über **Einstellungen → Apps** oder über die dort aktivierbare automatische App-Aktualisierung.

## Konfiguration

```yaml
automatic_update_check: true
update_check_interval_hours: 6
```

Das Prüfintervall kann zwischen 1 und 168 Stunden eingestellt werden.

## Dokumentation

- [Ausführliche Dokumentation](DOCS.md)
- [Änderungsprotokoll](CHANGELOG.md)
- [Release-Hinweise](RELEASE.md)

## Lizenz

Veröffentlicht unter der [MIT-Lizenz](LICENSE).
