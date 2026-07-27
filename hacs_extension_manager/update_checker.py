"""Automatic update checks through the Home Assistant Supervisor API."""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from supervisor import HomeAssistantClient, SupervisorError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _version_key(value: str) -> tuple[int, ...]:
    """Return a tolerant numeric comparison key for common version formats."""
    numbers = re.findall(r"\d+", str(value or ""))
    return tuple(int(number) for number in numbers) if numbers else (0,)


class UpdateChecker:
    """Cache and periodically refresh the Supervisor app update status."""

    def __init__(
        self,
        client: HomeAssistantClient,
        current_version: str,
        data_root: str | Path,
        *,
        enabled: bool = True,
        interval_hours: int = 6,
    ) -> None:
        self.client = client
        self.current_version = str(current_version)
        self.enabled = bool(enabled)
        self.interval = timedelta(hours=max(1, min(int(interval_hours), 168)))
        self.cache_path = Path(data_root) / "update_status.json"
        self._state_lock = threading.Lock()
        self._check_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._status: dict[str, Any] = self._default_status()
        self._load_cache()

    def _default_status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "checking": False,
            "available": self.client.available,
            "update_available": False,
            "installed_version": self.current_version,
            "latest_version": self.current_version,
            "auto_update": False,
            "repository": "",
            "checked_at": None,
            "next_check_at": None,
            "error": None,
            "message": "Update-Prüfung wurde noch nicht ausgeführt.",
        }

    def _load_cache(self) -> None:
        try:
            loaded = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(loaded, dict):
            return
        with self._state_lock:
            for key in self._status:
                if key in loaded:
                    self._status[key] = loaded[key]
            self._status["enabled"] = self.enabled
            self._status["available"] = self.client.available
            self._status["checking"] = False
            if self._status.get("installed_version") != self.current_version:
                self._status.update(
                    {
                        "installed_version": self.current_version,
                        "latest_version": self.current_version,
                        "update_available": False,
                        "checked_at": None,
                        "next_check_at": None,
                        "message": "App-Version wurde geändert; Update-Status wird neu geprüft.",
                    }
                )

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self._state_lock:
            payload = dict(self._status)
            payload["checking"] = False
        temp_path = self.cache_path.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(self.cache_path)
        except OSError:
            temp_path.unlink(missing_ok=True)

    def public_status(self) -> dict[str, Any]:
        with self._state_lock:
            return dict(self._status)

    def _is_stale(self, now: datetime) -> bool:
        checked_at = _parse_iso(self._status.get("checked_at"))
        return checked_at is None or now - checked_at >= self.interval

    def start(self) -> None:
        if self._thread is not None or not self.enabled or not self.client.available:
            if not self.enabled:
                with self._state_lock:
                    self._status["message"] = "Automatische Update-Prüfung ist deaktiviert."
            elif not self.client.available:
                with self._state_lock:
                    self._status.update(
                        {
                            "available": False,
                            "error": "SUPERVISOR_TOKEN ist nicht verfügbar.",
                            "message": "Update-Prüfung ist außerhalb von Home Assistant OS nicht verfügbar.",
                        }
                    )
            return
        self._thread = threading.Thread(
            target=self._run,
            name="hacs-extension-manager-update-check",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        # Give Supervisor a brief moment to finish its own startup sequence.
        if self._stop.wait(10.0):
            return
        while not self._stop.is_set():
            try:
                self.check(force=False)
            except Exception:
                # Unexpected failures are retried without terminating the app.
                with self._state_lock:
                    self._status.update(
                        {
                            "checking": False,
                            "available": False,
                            "error": "Unerwarteter Fehler bei der Update-Prüfung.",
                            "message": "Update-Prüfung wird automatisch erneut versucht.",
                        }
                    )
            status = self.public_status()
            next_check = _parse_iso(status.get("next_check_at"))
            now = _utc_now()
            wait_seconds = self.interval.total_seconds()
            if status.get("error") or not status.get("available"):
                wait_seconds = min(wait_seconds, 15 * 60)
            elif next_check is not None:
                wait_seconds = max(60.0, (next_check - now).total_seconds())
            self._stop.wait(wait_seconds)

    def stop(self) -> None:
        self._stop.set()

    def check(self, *, force: bool = False) -> dict[str, Any]:
        """Refresh the app store and query the currently installed app."""
        with self._check_lock:
            now = _utc_now()
            with self._state_lock:
                if not force and not self._is_stale(now):
                    return dict(self._status)
                self._status["checking"] = True
                self._status["error"] = None
                self._status["message"] = "Neueste App-Version wird geprüft …"

            if not self.client.available:
                with self._state_lock:
                    self._status.update(
                        {
                            "checking": False,
                            "available": False,
                            "error": "SUPERVISOR_TOKEN ist nicht verfügbar.",
                            "message": "Supervisor ist nicht erreichbar.",
                            "checked_at": _iso(now),
                            "next_check_at": _iso(now + self.interval),
                        }
                    )
                self._save_cache()
                return self.public_status()

            reload_warning: str | None = None
            try:
                self.client.reload_store()
            except SupervisorError as exc:
                # The cached Supervisor app data may still be usable even when
                # refreshing the store temporarily fails.
                reload_warning = str(exc)

            try:
                info = self.client.get_self_info()
                installed = str(info.get("version") or self.current_version)
                latest = str(info.get("version_latest") or installed)
                update_available = bool(info.get("update_available"))
                if not update_available and _version_key(latest) > _version_key(installed):
                    update_available = True

                message = (
                    f"Neue Version {latest} ist verfügbar."
                    if update_available
                    else "Die installierte App-Version ist aktuell."
                )
                if reload_warning:
                    message += " Der App-Store konnte nicht vollständig aktualisiert werden."

                with self._state_lock:
                    self._status.update(
                        {
                            "enabled": self.enabled,
                            "checking": False,
                            "available": True,
                            "update_available": update_available,
                            "installed_version": installed,
                            "latest_version": latest,
                            "auto_update": bool(info.get("auto_update")),
                            "repository": str(info.get("repository") or ""),
                            "checked_at": _iso(now),
                            "next_check_at": _iso(now + self.interval),
                            "error": reload_warning,
                            "message": message,
                        }
                    )
            except SupervisorError as exc:
                with self._state_lock:
                    self._status.update(
                        {
                            "checking": False,
                            "available": False,
                            "checked_at": _iso(now),
                            "next_check_at": _iso(now + self.interval),
                            "error": str(exc),
                            "message": "Update-Status konnte nicht ermittelt werden.",
                        }
                    )

            self._save_cache()
            return self.public_status()
