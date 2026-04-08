# Gotify Server for Home Assistant

## Deutsch

**Gotify Server** bringt einen selbst gehosteten Push-Nachrichten-Server direkt in Home Assistant. Die App startet einen vollständigen Gotify-Server, speichert seine Daten dauerhaft im App-Datenverzeichnis und bindet die Weboberfläche sauber in Home Assistant ein.

Damit kannst du Benachrichtigungen, Statusmeldungen und Alarme im eigenen Umfeld betreiben, ohne dafür einen externen Push-Dienst zu benötigen.

### Funktionen

- vollständiger Gotify-Server direkt in Home Assistant
- Zugriff auf die Weboberfläche über **Ingress**
- **Öffnen**-Button auf der App-Seite
- zusätzlicher Zugriff über die **Seitenleiste**
- persistente Speicherung von Datenbank, Bildern und Plugins unter `/data`
- vollständig übersetzte Konfigurationsoberfläche in **Deutsch** und **Englisch**
- logisch gruppierte Konfiguration
- Unterstützung für **SQLite**, **MySQL** und **PostgreSQL**
- zusätzliche Optionen für **Trusted Proxies**, **Response Headers**, **Realtime-Stream** und **CORS**

### Installation

Füge das Repository direkt in Home Assistant hinzu:

[![Open your Home Assistant instance and show the add app repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FQ14siX%2Fgotify-homeassistant-app%2F)

Oder verwende manuell diese Repository-URL:

```text
https://github.com/Q14siX/gotify-homeassistant-app
```

Danach:

1. den App-Store neu laden
2. **Gotify Server** öffnen
3. die App installieren
4. die Konfiguration prüfen oder anpassen
5. die App starten
6. die Weboberfläche über **Öffnen** oder über die **Seitenleiste** aufrufen

### Typische Einsatzfälle

- Benachrichtigungen aus Home-Assistant-Automationen
- Meldungen aus Shell-Skripten, Cronjobs oder Containern
- Push-Nachrichten aus Self-Hosting-Diensten
- interne Status- und Alarmmeldungen im Heimnetz
- zentrale Nachrichtensammlung für eigene Projekte

### Konfigurationsbereiche

Die App gruppiert die Optionen bewusst in zusammenhängende Bereiche:

- **Allgemein**
- **Initiales Administratorkonto**
- **Datenbank**
- **Sicherheit & Proxys**
- **Antwort-Header**
- **Echtzeit-Stream**
- **CORS**
- **Server & Netzwerk intern**
- **Speicher & Plugins**

Eine ausführliche Erklärung aller Punkte findest du in `gotify/DOCS.md`.

### Wichtige Hinweise

- Die Daten des initialen Administratorkontos werden nur bei der **ersten Erstellung der Gotify-Datenbank** verwendet.
- Änderst du Benutzername oder Passwort später in der App-Konfiguration, wird eine bereits vorhandene Gotify-Datenbank dadurch nicht nachträglich umgeschrieben.
- Der empfohlene Zugriff innerhalb von Home Assistant erfolgt über **Ingress**.
- Der veröffentlichte Host-Port ist für direkten Netzwerkzugriff gedacht und nicht notwendig, wenn du ausschließlich Ingress verwendest.

---

## English

**Gotify Server** brings a self-hosted push notification server directly into Home Assistant. The app starts a full Gotify server, stores its data persistently in the app data directory, and cleanly integrates the web interface into Home Assistant.

This allows you to run notifications, status messages, and alerts in your own environment without relying on an external push service.

### Features

- full Gotify server running directly inside Home Assistant
- access to the web interface through **ingress**
- **Open** button on the app page
- additional access through the **sidebar**
- persistent storage of database, images, and plugins under `/data`
- fully translated configuration UI in **German** and **English**
- logically grouped configuration
- support for **SQLite**, **MySQL**, and **PostgreSQL**
- additional options for **trusted proxies**, **response headers**, **realtime stream**, and **CORS**

### Installation

Add the repository directly to Home Assistant:

[![Open your Home Assistant instance and show the add app repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FQ14siX%2Fgotify-homeassistant-app%2F)

Or use this repository URL manually:

```text
https://github.com/Q14siX/gotify-homeassistant-app
```

Then:

1. reload the app store
2. open **Gotify Server**
3. install the app
4. review or adjust the configuration
5. start the app
6. open the web interface through **Open** or through the **sidebar**

### Typical use cases

- notifications from Home Assistant automations
- messages from shell scripts, cron jobs, or containers
- push notifications from self-hosted services
- internal status and alert messages in your network
- central message collection for your own projects

### Configuration groups

The app intentionally groups options into related areas:

- **General**
- **Initial admin account**
- **Database**
- **Security & proxies**
- **Response headers**
- **Realtime stream**
- **CORS**
- **Server & internal networking**
- **Storage & plugins**

A detailed explanation of every option is available in `gotify/DOCS.md`.

### Important notes

- The initial admin account values are only used when the Gotify database is **created for the first time**.
- If you later change the username or password in the app configuration, an existing Gotify database is not rewritten retroactively.
- **Ingress** is the recommended access method inside Home Assistant.
- The published host port is intended for direct network access and is not required if you only use ingress.
