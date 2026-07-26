# Änderungsprotokoll

## 20260726.142202

- neues ICON im Kopfbereich der Ingress-Weboberfläche eingebunden
- bisherigen Platzhalterbuchstaben `H` entfernt
- App-ICON als Browser-Favicon ergänzt
- ICON und LOGO den statischen Webressourcen hinzugefügt

## 20260726.142202

- neues ICON und neues LOGO integriert
- Grafiken für die Home-Assistant-App-Store-Darstellung zugeschnitten und mit Innenabstand aufbereitet
- JavaScript-Fehler `Cannot read properties of null (reading 'reset')` nach erfolgreicher ZIP-Installation behoben
- Uploadformular wird nach der Installation korrekt zurückgesetzt
- Neustartdialog wird nach der Installation zuverlässig geöffnet

## 20260726.133642

- GitHub-Repository-Struktur für die Installation über den Home-Assistant-App-Store ergänzt
- Repository-Metadaten und direkte Installationsverweise hinzugefügt
- Repository-URL in die App-Konfiguration aufgenommen
- README und Dokumentation für die GitHub-Installation überarbeitet
- Docker-Metadaten um Quellcode- und Dokumentationsverweise erweitert

## 20260726.125208

- Erste Version
- HACS-WebSocket-Erkennung und Dateisystem-Fallback
- Sicherung, Download, Löschen und Sichern-und-Löschen
- automatischer ZIP-Installer für mehrere Paketstrukturen
- Wiederherstellung eigener Sicherungsarchive mit Prüfsummenprüfung
- Unterstützung der aktuellen HACS-Kategorie für Jinja-Templates unter `custom_templates`
- Sicherheitskopien und transaktionaler Austausch vorhandener Erweiterungen
- Supervisor-Neustartdialog
- responsive Ingress-Weboberfläche
- CSRF-Schutz für alle schreibenden Ingress-Aktionen
