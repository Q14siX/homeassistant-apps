"""Filesystem and ZIP management for HACS extensions."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import stat
import tempfile
import threading
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from supervisor import HomeAssistantClient, SupervisorError

APP_VERSION = "20260726.142202"
ARCHIVE_FORMAT = "hacs-extension-manager/v1"
METADATA_NAME = "hacs-extension-manager.json"
IGNORED_NAMES = {".DS_Store", "Thumbs.db"}
IGNORED_PARTS = {"__MACOSX", "__pycache__", ".git", ".github", ".idea", ".vscode"}
CATEGORY_LABELS = {
    "integration": "Integration",
    "plugin": "Frontend",
    "theme": "Theme",
    "python_script": "Python-Skript",
    "template": "Template",
    "appdaemon": "AppDaemon",
    "netdaemon": "NetDaemon",
    "unknown": "Sonstige",
}


class ManagerError(RuntimeError):
    """User-facing extension manager error."""


@dataclass(slots=True)
class Extension:
    id: str
    category: str
    name: str
    path: str
    relative_path: str
    version: str = ""
    domain: str = ""
    repository: str = ""
    repository_id: str = ""
    source: str = "filesystem"
    size: int = 0
    modified: str = ""
    protected: bool = False
    warnings: list[str] = field(default_factory=list)

    def public(self) -> dict[str, Any]:
        data = asdict(self)
        data["category_label"] = CATEGORY_LABELS.get(self.category, self.category)
        return data


@dataclass(slots=True)
class InstallCandidate:
    category: str
    name: str
    source_path: Path
    destination_relative: str
    version: str = ""
    domain: str = ""
    archive_metadata: dict[str, Any] = field(default_factory=dict)


class ExtensionManager:
    def __init__(
        self,
        config_root: str | Path,
        data_root: str | Path,
        ha_client: HomeAssistantClient | None = None,
        max_upload_mb: int = 250,
        create_safety_backup: bool = True,
        prefer_hacs_uninstall: bool = True,
    ) -> None:
        self.config_root = Path(config_root).resolve()
        self.data_root = Path(data_root).resolve()
        self.ha_client = ha_client or HomeAssistantClient()
        self.max_upload_bytes = max_upload_mb * 1024 * 1024
        self.max_uncompressed_bytes = max(self.max_upload_bytes * 5, 1024 * 1024 * 1024)
        self.create_safety_backup = create_safety_backup
        self.prefer_hacs_uninstall = prefer_hacs_uninstall
        self.archive_root = self.data_root / "archives"
        self.safety_root = self.data_root / "safety_backups"
        self.upload_root = self.data_root / "uploads"
        for path in (self.archive_root, self.safety_root, self.upload_root):
            path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.hacs_status: dict[str, Any] = {
            "available": False,
            "message": "Noch nicht geprüft",
        }

    # ---------- IDs and paths ----------
    @staticmethod
    def _encode_id(category: str, relative_path: str) -> str:
        raw = f"{category}\0{relative_path}".encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_id(value: str) -> tuple[str, str]:
        try:
            padded = value + "=" * (-len(value) % 4)
            raw = base64.urlsafe_b64decode(padded).decode("utf-8")
            category, relative_path = raw.split("\0", 1)
            return category, relative_path
        except Exception as exc:
            raise ManagerError("Ungültige Erweiterungs-ID.") from exc

    def _path_from_relative(self, relative_path: str) -> Path:
        candidate = (self.config_root / relative_path).resolve()
        try:
            candidate.relative_to(self.config_root)
        except ValueError as exc:
            raise ManagerError("Pfad liegt außerhalb der Home-Assistant-Konfiguration.") from exc
        return candidate

    def _translate_hacs_path(self, path: str | None) -> Path | None:
        if not path:
            return None
        normalized = str(path).replace("\\", "/")
        if normalized == "/config":
            return self.config_root
        if normalized.startswith("/config/"):
            return self.config_root / normalized.removeprefix("/config/")
        candidate = Path(normalized)
        if candidate.is_absolute():
            try:
                candidate.resolve().relative_to(self.config_root)
                return candidate.resolve()
            except (ValueError, OSError):
                return None
        return self._path_from_relative(normalized)

    # ---------- Scanning ----------
    def scan(self) -> list[Extension]:
        with self._lock:
            found: dict[tuple[str, str], Extension] = {}
            self._scan_hacs(found)
            self._scan_filesystem(found)
            items = list(found.values())
            for item in items:
                path = Path(item.path)
                item.size = self._path_size(path)
                item.modified = self._modified_iso(path)
            return sorted(items, key=lambda x: (x.category, x.name.lower()))

    def _scan_hacs(self, found: dict[tuple[str, str], Extension]) -> None:
        try:
            repositories = self.ha_client.list_hacs_repositories()
            self.hacs_status = {
                "available": True,
                "message": "HACS-WebSocket verbunden",
            }
        except Exception as exc:
            self.hacs_status = {
                "available": False,
                "message": str(exc),
            }
            return

        for repo in repositories:
            if not repo.get("installed"):
                continue
            category = str(repo.get("category") or "unknown")
            local_path = self._translate_hacs_path(repo.get("local_path"))
            if local_path is None:
                continue
            # HACS reports the directory for single-file categories; include the actual file.
            if category in {"python_script", "template"} and repo.get("file_name"):
                local_path = local_path / str(repo["file_name"])
            if category == "theme" and not local_path.exists():
                name = str(repo.get("name") or Path(local_path).name)
                theme_file = self.config_root / "themes" / f"{name}.yaml"
                if theme_file.exists():
                    local_path = theme_file
            if not local_path.exists():
                continue
            try:
                relative = local_path.resolve().relative_to(self.config_root).as_posix()
            except ValueError:
                continue
            name = str(repo.get("name") or repo.get("domain") or local_path.name)
            if category == "integration" and str(repo.get("domain") or "") == "hacs":
                continue
            key = (category, relative)
            found[key] = Extension(
                id=self._encode_id(category, relative),
                category=category,
                name=name,
                path=str(local_path),
                relative_path=relative,
                version=str(repo.get("installed_version") or ""),
                domain=str(repo.get("domain") or ""),
                repository=str(repo.get("full_name") or ""),
                repository_id=str(repo.get("id") or ""),
                source="hacs",
                protected=False,
            )

    def _scan_filesystem(self, found: dict[tuple[str, str], Extension]) -> None:
        # Integrations
        root = self.config_root / "custom_components"
        if root.is_dir():
            for directory in root.iterdir():
                if not directory.is_dir() or directory.name.startswith(".") or directory.name == "hacs":
                    continue
                manifest = self._read_json(directory / "manifest.json")
                if not manifest:
                    continue
                self._add_filesystem_item(
                    found,
                    "integration",
                    directory,
                    str(manifest.get("name") or directory.name),
                    version=str(manifest.get("version") or ""),
                    domain=str(manifest.get("domain") or directory.name),
                )

        # Frontend repositories
        root = self.config_root / "www" / "community"
        if root.is_dir():
            for entry in root.iterdir():
                if entry.name.startswith("."):
                    continue
                self._add_filesystem_item(found, "plugin", entry, self._pretty_name(entry.name))

        # Themes (top-level files and folders)
        root = self.config_root / "themes"
        if root.is_dir():
            for entry in root.iterdir():
                if entry.name.startswith(".") or entry.name in IGNORED_NAMES:
                    continue
                if entry.is_dir() or entry.suffix.lower() in {".yaml", ".yml"}:
                    self._add_filesystem_item(found, "theme", entry, self._pretty_name(entry.stem))

        # Python scripts
        root = self.config_root / "python_scripts"
        if root.is_dir():
            for entry in root.glob("*.py"):
                self._add_filesystem_item(
                    found, "python_script", entry, self._pretty_name(entry.stem)
                )

        # Reusable Jinja templates (HACS template repositories)
        root = self.config_root / "custom_templates"
        if root.is_dir():
            for entry in root.glob("*.jinja"):
                self._add_filesystem_item(
                    found, "template", entry, self._pretty_name(entry.stem)
                )

        # AppDaemon apps
        for root in (
            self.config_root / "appdaemon" / "apps",
            self.config_root / "apps",
        ):
            if root.is_dir():
                for entry in root.iterdir():
                    if entry.name.startswith("."):
                        continue
                    self._add_filesystem_item(
                        found, "appdaemon", entry, self._pretty_name(entry.stem)
                    )

        # NetDaemon apps
        root = self.config_root / "netdaemon" / "apps"
        if root.is_dir():
            for entry in root.iterdir():
                if entry.name.startswith("."):
                    continue
                self._add_filesystem_item(
                    found, "netdaemon", entry, self._pretty_name(entry.stem)
                )

    def _add_filesystem_item(
        self,
        found: dict[tuple[str, str], Extension],
        category: str,
        path: Path,
        name: str,
        version: str = "",
        domain: str = "",
    ) -> None:
        try:
            relative = path.resolve().relative_to(self.config_root).as_posix()
        except ValueError:
            return
        key = (category, relative)
        if key in found:
            return
        found[key] = Extension(
            id=self._encode_id(category, relative),
            category=category,
            name=name,
            path=str(path),
            relative_path=relative,
            version=version,
            domain=domain,
            source="filesystem",
        )

    def get_extension(self, extension_id: str) -> Extension:
        category, relative = self._decode_id(extension_id)
        for item in self.scan():
            if item.category == category and item.relative_path == relative:
                return item
        raise ManagerError("Erweiterung wurde nicht gefunden oder bereits entfernt.")

    # ---------- Archive ----------
    def create_archive(self, extension: Extension, target_dir: Path | None = None) -> Path:
        source = Path(extension.path)
        if not source.exists():
            raise ManagerError("Die zu sichernde Erweiterung existiert nicht mehr.")
        target_dir = target_dir or self.archive_root
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().astimezone().strftime("%Y%m%d.%H%M%S")
        safe_name = self._slug(extension.domain or extension.name or source.stem)
        filename = f"{safe_name}_{timestamp}.zip"
        target = target_dir / filename
        metadata = {
            "format": ARCHIVE_FORMAT,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "app_version": APP_VERSION,
            "extension": extension.public(),
            "destination_relative": extension.relative_path,
            "payload_root": "payload",
            "source_type": "directory" if source.is_dir() else "file",
            "source_name": source.name,
            "sha256": self._tree_hash(source),
        }
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr(METADATA_NAME, json.dumps(metadata, ensure_ascii=False, indent=2))
            if source.is_dir():
                for path in self._iter_payload_files(source):
                    relative = path.relative_to(source).as_posix()
                    archive.write(path, f"payload/{relative}")
                # Keep empty directories.
                for directory in self._iter_empty_dirs(source):
                    relative = directory.relative_to(source).as_posix().rstrip("/") + "/"
                    archive.writestr(f"payload/{relative}", b"")
            else:
                archive.write(source, f"payload/{source.name}")
        return target

    def delete_extension(self, extension: Extension) -> dict[str, Any]:
        if extension.protected:
            raise ManagerError("Diese Erweiterung ist geschützt und kann nicht gelöscht werden.")
        path = Path(extension.path)
        if not path.exists():
            raise ManagerError("Die Erweiterung existiert nicht mehr.")

        safety_archive: Path | None = None
        if self.create_safety_backup:
            safety_archive = self.create_archive(extension, self.safety_root)

        warning = ""
        method = "filesystem"
        if (
            self.prefer_hacs_uninstall
            and extension.source == "hacs"
            and extension.repository_id
            and self.ha_client.available
        ):
            try:
                self.ha_client.remove_hacs_repository(extension.repository_id)
                method = "hacs"
            except Exception as exc:
                warning = (
                    "HACS konnte die Erweiterung nicht austragen. "
                    f"Sie wurde deshalb dateibasiert entfernt: {exc}"
                )
                self._remove_path(path, missing_ok=True)
        else:
            self._remove_path(path)

        if path.exists():
            # Some HACS categories report parent paths; ensure the selected target is gone.
            self._remove_path(path)
        return {
            "deleted": True,
            "method": method,
            "warning": warning,
            "safety_archive": str(safety_archive) if safety_archive else "",
        }

    # ---------- Installation ----------
    def install_zip(
        self,
        zip_path: Path,
        original_name: str,
        category_hint: str = "auto",
        overwrite: bool = False,
    ) -> dict[str, Any]:
        if zip_path.stat().st_size > self.max_upload_bytes:
            raise ManagerError("Die ZIP-Datei überschreitet die konfigurierte Maximalgröße.")
        with self._lock, tempfile.TemporaryDirectory(prefix="hacs-ext-") as temp_name:
            temp_root = Path(temp_name)
            extract_root = temp_root / "extracted"
            extract_root.mkdir()
            self._safe_extract(zip_path, extract_root)
            self._cleanup_extracted(extract_root)
            candidate = self._detect_candidate(extract_root, original_name, category_hint)
            destination = self._path_from_relative(candidate.destination_relative)

            previous_backup: Path | None = None
            if destination.exists():
                if not overwrite:
                    raise ManagerError(
                        f"Das Ziel '{candidate.destination_relative}' existiert bereits. "
                        "Aktivieren Sie 'Vorhandene Erweiterung ersetzen'."
                    )
                existing = self._extension_for_destination(candidate, destination)
                previous_backup = self.create_archive(existing, self.safety_root)

            staging = destination.parent / f".{destination.name}.installing-{os.getpid()}"
            rollback = destination.parent / f".{destination.name}.rollback-{os.getpid()}"
            self._remove_path(staging, missing_ok=True)
            self._remove_path(rollback, missing_ok=True)
            destination.parent.mkdir(parents=True, exist_ok=True)

            try:
                self._copy_candidate(candidate, staging)
                self._validate_staged(candidate, staging)
                if destination.exists():
                    destination.rename(rollback)
                staging.rename(destination)
                self._remove_path(rollback, missing_ok=True)
            except Exception:
                self._remove_path(staging, missing_ok=True)
                if rollback.exists() and not destination.exists():
                    rollback.rename(destination)
                raise

            return {
                "installed": True,
                "category": candidate.category,
                "category_label": CATEGORY_LABELS.get(candidate.category, candidate.category),
                "name": candidate.name,
                "version": candidate.version,
                "destination": candidate.destination_relative,
                "replaced": bool(previous_backup),
                "safety_archive": str(previous_backup) if previous_backup else "",
                "hacs_tracking_note": (
                    "Die Dateien wurden lokal installiert. Eine aus einer Sicherung oder fremden ZIP "
                    "installierte Erweiterung wird von HACS nicht automatisch als heruntergeladen markiert."
                ),
            }

    def _detect_candidate(
        self, root: Path, original_name: str, category_hint: str
    ) -> InstallCandidate:
        metadata_file = root / METADATA_NAME
        if metadata_file.is_file():
            metadata = self._read_json(metadata_file)
            if metadata.get("format") != ARCHIVE_FORMAT:
                raise ManagerError("Unbekanntes Sicherungsformat.")
            relative = str(metadata.get("destination_relative") or "").strip()
            if not relative:
                raise ManagerError("Die Sicherung enthält keinen gültigen Zielpfad.")
            extension = metadata.get("extension") or {}
            category = str(extension.get("category") or "unknown")
            if category not in CATEGORY_LABELS:
                raise ManagerError("Die Sicherung enthält eine unbekannte Erweiterungskategorie.")

            payload_value = str(metadata.get("payload_root") or "payload").replace("\\", "/")
            payload_relative = PurePosixPath(payload_value)
            if payload_relative.is_absolute() or ".." in payload_relative.parts:
                raise ManagerError("Die Sicherung enthält einen unsicheren Nutzdatenpfad.")
            payload = (root / Path(*payload_relative.parts)).resolve()
            try:
                payload.relative_to(root.resolve())
            except ValueError as exc:
                raise ManagerError("Die Sicherung enthält einen unsicheren Nutzdatenpfad.") from exc
            if not payload.exists():
                raise ManagerError("Die Sicherung enthält keinen Nutzdatenbereich.")

            source_path = payload
            source_type = str(metadata.get("source_type") or "directory")
            if source_type == "file":
                source_name = str(metadata.get("source_name") or Path(relative).name)
                if not source_name or Path(source_name).name != source_name:
                    raise ManagerError("Die Sicherung enthält einen unsicheren Dateinamen.")
                source_path = payload / source_name
                if not source_path.is_file():
                    raise ManagerError("Die Sicherung enthält die erwartete Datei nicht.")
            elif source_type != "directory" or not source_path.is_dir():
                raise ManagerError("Die Sicherung enthält einen ungültigen Nutzdatentyp.")

            expected_hash = str(metadata.get("sha256") or "")
            if expected_hash and not hmac.compare_digest(expected_hash, self._tree_hash(source_path)):
                raise ManagerError("Die Prüfsumme der Sicherung ist ungültig.")
            return InstallCandidate(
                category=category,
                name=str(extension.get("name") or Path(relative).name),
                source_path=source_path,
                destination_relative=relative,
                version=str(extension.get("version") or ""),
                domain=str(extension.get("domain") or ""),
                archive_metadata=metadata,
            )

        manifests = [
            path
            for path in root.rglob("manifest.json")
            if not any(part in IGNORED_PARTS for part in path.parts)
        ]
        candidates: list[InstallCandidate] = []
        for manifest_path in manifests:
            manifest = self._read_json(manifest_path)
            domain = str(manifest.get("domain") or "").strip()
            if not re.fullmatch(r"[a-z0-9_]+", domain):
                continue
            component_dir = manifest_path.parent
            candidates.append(
                InstallCandidate(
                    category="integration",
                    name=str(manifest.get("name") or domain),
                    source_path=component_dir,
                    destination_relative=f"custom_components/{domain}",
                    version=str(manifest.get("version") or ""),
                    domain=domain,
                )
            )
        # Prefer manifests under custom_components, then shallowest path.
        candidates.sort(
            key=lambda item: (
                0 if "custom_components" in item.source_path.parts else 1,
                len(item.source_path.parts),
            )
        )
        unique = {(c.domain, str(c.source_path)): c for c in candidates}
        if category_hint in {"auto", "integration"} and unique:
            domains = {c.domain for c in unique.values()}
            if len(domains) > 1:
                raise ManagerError(
                    "Die ZIP-Datei enthält mehrere Integrationen. Bitte pro ZIP nur eine Erweiterung verwenden."
                )
            return next(iter(unique.values()))

        effective_root = self._single_content_root(root)
        hint = category_hint
        if hint == "auto":
            hint = self._guess_non_integration_category(effective_root)
        slug = self._slug(Path(original_name).stem)
        if effective_root != root and self._slug(effective_root.name):
            slug = self._slug(effective_root.name)
        if hint == "plugin":
            return InstallCandidate(
                "plugin", self._pretty_name(slug), effective_root, f"www/community/{slug}"
            )
        if hint == "theme":
            # One YAML file can be restored as a file; otherwise use a directory.
            yaml_files = list(effective_root.glob("*.yaml")) + list(effective_root.glob("*.yml"))
            if effective_root == root and len(yaml_files) == 1 and len(list(root.iterdir())) == 1:
                source = yaml_files[0]
                return InstallCandidate(
                    "theme", self._pretty_name(source.stem), source, f"themes/{source.name}"
                )
            return InstallCandidate(
                "theme", self._pretty_name(slug), effective_root, f"themes/{slug}"
            )
        if hint == "python_script":
            py_files = list(effective_root.rglob("*.py"))
            if len(py_files) != 1:
                raise ManagerError("Für ein Python-Skript muss die ZIP genau eine .py-Datei enthalten.")
            source = py_files[0]
            return InstallCandidate(
                "python_script",
                self._pretty_name(source.stem),
                source,
                f"python_scripts/{source.name}",
            )
        if hint == "appdaemon":
            return InstallCandidate(
                "appdaemon",
                self._pretty_name(slug),
                effective_root,
                f"appdaemon/apps/{slug}",
            )
        if hint == "netdaemon":
            return InstallCandidate(
                "netdaemon",
                self._pretty_name(slug),
                effective_root,
                f"netdaemon/apps/{slug}",
            )
        if hint == "template":
            files = [p for p in effective_root.rglob("*") if p.is_file()]
            if len(files) != 1:
                raise ManagerError("Für ein Template muss die ZIP genau eine Datei enthalten.")
            source = files[0]
            if source.suffix.lower() != ".jinja":
                raise ManagerError("Ein HACS-Template muss eine .jinja-Datei enthalten.")
            return InstallCandidate(
                "template",
                self._pretty_name(source.stem),
                source,
                f"custom_templates/{source.name}",
            )
        raise ManagerError(
            "Der Erweiterungstyp konnte nicht eindeutig erkannt werden. Wählen Sie den Typ manuell aus."
        )

    def _guess_non_integration_category(self, root: Path) -> str:
        files = [path for path in root.rglob("*") if path.is_file()]
        suffixes = {path.suffix.lower() for path in files}
        if suffixes & {".js", ".mjs"}:
            return "plugin"
        if files and suffixes <= {".yaml", ".yml", ".jpg", ".jpeg", ".png", ".webp", ".svg"}:
            return "theme"
        if len(files) == 1 and files[0].suffix.lower() == ".py":
            return "python_script"
        return "unknown"

    def _copy_candidate(self, candidate: InstallCandidate, staging: Path) -> None:
        source = candidate.source_path
        if source.is_dir():
            shutil.copytree(source, staging, ignore=self._copy_ignore)
        else:
            staging.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, staging)

    def _validate_staged(self, candidate: InstallCandidate, staging: Path) -> None:
        if candidate.category == "integration":
            manifest_path = staging / "manifest.json"
            manifest = self._read_json(manifest_path)
            if not manifest:
                raise ManagerError("Die Integration enthält keine gültige manifest.json.")
            if str(manifest.get("domain") or "") != candidate.domain:
                raise ManagerError("Die Domain der Integration stimmt nach dem Kopieren nicht überein.")
            if not (staging / "__init__.py").exists():
                raise ManagerError("Die Integration enthält keine __init__.py.")
        if not staging.exists():
            raise ManagerError("Die Erweiterung konnte nicht in den Zielbereich kopiert werden.")

    def _extension_for_destination(
        self, candidate: InstallCandidate, destination: Path
    ) -> Extension:
        relative = destination.resolve().relative_to(self.config_root).as_posix()
        return Extension(
            id=self._encode_id(candidate.category, relative),
            category=candidate.category,
            name=candidate.name,
            path=str(destination),
            relative_path=relative,
            version=candidate.version,
            domain=candidate.domain,
            source="filesystem",
        )

    # ---------- ZIP safety ----------
    def _safe_extract(self, zip_path: Path, destination: Path) -> None:
        if not zipfile.is_zipfile(zip_path):
            raise ManagerError("Die hochgeladene Datei ist keine gültige ZIP-Datei.")
        total_size = 0
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.infolist()
            if not members:
                raise ManagerError("Die ZIP-Datei ist leer.")
            for member in members:
                posix = PurePosixPath(member.filename.replace("\\", "/"))
                if posix.is_absolute() or ".." in posix.parts:
                    raise ManagerError("Die ZIP-Datei enthält einen unsicheren Pfad.")
                if not posix.parts:
                    continue
                mode = (member.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise ManagerError("Symbolische Links in ZIP-Dateien sind nicht erlaubt.")
                total_size += member.file_size
                if total_size > self.max_uncompressed_bytes:
                    raise ManagerError("Die entpackten Daten überschreiten das Sicherheitslimit.")
                if member.compress_size > 0 and member.file_size / member.compress_size > 250:
                    raise ManagerError("Die ZIP-Datei weist ein verdächtiges Kompressionsverhältnis auf.")
            for member in members:
                archive.extract(member, destination)

    def _cleanup_extracted(self, root: Path) -> None:
        for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.name in IGNORED_NAMES or any(part in IGNORED_PARTS for part in path.parts):
                self._remove_path(path, missing_ok=True)

    # ---------- Helpers ----------
    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return {}

    @staticmethod
    def _pretty_name(value: str) -> str:
        return value.replace("-", " ").replace("_", " ").strip().title()

    @staticmethod
    def _slug(value: str) -> str:
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9._-]+", "_", value)
        value = re.sub(r"_+", "_", value).strip("._-")
        return value or "extension"

    @staticmethod
    def _modified_iso(path: Path) -> str:
        try:
            return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        except OSError:
            return ""

    @staticmethod
    def _path_size(path: Path) -> int:
        try:
            if path.is_file():
                return path.stat().st_size
            return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
        except OSError:
            return 0

    @staticmethod
    def _remove_path(path: Path, missing_ok: bool = False) -> None:
        if not path.exists() and not path.is_symlink():
            if missing_ok:
                return
            raise ManagerError(f"Pfad existiert nicht: {path}")
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=missing_ok)

    @staticmethod
    def _iter_payload_files(root: Path) -> Iterable[Path]:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.name in IGNORED_NAMES or any(part in IGNORED_PARTS for part in path.parts):
                continue
            yield path

    @staticmethod
    def _iter_empty_dirs(root: Path) -> Iterable[Path]:
        for path in root.rglob("*"):
            if path.is_dir() and not any(path.iterdir()):
                yield path

    @staticmethod
    def _copy_ignore(directory: str, names: list[str]) -> set[str]:
        ignored = set()
        for name in names:
            if name in IGNORED_NAMES or name in IGNORED_PARTS:
                ignored.add(name)
        return ignored

    @staticmethod
    def _tree_hash(path: Path) -> str:
        digest = hashlib.sha256()
        if path.is_file():
            digest.update(path.name.encode())
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        for file in sorted(p for p in path.rglob("*") if p.is_file()):
            if file.name in IGNORED_NAMES or any(part in IGNORED_PARTS for part in file.parts):
                continue
            digest.update(file.relative_to(path).as_posix().encode())
            with file.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _single_content_root(root: Path) -> Path:
        entries = [p for p in root.iterdir() if p.name not in IGNORED_NAMES]
        if len(entries) == 1 and entries[0].is_dir():
            return entries[0]
        return root
