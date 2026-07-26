"""Communication with Home Assistant Core and Supervisor."""
from __future__ import annotations

import json
import os
import threading
from typing import Any

import requests
import websocket


class SupervisorError(RuntimeError):
    """Raised when a Supervisor or Core API operation fails."""


class HomeAssistantClient:
    """Small synchronous client for the internal Supervisor proxies."""

    def __init__(self, token: str | None = None, timeout: int = 30) -> None:
        self.token = token or os.environ.get("SUPERVISOR_TOKEN", "")
        self.timeout = timeout
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return bool(self.token)

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise SupervisorError("SUPERVISOR_TOKEN ist nicht verfügbar.")
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def restart_core(self) -> dict[str, Any]:
        """Restart Home Assistant Core through Supervisor."""
        try:
            response = requests.post(
                "http://supervisor/core/restart",
                headers=self._headers(),
                json={},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise SupervisorError(f"Supervisor ist nicht erreichbar: {exc}") from exc
        if response.status_code >= 300:
            raise SupervisorError(
                f"Neustart wurde abgelehnt ({response.status_code}): {response.text[:500]}"
            )
        try:
            return response.json()
        except ValueError:
            return {"result": "ok"}

    def websocket_command(self, command: dict[str, Any]) -> Any:
        """Execute one Home Assistant WebSocket command."""
        if not self.token:
            raise SupervisorError("SUPERVISOR_TOKEN ist nicht verfügbar.")

        with self._lock:
            ws = None
            try:
                ws = websocket.create_connection(
                    "ws://supervisor/core/websocket",
                    timeout=self.timeout,
                    header=[f"Authorization: Bearer {self.token}"],
                )
                hello = json.loads(ws.recv())
                if hello.get("type") != "auth_required":
                    raise SupervisorError(f"Unerwartete WebSocket-Antwort: {hello}")

                ws.send(json.dumps({"type": "auth", "access_token": self.token}))
                auth = json.loads(ws.recv())
                if auth.get("type") != "auth_ok":
                    raise SupervisorError(
                        f"Home-Assistant-Authentifizierung fehlgeschlagen: {auth}"
                    )

                message = {"id": 1, **command}
                ws.send(json.dumps(message))
                while True:
                    result = json.loads(ws.recv())
                    if result.get("id") != 1:
                        continue
                    if result.get("type") != "result":
                        raise SupervisorError(f"Unerwartete WebSocket-Antwort: {result}")
                    if not result.get("success", False):
                        error = result.get("error") or {}
                        raise SupervisorError(
                            error.get("message")
                            or error.get("code")
                            or "WebSocket-Befehl fehlgeschlagen."
                        )
                    return result.get("result")
            except (OSError, websocket.WebSocketException, json.JSONDecodeError) as exc:
                raise SupervisorError(f"Home-Assistant-WebSocket nicht erreichbar: {exc}") from exc
            finally:
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass

    def list_hacs_repositories(self) -> list[dict[str, Any]]:
        result = self.websocket_command({"type": "hacs/repositories/list"})
        if not isinstance(result, list):
            raise SupervisorError("HACS lieferte keine Repository-Liste.")
        return [item for item in result if isinstance(item, dict)]

    def remove_hacs_repository(self, repository_id: str) -> None:
        self.websocket_command(
            {"type": "hacs/repository/remove", "repository": str(repository_id)}
        )
