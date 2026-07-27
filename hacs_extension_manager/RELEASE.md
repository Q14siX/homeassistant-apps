# Release 20260726.190947

## Automatische Update-Prüfung und Quellenfilter

Diese Version erweitert den HACS Erweiterungsmanager um eine automatische Versionsprüfung und einen zusätzlichen Filter für die Installationsquelle.

## Repository

```text
https://github.com/Q14siX/homeassistant-apps
```

App-Verzeichnis:

```text
hacs_extension_manager
```

## Änderungen

- automatische Prüfung auf neue App-Versionen beim Start
- regelmäßige Versionsprüfung standardmäßig alle 6 Stunden
- App-Store wird vor der Prüfung neu eingelesen
- Anzeige von installierter und neuester verfügbarer Version
- auffälliger Hinweis bei verfügbarem Update
- manuelle Sofortprüfung über **Jetzt prüfen**
- konfigurierbares Prüfintervall von 1 bis 168 Stunden
- zusätzliche Quellenfilter **Alle Quellen**, **Nur HACS** und **Nur lokal**
- Quellenfilter mit Suche und Kategoriefilter kombinierbar
- lokale Erweiterungen erhalten eine eigene farbliche Kennzeichnung
- Repository- und Dokumentationsverweise auf `Q14siX/homeassistant-apps` umgestellt
- Versionsangaben auf `20260726.190947` aktualisiert

## Aktualisierung

1. Den Ordner `hacs_extension_manager` im Repository `https://github.com/Q14siX/homeassistant-apps` durch die neue Version ersetzen.
2. Änderungen nach GitHub übertragen.
3. In Home Assistant **Einstellungen → Apps → App-Store** öffnen.
4. **Nach Updates suchen** ausführen.
5. Den HACS Erweiterungsmanager aktualisieren und neu starten.

## Hinweis

Die automatische Prüfung informiert über eine neue Version. Die App installiert ein Update nicht selbstständig. Ist die automatische App-Aktualisierung im Home-Assistant-Supervisor aktiviert, zeigt die App diesen Status im Update-Hinweis an.
