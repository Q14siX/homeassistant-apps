# Gotify Server – DOCS / Dokumentation

## Deutsch

### Überblick

Diese App stellt einen eigenen Gotify-Server innerhalb von Home Assistant bereit. Die Konfigurationsseite ist bewusst in wenige, klarere Gruppen aufgeteilt:

- **Allgemein**
- **Initiales Administratorkonto**
- **Datenbank**
- **Sicherheit & Proxys**
- **Erweitert**

Die meisten Installationen benötigen nur die ersten vier Bereiche. Der Bereich **Erweitert** fasst selten benötigte Spezialoptionen zusammen, damit die Oberfläche übersichtlicher bleibt.

### Allgemein

#### Home-Assistant-Zeitzone verwenden
Wenn diese Option aktiviert ist, versucht die App beim Start automatisch die in Home Assistant konfigurierte Zeitzone zu übernehmen. Dadurch müssen Nutzer die Zeitzone in der Regel nicht doppelt pflegen.

**Empfehlung:** Aktiviert lassen.

#### Eigene Zeitzone (optional)
Hier kann optional eine IANA-Zeitzone wie `Europe/Berlin` oder `Europe/Vienna` eingetragen werden. Sobald hier ein Wert eingetragen ist, hat dieser Vorrang vor der automatisch übernommenen Home-Assistant-Zeitzone.

**Typische Verwendung:** Nur setzen, wenn Gotify bewusst eine andere Zeitzone als Home Assistant verwenden soll.

#### Registrierung erlauben
Erlaubt neuen Benutzern, sich direkt über die Gotify-Weboberfläche selbst zu registrieren.

**Empfehlung:** Für private oder geschlossene Installationen meistens deaktiviert lassen.

### Initiales Administratorkonto

#### Benutzername
Benutzername des ersten Administrators, den Gotify beim ersten Erstellen einer neuen Datenbank anlegt.

#### Passwort
Passwort des ersten Administrators.

**Wichtig:** Diese beiden Werte werden nur beim allerersten Initialisieren einer neuen Gotify-Datenbank verwendet. Wenn bereits eine Datenbank unter `/data` existiert, ändern diese Felder keine bestehenden Benutzerkonten mehr.

### Datenbank

#### Datenbanktyp
Legt fest, welches Datenbank-Backend Gotify verwenden soll.

Verfügbare Werte:
- `sqlite3`
- `mysql`
- `postgres`

**Empfehlung:** Für die meisten Home-Assistant-Installationen ist `sqlite3` die einfachste und sinnvollste Wahl.

#### Verbindungszeichenfolge
Je nach gewähltem Datenbanktyp hat dieses Feld eine andere Bedeutung:

- **SQLite:** Dateipfad zur Datenbankdatei, z. B. `/data/gotify.db`
- **MySQL:** vollständiger MySQL-Connection-String
- **PostgreSQL:** vollständiger PostgreSQL-Connection-String

**Hinweis:** Bei SQLite sollte der Pfad unter `/data` liegen, damit die Daten dauerhaft erhalten bleiben.

### Sicherheit & Proxys

#### Bcrypt-Stärke
Bestimmt den Kostenfaktor für das Hashen von Passwörtern. Höhere Werte sind sicherer, benötigen aber mehr CPU-Zeit.

**Praxis:** Der Standardwert ist ein vernünftiger Kompromiss. Nur erhöhen, wenn genügend Leistung vorhanden ist und bewusst eine stärkere Hashing-Konfiguration gewünscht wird.

#### Vertrauenswürdige Proxys
Liste mit IP-Adressen oder Netzen, deren Forwarded-Header Gotify vertrauen darf. Das ist relevant, wenn Gotify hinter einem Reverse Proxy betrieben wird und Header wie `X-Forwarded-For` oder `X-Forwarded-Proto` ausgewertet werden sollen.

**Typische Verwendung:** Nur pflegen, wenn wirklich ein Reverse-Proxy-Aufbau vorhanden ist.

### Erweitert

Dieser Bereich bündelt bewusst alle Optionen, die für den normalen Betrieb meistens nicht angepasst werden müssen.

#### Zusätzliche Antwort-Header
Jeder Eintrag muss im Format `Header-Name: Wert` angegeben werden.

Beispiele:
- `X-Frame-Options: SAMEORIGIN`
- `Cache-Control: no-store`

Damit lassen sich zusätzliche HTTP-Antwort-Header an alle Antworten von Gotify anhängen.

#### Stream-Ping-Intervall
Intervall in Sekunden für die WebSocket-Pings des Echtzeit-Streams. Niedrigere Werte halten Verbindungen aktiver, erzeugen aber mehr Netzwerkverkehr.

#### Zusätzliche Stream-Origins
Liste zusätzlicher Origins, die den Echtzeit-Stream per WebSocket verwenden dürfen. Meist nur für spezielle Frontend- oder Proxy-Szenarien relevant.

#### CORS-Origins
Liste der erlaubten Ursprungs-URLs für Browser-Zugriffe auf die Gotify-API.

#### CORS-Methoden
Liste der erlaubten HTTP-Methoden für CORS, z. B. `GET`, `POST`, `DELETE`.

#### CORS-Header
Liste der erlaubten HTTP-Header für CORS, z. B. `Authorization` oder `Content-Type`.

#### Keepalive-Intervall
Intervall in Sekunden für TCP-Keepalive-Pakete.

- `0` verwendet den Go-Standard
- `-1` deaktiviert Keepalive

#### Listen-Adresse
Interne Bind-Adresse des Gotify-Webservers innerhalb des Containers.

**Empfehlung:** In der Regel leer lassen.

#### Pfad für hochgeladene Bilder
Verzeichnis für hochgeladene Applikationsbilder.

**Empfehlung:** Unter `/data` belassen, damit die Daten persistent sind.

#### Pfad für Plugins
Verzeichnis, aus dem Gotify Plugins lädt.

**Hinweis:** Nur relevant, wenn tatsächlich Plugins genutzt werden.

### Zeitzonenlogik der App

Die App verwendet folgende Reihenfolge:

1. **Eigene Zeitzone (optional)**, falls gesetzt
2. **Home-Assistant-Zeitzone**, falls aktiviert und abrufbar
3. Fallback auf **`Etc/UTC`**

Dadurch ist eine automatische Übernahme der Home-Assistant-Zeitzone möglich, auch wenn Home Assistant für App-Optionen selbst keinen dynamischen UI-Default pro Feld vorsieht.

---

## English

### Overview

This app provides a self-hosted Gotify server inside Home Assistant. The configuration page is intentionally grouped into fewer, clearer sections:

- **General**
- **Initial admin account**
- **Database**
- **Security & proxies**
- **Advanced**

Most installations only need the first four sections. The **Advanced** section collects less commonly needed options so the UI stays easier to understand.

### General

#### Use Home Assistant timezone
When this option is enabled, the app tries to automatically use the timezone configured in Home Assistant when it starts. In most cases this avoids maintaining the timezone twice.

**Recommendation:** Leave enabled.

#### Custom timezone (optional)
You can optionally enter an IANA timezone such as `Europe/Berlin` or `Europe/Vienna`. If a value is set here, it overrides the automatically detected Home Assistant timezone.

**Typical use case:** Only set this if Gotify should intentionally use a different timezone than Home Assistant.

#### Allow registration
Allows new users to register themselves directly through the Gotify web interface.

**Recommendation:** Usually leave disabled for private or closed installations.

### Initial admin account

#### Username
Username of the first administrator that Gotify creates when initializing a new database.

#### Password
Password of the first administrator.

**Important:** These values are only used during the very first initialization of a new Gotify database. If a database already exists under `/data`, changing these fields does not update existing user accounts.

### Database

#### Database type
Defines which database backend Gotify should use.

Available values:
- `sqlite3`
- `mysql`
- `postgres`

**Recommendation:** `sqlite3` is the simplest and most sensible choice for most Home Assistant installations.

#### Connection string
This field depends on the selected database type:

- **SQLite:** file path to the database file, for example `/data/gotify.db`
- **MySQL:** full MySQL connection string
- **PostgreSQL:** full PostgreSQL connection string

**Note:** For SQLite, the path should remain under `/data` to keep data persistent.

### Security & proxies

#### Bcrypt strength
Defines the cost factor used for password hashing. Higher values improve security but require more CPU time.

**Practical note:** The default value is a good compromise. Only increase it if enough performance is available and a stronger hashing setup is explicitly desired.

#### Trusted proxies
List of IP addresses or networks whose forwarded headers Gotify may trust. This matters when Gotify runs behind a reverse proxy and should evaluate headers such as `X-Forwarded-For` or `X-Forwarded-Proto`.

**Typical use case:** Only configure this when you actually use a reverse-proxy setup.

### Advanced

This section intentionally groups all options that usually do not need to be changed for normal operation.

#### Extra response headers
Each entry must use the format `Header-Name: Value`.

Examples:
- `X-Frame-Options: SAMEORIGIN`
- `Cache-Control: no-store`

This adds extra HTTP response headers to all Gotify responses.

#### Stream ping interval
Interval in seconds for WebSocket pings of the realtime stream. Lower values keep connections more active but create more network traffic.

#### Extra stream origins
List of additional origins that may use the realtime stream via WebSocket. Usually only relevant for special frontend or proxy scenarios.

#### CORS origins
List of allowed origin URLs for browser-based access to the Gotify API.

#### CORS methods
List of allowed HTTP methods for CORS, for example `GET`, `POST`, `DELETE`.

#### CORS headers
List of allowed HTTP headers for CORS, for example `Authorization` or `Content-Type`.

#### Keepalive interval
Interval in seconds for TCP keepalive packets.

- `0` uses the Go default
- `-1` disables keepalive

#### Listen address
Internal bind address of the Gotify web server inside the container.

**Recommendation:** Usually leave empty.

#### Uploaded images path
Directory for uploaded application images.

**Recommendation:** Keep it under `/data` so the data remains persistent.

#### Plugins path
Directory from which Gotify loads plugins.

**Note:** Only relevant if you actually use plugins.

### App timezone logic

The app resolves the timezone in this order:

1. **Custom timezone (optional)**, if set
2. **Home Assistant timezone**, if enabled and available
3. fallback to **`Etc/UTC`**

This makes automatic timezone reuse possible even though Home Assistant app options do not provide per-field dynamic UI defaults.
