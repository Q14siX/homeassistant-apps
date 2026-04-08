#!/bin/sh
set -eu

log() {
    printf '%s\n' "[gotify-homeassistant-app] $*"
}

log "Preparing Gotify configuration"

RESOLVED_TIMEZONE="$(python3 - <<'PY'
import json
import os
import urllib.request
from pathlib import Path


def load_options():
    path = Path('/data/options.json')
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def section(options, name):
    value = options.get(name, {})
    return value if isinstance(value, dict) else {}


def as_bool(value, default):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {'1', 'true', 'yes', 'on'}:
            return True
        if lowered in {'0', 'false', 'no', 'off'}:
            return False
    return bool(value)


def as_str(value, default=''):
    if value is None:
        return default
    return str(value)


def fetch_supervisor_timezone():
    token = os.environ.get('SUPERVISOR_TOKEN', '').strip()
    if not token:
        return ''
    req = urllib.request.Request(
        'http://supervisor/info',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = json.load(response)
    except Exception:
        return ''

    if isinstance(payload, dict):
        data = payload.get('data')
        if isinstance(data, dict):
            return as_str(data.get('timezone'), '').strip()
        return as_str(payload.get('timezone'), '').strip()
    return ''


options = load_options()
general = section(options, 'general')

use_homeassistant_timezone = as_bool(general.get('use_homeassistant_timezone'), True)
timezone_override = as_str(
    general.get('timezone_override', general.get('timezone', options.get('timezone'))),
    '',
).strip()

if timezone_override:
    print(timezone_override)
elif use_homeassistant_timezone:
    print(fetch_supervisor_timezone() or 'Etc/UTC')
else:
    print('Etc/UTC')
PY
)"

if [ -n "$RESOLVED_TIMEZONE" ]; then
    export TZ="$RESOLVED_TIMEZONE"
    log "Using timezone: $TZ"
fi

python3 - <<'PY'
import json
from pathlib import Path

OPTIONS_PATH = Path('/data/options.json')
CONFIG_PATH = Path('/app/config.yml')

if OPTIONS_PATH.exists():
    options = json.loads(OPTIONS_PATH.read_text(encoding='utf-8'))
else:
    options = {}


def section(name, default):
    value = options.get(name, default)
    return value if isinstance(value, dict) else default


def list_value(value):
    return value if isinstance(value, list) else []


def response_headers_from_list(entries):
    headers = {}
    for entry in list_value(entries):
        if entry is None:
            continue
        text = str(entry).strip()
        if not text or ':' not in text:
            continue
        name, value = text.split(':', 1)
        name = name.strip()
        value = value.strip()
        if name:
            headers[name] = value
    return headers


def dump_scalar(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def emit(value, indent=0):
    lines = []
    prefix = ' ' * indent
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, dict):
                if not item:
                    lines.append(f"{prefix}{key}: {{}}")
                else:
                    lines.append(f"{prefix}{key}:")
                    lines.extend(emit(item, indent + 2))
            elif isinstance(item, list):
                if not item:
                    lines.append(f"{prefix}{key}: []")
                else:
                    lines.append(f"{prefix}{key}:")
                    for entry in item:
                        if isinstance(entry, (dict, list)):
                            raise ValueError('Nested complex list values are not supported in this config writer')
                        lines.append(f"{' ' * (indent + 2)}- {dump_scalar(entry)}")
            else:
                lines.append(f"{prefix}{key}: {dump_scalar(item)}")
    else:
        raise TypeError('Top-level YAML document must be a dictionary')
    return lines


def as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_bool(value, default):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {'1', 'true', 'yes', 'on'}:
            return True
        if lowered in {'0', 'false', 'no', 'off'}:
            return False
    return bool(value)


def as_str(value, default=''):
    if value is None:
        return default
    return str(value)


general = section('general', {})
database = section('database', {})
security = section('security', {})
defaultuser = section('defaultuser', {})
advanced = section('advanced', {})

# Backward compatibility with older package layouts.
headers = section('headers', {})
stream = section('stream', {})
cors = section('cors', {})
server = section('server', {})
storage = section('storage', {})
legacy_advanced = section('advanced_legacy', {})

registration = as_bool(general.get('registration', options.get('registration')), False)
keepalive = as_int(
    advanced.get('keepaliveperiodseconds', server.get('keepaliveperiodseconds', legacy_advanced.get('keepaliveperiodseconds'))),
    0,
)
listenaddr = as_str(
    advanced.get('listenaddr', server.get('listenaddr', legacy_advanced.get('listenaddr'))),
    '',
)
uploaded_images_dir = as_str(
    advanced.get('uploadedimagesdir', storage.get('uploadedimagesdir', legacy_advanced.get('uploadedimagesdir'))),
    '/data/images',
) or '/data/images'
plugins_dir = as_str(
    advanced.get('pluginsdir', storage.get('pluginsdir', legacy_advanced.get('pluginsdir'))),
    '/data/plugins',
)
responseheaders = advanced.get('responseheaders', headers.get('responseheaders'))
pingperiodseconds = advanced.get('pingperiodseconds', stream.get('pingperiodseconds'))
stream_allowedorigins = advanced.get('streamallowedorigins', stream.get('allowedorigins', stream.get('allowedorigins')))
cors_alloworigins = advanced.get('corsalloworigins', cors.get('alloworigins'))
cors_allowmethods = advanced.get('corsallowmethods', cors.get('allowmethods'))
cors_allowheaders = advanced.get('corsallowheaders', cors.get('allowheaders'))

gotify_config = {
    'server': {
        'keepaliveperiodseconds': keepalive,
        'listenaddr': listenaddr,
        'port': 80,
        'trustedproxies': list_value(security.get('trustedproxies')),
        'responseheaders': response_headers_from_list(responseheaders),
        'cors': {
            'alloworigins': list_value(cors_alloworigins),
            'allowmethods': list_value(cors_allowmethods),
            'allowheaders': list_value(cors_allowheaders),
        },
        'stream': {
            'pingperiodseconds': as_int(pingperiodseconds, 45),
            'allowedorigins': list_value(stream_allowedorigins),
        },
    },
    'database': {
        'dialect': as_str(database.get('dialect'), 'sqlite3') or 'sqlite3',
        'connection': as_str(database.get('connection'), '/data/gotify.db') or '/data/gotify.db',
    },
    'defaultuser': {
        'name': as_str(defaultuser.get('name'), 'admin') or 'admin',
        'pass': as_str(defaultuser.get('pass'), 'admin') or 'admin',
    },
    'passstrength': as_int(security.get('passstrength'), 10),
    'uploadedimagesdir': uploaded_images_dir,
    'pluginsdir': plugins_dir,
    'registration': registration,
}

CONFIG_PATH.write_text('\n'.join(emit(gotify_config)) + '\n', encoding='utf-8')

if gotify_config['database']['dialect'] == 'sqlite3':
    Path(gotify_config['database']['connection']).parent.mkdir(parents=True, exist_ok=True)
Path(uploaded_images_dir).mkdir(parents=True, exist_ok=True)
if plugins_dir:
    Path(plugins_dir).mkdir(parents=True, exist_ok=True)
PY

log "Starting Gotify"
exec /app/gotify-app
