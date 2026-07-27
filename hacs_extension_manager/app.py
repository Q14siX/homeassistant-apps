"""Ingress web UI for the HACS Extension Manager app."""
from __future__ import annotations

import json
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from werkzeug.utils import secure_filename

from manager import APP_VERSION, ExtensionManager, ManagerError
from supervisor import HomeAssistantClient, SupervisorError
from update_checker import UpdateChecker


def load_options() -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "max_upload_mb": 250,
        "create_safety_backup": True,
        "prefer_hacs_uninstall": True,
        "automatic_update_check": True,
        "update_check_interval_hours": 6,
    }
    try:
        loaded = json.loads(Path("/data/options.json").read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            defaults.update(loaded)
    except (OSError, json.JSONDecodeError):
        pass
    return defaults


OPTIONS = load_options()
CONFIG_ROOT = Path(os.environ.get("HOMEASSISTANT_CONFIG", "/homeassistant"))
DATA_ROOT = Path(os.environ.get("APP_DATA", "/data"))
HA_CLIENT = HomeAssistantClient()
UPDATE_CHECKER = UpdateChecker(
    HA_CLIENT,
    APP_VERSION,
    DATA_ROOT,
    enabled=bool(OPTIONS["automatic_update_check"]),
    interval_hours=int(OPTIONS["update_check_interval_hours"]),
)
UPDATE_CHECKER.start()

MANAGER = ExtensionManager(
    CONFIG_ROOT,
    DATA_ROOT,
    ha_client=HA_CLIENT,
    max_upload_mb=int(OPTIONS["max_upload_mb"]),
    create_safety_backup=bool(OPTIONS["create_safety_backup"]),
    prefer_hacs_uninstall=bool(OPTIONS["prefer_hacs_uninstall"]),
)

app = Flask(__name__, static_url_path="/static")
CSRF_TOKEN = secrets.token_urlsafe(32)
app.config.update(
    MAX_CONTENT_LENGTH=MANAGER.max_upload_bytes + 1024 * 1024,
    SECRET_KEY=secrets.token_hex(32),
    JSON_AS_ASCII=False,
)
RESTART_REQUIRED = False


@app.before_request
def csrf_protection():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.path.startswith("/api/"):
        supplied = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(supplied, CSRF_TOKEN):
            return jsonify({"ok": False, "error": "Ungültige oder abgelaufene Sitzung."}), 403
    return None


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; img-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'self'"
    )
    return response


@app.get("/")
def index():
    return render_template("index.html", version=APP_VERSION, csrf_token=CSRF_TOKEN)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "version": APP_VERSION})


@app.get("/api/status")
def status():
    return jsonify(
        {
            "version": APP_VERSION,
            "config_root": str(CONFIG_ROOT),
            "restart_required": RESTART_REQUIRED,
            "hacs": MANAGER.hacs_status,
            "max_upload_mb": OPTIONS["max_upload_mb"],
            "update": UPDATE_CHECKER.public_status(),
        }
    )


@app.get("/api/update-status")
def update_status():
    return jsonify({"ok": True, **UPDATE_CHECKER.public_status()})


@app.post("/api/update-status/check")
def check_update_status():
    return jsonify({"ok": True, **UPDATE_CHECKER.check(force=True)})


@app.get("/api/extensions")
def extensions():
    items = MANAGER.scan()
    return jsonify(
        {
            "items": [item.public() for item in items],
            "hacs": MANAGER.hacs_status,
            "count": len(items),
        }
    )


@app.post("/api/extensions/<extension_id>/archive")
def archive(extension_id: str):
    extension = MANAGER.get_extension(extension_id)
    archive_path = MANAGER.create_archive(extension)
    return send_file(
        archive_path,
        as_attachment=True,
        download_name=archive_path.name,
        mimetype="application/zip",
        max_age=0,
    )


@app.post("/api/extensions/<extension_id>/delete")
def delete(extension_id: str):
    global RESTART_REQUIRED
    extension = MANAGER.get_extension(extension_id)
    result = MANAGER.delete_extension(extension)
    RESTART_REQUIRED = True
    return jsonify({"ok": True, "restart_required": True, **result})


@app.post("/api/install")
def install():
    global RESTART_REQUIRED
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise ManagerError("Es wurde keine ZIP-Datei ausgewählt.")
    filename = secure_filename(upload.filename)
    if not filename.lower().endswith(".zip"):
        raise ManagerError("Es sind ausschließlich ZIP-Dateien zulässig.")
    category = request.form.get("category", "auto")
    allowed = {"auto", "integration", "plugin", "theme", "python_script", "template", "appdaemon", "netdaemon"}
    if category not in allowed:
        raise ManagerError("Ungültiger Erweiterungstyp.")
    overwrite = request.form.get("overwrite", "false").lower() in {"1", "true", "yes", "on"}

    MANAGER.upload_root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="upload-", suffix=".zip", dir=MANAGER.upload_root, delete=False
    ) as handle:
        temp_path = Path(handle.name)
        upload.save(handle)
    try:
        result = MANAGER.install_zip(temp_path, filename, category, overwrite)
    finally:
        temp_path.unlink(missing_ok=True)
    RESTART_REQUIRED = True
    return jsonify({"ok": True, "restart_required": True, **result})


@app.post("/api/restart")
def restart():
    global RESTART_REQUIRED
    result = HA_CLIENT.restart_core()
    RESTART_REQUIRED = False
    return jsonify({"ok": True, "message": "Home Assistant wird neu gestartet.", "result": result})


@app.errorhandler(ManagerError)
@app.errorhandler(SupervisorError)
def expected_error(exc):
    return jsonify({"ok": False, "error": str(exc)}), 400


@app.errorhandler(RequestEntityTooLarge)
def too_large(_exc):
    return jsonify(
        {
            "ok": False,
            "error": f"Die Datei ist größer als {OPTIONS['max_upload_mb']} MB.",
        }
    ), 413


@app.errorhandler(Exception)
def unexpected_error(exc):
    if isinstance(exc, HTTPException):
        return jsonify({"ok": False, "error": exc.description}), exc.code
    app.logger.exception("Unbehandelter Fehler")
    return jsonify({"ok": False, "error": "Interner Fehler. Details stehen im App-Protokoll."}), 500
