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

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> Any:
        if not path.startswith("/"):
            path = f"/{path}"
        try:
            response = requests.request(
                method,
                f"http://supervisor{path}",
                headers=self._headers(),
                json=payload,
                timeout=timeout or self.timeout,
            )
        except requests.RequestException as exc:
            raise SupervisorError(f"Supervisor ist nicht erreichbar: {exc}") from exc

        try:
            body = response.json()
        except ValueError:
            body = None

        if response.status_code >= 300:
            detail = ""
            if isinstance(body, dict):
                detail = str(body.get("message") or body.get("error") or "")
            if not detail:
                detail = response.text[:500]
            raise SupervisorError(
                f"Supervisor-Anfrage wurde abgelehnt ({response.status_code}): {detail}"
            )

        if isinstance(body, dict) and body.get("result") == "error":
            raise SupervisorError(str(body.get("message") or "Supervisor-Anfrage fehlgeschlagen."))
        if isinstance(body, dict) and "data" in body:
            return body.get("data")
        return body if body is not None else {"result": "ok"}

    def restart_core(self) -> Any:
        """Restart Home Assistant Core through Supervisor."""
        return self._request("POST", "/core/restart", payload={})

    def reload_store(self) -> Any:
        """Refresh app repositories and available versions."""
        return self._request("POST", "/store/reload", payload={}, timeout=120)

    def get_self_info(self) -> dict[str, Any]:
        """Return Supervisor metadata for the calling app."""
        result = self._request("GET", "/addons/self/info")
        if not isinstance(result, dict):
            raise SupervisorError("Supervisor lieferte keine gültigen App-Informationen.")
        return result

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
