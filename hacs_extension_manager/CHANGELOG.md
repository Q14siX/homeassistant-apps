# Änderungsprotokoll

## 20260726.190947

- automatische Update-Prüfung über die Home-Assistant-Supervisor-API ergänzt
- App-Store wird vor planmäßigen und manuellen Prüfungen aktualisiert
- installierte und neueste verfügbare App-Version werden angezeigt
- auffälliger Update-Hinweis und Schaltfläche **Jetzt prüfen** ergänzt
- Prüfintervall über die App-Konfiguration einstellbar
- Quellenfilter **Alle Quellen**, **Nur HACS** und **Nur lokal** ergänzt
- Quellenfilter mit Suche und Kategoriefilter kombinierbar
- lokale Installationen farblich eindeutig gekennzeichnet
- Repository- und Dokumentationsverweise auf `Q14siX/homeassistant-apps` umgestellt


## 20260726.142202

- neues ICON im Kopfbereich der Ingress-Weboberfläche eingebunden
- bisherigen Platzhalterbuchstaben `H` entfernt
- App-ICON als Browser-Favicon ergänzt
- ICON und LOGO den statischen Webressourcen hinzugefügt
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
