# HACS Erweiterungsmanager

Home-Assistant-App zur Verwaltung installierter HACS- und lokaler Erweiterungen. Die App kann Erweiterungen sichern, herunterladen, löschen, aus ZIP-Dateien installieren und aus eigenen Sicherungsarchiven wiederherstellen.

## Kernfunktionen

- HACS-Erweiterungen über die Home-Assistant-WebSocket-API erkennen
- manuell installierte Erweiterungen über das Dateisystem ergänzen
- Integrationen, Frontend-Erweiterungen, Themes, Python-Skripte, Templates sowie AppDaemon- und NetDaemon-Anwendungen sichern
- portable ZIP-Sicherungen herunterladen
- Erweiterungen löschen oder in einem Schritt sichern und löschen
- ZIP-Dateien automatisch analysieren und installieren
- vorhandene Erweiterungen mit vorheriger Sicherheitskopie ersetzen
- nach Änderungen einen Home-Assistant-Neustart anbieten
- unsichere ZIP-Pfade, symbolische Links und auffällige ZIP-Bombs blockieren

## Installation über GitHub

Füge im Home-Assistant-App-Store folgendes Repository hinzu:

```text
https://github.com/Q14siX/homeassistant-apps
```

Öffne anschließend den **HACS Erweiterungsmanager**, installiere und starte die App. Über **In Seitenleiste anzeigen** kann die Ingress-Oberfläche dauerhaft in die Navigation aufgenommen werden.

Ausführliche Hinweise stehen in `DOCS.md`.
