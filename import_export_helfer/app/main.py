import os
import json
import glob
import zipfile
import io
import time
import threading
import uuid
from flask import Flask, jsonify, request, send_file, render_template
from ruamel.yaml import YAML
import logging
app = Flask(__name__)
yaml = YAML()
yaml.preserve_quotes = True
yaml.width = 1024
logging.basicConfig(level=logging.INFO)
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(logging.INFO)
CONFIG_PATH = '/config'
STORAGE_PATH = os.path.join(CONFIG_PATH, '.storage')
FILE_LOCKS = {
    'core.entity_registry': threading.Lock(),
    'core.config_entries': threading.Lock(),
    'core.automation': threading.Lock(),
    'core.script': threading.Lock(),
    'core.scene': threading.Lock(),
    'automations.yaml': threading.Lock(),
    'scripts.yaml': threading.Lock(),
    'scenes.yaml': threading.Lock(),
    'generic_yaml': threading.Lock(),
    'generic_helper': threading.Lock(),
}
HELPER_PLATFORMS = [
    'input_boolean', 'input_text', 'input_number', 'input_datetime', 
    'input_select', 'input_button',
    'timer', 'counter', 'schedule', 'random', 
    'derivative', 'group', 'integration', 'min_max',
    'template', 'threshold', 'utility_meter'
]
INTEGRATION_HELPER_PLATFORMS = [
    'derivative', 'integration', 'min_max', 'template',
    'threshold', 'utility_meter', 'random'
]
LEGACY_HELPER_PLATFORMS = [p for p in HELPER_PLATFORMS if p not in INTEGRATION_HELPER_PLATFORMS]
for platform in LEGACY_HELPER_PLATFORMS:
    FILE_LOCKS[platform] = threading.Lock()
STORAGE_FILES_MAP = {
    'Automation': {
        'file_key': 'core.automation',
        'storage_key': 'automation',
        'is_dict': True
    },
    'Skript': {
        'file_key': 'core.script',
        'storage_key': 'items',
        'is_dict': False
    },
    'Szene': {
        'file_key': 'core.scene',
        'storage_key': 'items',
        'is_dict': False
    }
}
YAML_LIST_MAP = {
    'Automation (YAML)': {
        'file': 'automations.yaml',
        'name_key': 'alias'
    },
    'Skript (YAML)': {
        'file': 'scripts.yaml',
        'name_key': 'alias' 
    },
    'Szene (YAML)': {
        'file': 'scenes.yaml',
        'name_key': 'name'
    }
}
def load_json(filepath):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        app.logger.error(f"Fehler beim Laden von JSON {filepath}: {e}")
    return None
def save_json(filepath, data):
    tmp_path = f"{filepath}.tmp"
    bak_path = f"{filepath}.bak"
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        if os.path.exists(filepath):
            os.rename(filepath, bak_path)
        os.rename(tmp_path, filepath)
        if os.path.exists(bak_path):
            os.remove(bak_path)
        return True
    except Exception as e:
        app.logger.error(f"Fehler beim Speichern von JSON {filepath}: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if os.path.exists(bak_path) and not os.path.exists(filepath):
            os.rename(bak_path, filepath)
        return False
def load_yaml(filepath):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return yaml.load(f)
    except Exception as e:
        app.logger.error(f"Fehler beim Laden von YAML {filepath}: {e}")
    return None
def save_yaml(filepath, data):
    tmp_path = f"{filepath}.tmp"
    bak_path = f"{filepath}.bak"
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)
        if os.path.exists(filepath):
            os.rename(filepath, bak_path)
        os.rename(tmp_path, filepath)
        if os.path.exists(bak_path):
            os.remove(bak_path)
        return True
    except Exception as e:
        app.logger.error(f"Fehler beim Speichern von YAML {filepath}: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if os.path.exists(bak_path) and not os.path.exists(filepath):
            os.rename(bak_path, filepath)
        return False
def load_yaml_from_string(yaml_string):
    try:
        return yaml.load(yaml_string)
    except Exception as e:
        app.logger.error(f"Fehler beim Parsen von YAML-String: {e}")
    return None
def scan_yaml_list_file(items, item_type, file_path, name_key, item_ids_set=None):
    data = load_yaml(file_path)
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                item_id = entry.get('id')
                name = entry.get(name_key)
                if item_id:
                    full_id = f"{item_type}::{item_id}"
                    items.append({
                        'id': full_id,
                        'name': name or f"Eintrag (ID: {item_id})",
                        'type': item_type,
                        'source': os.path.basename(file_path)
                    })
                    if item_ids_set is not None:
                        item_ids_set.add(full_id)
    elif isinstance(data, dict):
        for item_id, entry in data.items():
            if isinstance(entry, dict):
                name = entry.get(name_key)
                full_id = f"{item_type}::{item_id}"
                items.append({
                    'id': full_id,
                    'name': name or item_id,
                    'type': item_type,
                    'source': os.path.basename(file_path)
                })
                if item_ids_set is not None:
                    item_ids_set.add(full_id)
def get_items(include_ids_set=False):
    items = []
    item_ids_set = set() if include_ids_set else None
    try:
        excluded_yaml_files = [YAML_LIST_MAP[key]['file'] for key in YAML_LIST_MAP]
        yaml_files = glob.glob(os.path.join(CONFIG_PATH, '**/*.yaml'), recursive=True)
        for yf in yaml_files:
            rel_path = os.path.relpath(yf, CONFIG_PATH)
            if rel_path in excluded_yaml_files or 'secrets.yaml' in rel_path or \
               rel_path.startswith('.storage') or rel_path.startswith('blueprints'):
                continue
            file_name = os.path.basename(rel_path)
            dir_name = os.path.dirname(rel_path)
            source_display = 'config/'
            if dir_name and dir_name != '.':
                source_display = f"config/{dir_name}/"
            full_id = f"YAML-Datei::{rel_path}"
            items.append({'id': full_id, 'name': file_name, 'type': 'YAML-Datei', 'source': source_display})
            if item_ids_set is not None:
                item_ids_set.add(full_id)
    except Exception as e:
        app.logger.error(f"Fehler beim Scannen der YAML-Dateien: {e}")
    try:
        for platform in LEGACY_HELPER_PLATFORMS:
            helper_file_path = os.path.join(STORAGE_PATH, platform)
            helper_data = load_json(helper_file_path)
            if helper_data and 'data' in helper_data and 'items' in helper_data['data']:
                for item in helper_data['data']['items']:
                    item_id = item.get('id')
                    if item_id:
                        full_id = f"Helfer::{platform}::{item_id}"
                        items.append({
                            'id': full_id,
                            'name': item.get('name'),
                            'type': 'Helfer',
                            'source': f".storage/{platform}"
                        })
                        if item_ids_set is not None: item_ids_set.add(full_id)
    except Exception as e:
        app.logger.error(f"Fehler beim Scannen der Legacy-Helfer: {e}")
    try:
        config_entries = load_json(os.path.join(STORAGE_PATH, 'core.config_entries'))
        if config_entries and 'data' in config_entries and 'entries' in config_entries['data']:
            for entry in config_entries['data']['entries']:
                domain = entry.get('domain')
                if domain in INTEGRATION_HELPER_PLATFORMS:
                    entry_id = entry.get('entry_id')
                    if entry_id:
                        full_id = f"Helfer::{domain}::{entry_id}"
                        items.append({
                            'id': full_id,
                            'name': entry.get('title'),
                            'type': 'Helfer',
                            'source': 'core.config_entries'
                        })
                        if item_ids_set is not None: item_ids_set.add(full_id)
    except Exception as e:
        app.logger.error(f"Fehler beim Scannen der Integrations-Helfer: {e}")
    try:
        for item_type, config in STORAGE_FILES_MAP.items():
            storage_file_key = config['file_key']
            storage_data_key = config['storage_key']
            storage_file_path = os.path.join(STORAGE_PATH, storage_file_key)
            storage_file = load_json(storage_file_path)
            if storage_file and 'data' in storage_file and storage_data_key in storage_file['data']:
                data_list = storage_file['data'][storage_data_key]
                data_source = []
                if isinstance(data_list, dict): data_source = data_list.values()
                elif isinstance(data_list, list): data_source = data_list
                for entry in data_source:
                    if entry.get('id'):
                        full_id = f"{item_type}::{entry.get('id')}"
                        items.append({
                            'id': full_id,
                            'name': entry.get('alias') or entry.get('name'),
                            'type': item_type, 
                            'source': f"{storage_file_key}"
                        })
                        if item_ids_set is not None:
                            item_ids_set.add(full_id)
    except Exception as e:
        app.logger.error(f"Fehler beim Scannen der Storage-Dateien: {e}")
    try:
        for item_type, config in YAML_LIST_MAP.items():
            file_path = os.path.join(CONFIG_PATH, config['file'])
            if os.path.exists(file_path):
                scan_yaml_list_file(items, item_type, file_path, config['name_key'], item_ids_set)
    except Exception as e:
        app.logger.error(f"Fehler beim Scannen der YAML-Listen-Dateien: {e}")
    try:
        blueprint_paths = [
            os.path.join(CONFIG_PATH, 'blueprints/automation'),
            os.path.join(CONFIG_PATH, 'blueprints/script')
        ]
        for bp_path in blueprint_paths:
            if os.path.exists(bp_path):
                yaml_files = glob.glob(os.path.join(bp_path, '**/*.yaml'), recursive=True)
                for yf in yaml_files:
                    rel_path = os.path.relpath(yf, CONFIG_PATH)
                    data = load_yaml(yf)
                    blueprint_name = None
                    if isinstance(data, dict):
                        blueprint_name = data.get('blueprint', {}).get('name')
                    full_id = f"Blueprint::{rel_path}"
                    items.append({
                        'id': full_id,
                        'name': blueprint_name or os.path.basename(yf),
                        'type': 'Blueprint',
                        'source': rel_path
                    })
                    if item_ids_set is not None:
                        item_ids_set.add(full_id)
    except Exception as e:
        app.logger.error(f"Fehler beim Scannen der Blueprints: {e}")
    app.logger.info(f"{len(items)} Elemente gefunden.")
    if include_ids_set:
        return items, item_ids_set
    return items
def get_existing_item_ids():
    _, item_ids_set = get_items(include_ids_set=True)
    return item_ids_set
def get_legacy_helper_by_id(platform, item_id):
    filepath = os.path.join(STORAGE_PATH, platform)
    data = load_json(filepath)
    if data and 'data' in data and 'items' in data['data']:
        for item in data['data']['items']:
            if item.get('id') == item_id:
                return item
    return None
def get_config_entry_by_id(entry_id):
    filepath = os.path.join(STORAGE_PATH, 'core.config_entries')
    data = load_json(filepath)
    if data and 'data' in data and 'entries' in data['data']:
        for entry in data['data']['entries']:
            if entry.get('entry_id') == entry_id:
                return entry
    return None
def get_storage_item_by_id(item_type, item_id):
    config = STORAGE_FILES_MAP.get(item_type)
    if not config: return None
    storage_file_key = config['file_key']
    storage_data_key = config['storage_key']
    storage_file_path = os.path.join(STORAGE_PATH, storage_file_key)
    storage_file = load_json(storage_file_path)
    if storage_file and 'data' in storage_file and storage_data_key in storage_file['data']:
        data_list = storage_file['data'][storage_data_key]
        if isinstance(data_list, dict): return data_list.get(item_id)
        elif isinstance(data_list, list):
            for entry in data_list:
                if entry.get('id') == item_id:
                    return entry
    return None
def get_yaml_list_item_by_id(item_type, item_id):
    config = YAML_LIST_MAP.get(item_type)
    if not config: return None
    file_path = os.path.join(CONFIG_PATH, config['file'])
    data = load_yaml(file_path)
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict) and entry.get('id') == item_id:
                return entry
    elif isinstance(data, dict):
        return data.get(item_id)
    return None
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/api/items')
def api_get_items():
    try:
        items = get_items()
        return jsonify(items)
    except Exception as e:
        app.logger.error(f"API Fehler /api/items: {e}")
        return jsonify({"error": "Elemente konnten nicht geladen werden"}), 500
@app.route('/api/export', methods=['POST'])
def api_export_items():
    try:
        data = request.get_json()
        item_ids = data.get('item_ids', [])
        memory_file = io.BytesIO()
        manifest = []
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for full_id in item_ids:
                try:
                    item_type, item_key = full_id.split('::', 1)
                    if item_type == 'YAML-Datei':
                        file_path = os.path.join(CONFIG_PATH, item_key)
                        if os.path.exists(file_path):
                            zf.write(file_path, arcname=f"yaml/{item_key}")
                            manifest.append({'id': full_id, 'type': 'yaml', 'zip_path': f"yaml/{item_key}", 'restore_path': item_key, 'name': os.path.basename(item_key)})
                    elif item_type == 'Blueprint':
                        file_path = os.path.join(CONFIG_PATH, item_key)
                        if os.path.exists(file_path):
                            zf.write(file_path, arcname=f"blueprint/{item_key}")
                            manifest.append({'id': full_id, 'type': 'blueprint', 'zip_path': f"blueprint/{item_key}", 'restore_path': item_key, 'name': os.path.basename(item_key)})
                    elif item_type == 'Helfer':
                        platform, item_id = item_key.split('::', 1)
                        config_data = None
                        manifest_type = ''
                        if platform in INTEGRATION_HELPER_PLATFORMS:
                            config_data = get_config_entry_by_id(item_id)
                            manifest_type = 'helper_integration'
                        else:
                            config_data = get_legacy_helper_by_id(platform, item_id)
                            manifest_type = 'helper_legacy'
                        if config_data:
                            filename = f"helper/{platform}_{item_id}.json"
                            zf.writestr(filename, json.dumps(config_data, indent=2))
                            manifest.append({
                                'id': full_id, 
                                'type': manifest_type, 
                                'platform': platform,
                                'item_id': item_id,
                                'zip_path': filename, 
                                'name': config_data.get('name') or config_data.get('title')
                            })
                    elif item_type in STORAGE_FILES_MAP:
                        storage_item = get_storage_item_by_id(item_type, item_key)
                        if storage_item:
                            filename = f"storage_item/{item_type.lower()}_{item_key}.json"
                            zf.writestr(filename, json.dumps(storage_item, indent=2))
                            manifest.append({'id': full_id, 'type': 'storage_item', 'storage_key': STORAGE_FILES_MAP[item_type]['file_key'], 'item_id': item_key, 'zip_path': filename, 'name': storage_item.get('alias') or storage_item.get('name')})
                    elif item_type in YAML_LIST_MAP:
                        yaml_item = get_yaml_list_item_by_id(item_type, item_key)
                        if yaml_item:
                            clean_type = item_type.lower().replace(' (yaml)', '').replace(' ', '_')
                            filename = f"yaml_item/{clean_type}_{item_key}.yaml"
                            string_stream = io.StringIO()
                            yaml.dump(yaml_item, string_stream)
                            zf.writestr(filename, string_stream.getvalue())
                            manifest.append({'id': full_id, 'type': 'yaml_item', 'yaml_list_file': YAML_LIST_MAP[item_type]['file'], 'item_id': item_key, 'zip_path': filename, 'name': yaml_item.get('alias') or yaml_item.get('name') or item_key})
                except Exception as e:
                    app.logger.warning(f"Konnte Item {full_id} nicht exportieren: {e}")
            zf.writestr('export_manifest.json', json.dumps(manifest, indent=2))
        memory_file.seek(0)
        hostname = "Backup"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        download_name = f"{hostname}_{timestamp}.zip"
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=download_name
        )
    except Exception as e:
        app.logger.error(f"API Fehler /api/export: {e}")
        return jsonify({"error": f"Export fehlgeschlagen: {e}"}), 500
@app.route('/api/analyze_import', methods=['POST'])
def api_analyze_import():
    app.logger.info("Import-Analyse gestartet")
    if 'file' not in request.files:
        return jsonify({"error": "Keine Datei im Request"}), 400
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.zip'):
        return jsonify({"error": "Ungültige Datei (nur .zip erlaubt)"}), 400
    try:
        existing_item_ids = get_existing_item_ids()
        analysis_results = []
        with zipfile.ZipFile(file, 'r') as zf:
            if 'export_manifest.json' not in zf.namelist():
                return jsonify({"error": "ZIP-Datei ist kein gültiges Backup (manifest.json fehlt)"}), 400
            manifest_data = zf.read('export_manifest.json')
            manifest = json.loads(manifest_data)
            for item in manifest:
                item_id = item['id']
                status = "conflict" if item_id in existing_item_ids else "new"
                item_name = item.get('name')
                display_type = item_id.split('::')[0]
                zip_path = item['zip_path']
                if not item_name:
                    try:
                        item_data_str = zf.read(zip_path).decode('utf-8')
                        item_data = None
                        item_type_internal = item.get('type')
                        if zip_path.endswith('.json'):
                            item_data = json.loads(item_data_str)
                        elif zip_path.endswith('.yaml'):
                            item_data = load_yaml_from_string(item_data_str)
                        if item_type_internal == 'helper_legacy':
                            item_name = item_data.get('name')
                            display_type = "Helfer"
                        elif item_type_internal == 'helper_integration':
                            item_name = item_data.get('title')
                            display_type = "Helfer"
                        elif item_type_internal == 'storage_item':
                            item_name = item_data.get('alias') or item_data.get('name')
                        elif item_type_internal == 'yaml_item':
                            item_name = item_data.get('alias') or item_data.get('name') or item.get('item_id')
                        elif item_type_internal == 'yaml':
                            item_name = os.path.basename(item.get('restore_path', 'N/A'))
                            display_type = "YAML-Datei"
                        elif item_type_internal == 'blueprint':
                            if item_data:
                                item_name = item_data.get('blueprint', {}).get('name') or os.path.basename(item.get('restore_path', 'N/A'))
                            else:
                                item_name = os.path.basename(item.get('restore_path', 'N/A'))
                            display_type = "Blueprint"
                        else:
                            item_name = 'N/A'
                    except Exception as e:
                        app.logger.warning(f"Konnte Fallback-Namen für {item_id} nicht lesen: {e}")
                        item_name = 'N/A (Lese-Fehler)'
                analysis_results.append({
                    'id': item_id,
                    'name': item_name or 'N/A',
                    'type': display_type,
                    'status': status,
                    'zip_path': item['zip_path']
                })
        app.logger.info(f"Analyse abgeschlossen. {len(analysis_results)} Elemente gefunden.")
        return jsonify(analysis_results)
    except zipfile.BadZipFile:
        return jsonify({"error": "Ungültige ZIP-Datei"}), 400
    except Exception as e:
        app.logger.error(f"API Fehler /api/analyze_import: {e}")
        return jsonify({"error": f"Import-Analyse fehlgeschlagen: {e}"}), 500
def execute_import_decision(manifest_item, item_data, decision, zf):
    action = decision['action']
    item_type_internal = manifest_item['type']
    if item_type_internal == 'yaml':
        restore_path = os.path.join(CONFIG_PATH, manifest_item['restore_path'])
        if action == 'overwrite':
            with FILE_LOCKS['generic_yaml']:
                os.makedirs(os.path.dirname(restore_path), exist_ok=True)
                with open(restore_path, 'w', encoding='utf-8') as f:
                    f.write(item_data)
            return f"'{restore_path}' überschrieben."
        elif action == 'rename':
            new_path = os.path.join(os.path.dirname(restore_path), decision['new_name'])
            with FILE_LOCKS['generic_yaml']:
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write(item_data)
            return f"Als '{new_path}' gespeichert."
    elif item_type_internal == 'blueprint':
        restore_path = os.path.join(CONFIG_PATH, manifest_item['restore_path'])
        if action == 'overwrite':
            with FILE_LOCKS['generic_yaml']:
                os.makedirs(os.path.dirname(restore_path), exist_ok=True)
                with open(restore_path, 'w', encoding='utf-8') as f:
                    f.write(item_data)
            return f"'{restore_path}' überschrieben."
        elif action == 'rename':
            new_display_name = decision['new_name']
            new_filename = new_display_name.lower().replace(' ', '_').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
            new_filename = "".join(c for c in new_filename if c.isalnum() or c == '_') + '.yaml'
            new_path = os.path.join(os.path.dirname(restore_path), new_filename)
            data = load_yaml_from_string(item_data)
            if not isinstance(data, dict) or 'blueprint' not in data:
                raise Exception("Blueprint-Datei hat ein ungültiges Format.")
            data['blueprint']['name'] = new_display_name
            string_stream = io.StringIO()
            yaml.dump(data, string_stream)
            new_item_data_str = string_stream.getvalue()
            with FILE_LOCKS['generic_yaml']:
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write(new_item_data_str)
            return f"Blueprint als '{new_display_name}' in '{new_path}' gespeichert."
    elif item_type_internal == 'helper_legacy':
        platform = manifest_item['platform']
        item_id = manifest_item['item_id']
        filepath = os.path.join(STORAGE_PATH, platform)
        lock = FILE_LOCKS.get(platform, FILE_LOCKS['generic_helper'])
        with lock:
            helper_storage = load_json(filepath) or {'data': {'items': []}}
            items = helper_storage['data']['items']
            if action == 'overwrite':
                found = False
                for i, item in enumerate(items):
                    if item.get('id') == item_id:
                        items[i] = item_data
                        found = True
                        break
                if not found:
                    items.append(item_data)
                save_json(filepath, helper_storage)
                return f"Helfer '{item_data.get('name')}' in {platform} überschrieben."
            elif action == 'rename':
                new_id = str(uuid.uuid4())
                item_data['id'] = new_id
                item_data['name'] = decision['new_name']
                items.append(item_data)
                save_json(filepath, helper_storage)
                return f"Helfer als '{decision['new_name']}' in {platform} importiert."
    elif item_type_internal == 'helper_integration':
        entry_id = manifest_item['item_id']
        filepath = os.path.join(STORAGE_PATH, 'core.config_entries')
        with FILE_LOCKS['core.config_entries']:
            config_entries = load_json(filepath) or {'data': {'entries': []}}
            entries = config_entries['data']['entries']
            if action == 'overwrite':
                found = False
                for i, entry in enumerate(entries):
                    if entry.get('entry_id') == entry_id:
                        entries[i] = item_data
                        found = True
                        break
                if not found:
                    entries.append(item_data)
                save_json(filepath, config_entries)
                return f"Helfer '{item_data.get('title')}' in core.config_entries überschrieben."
            elif action == 'rename':
                new_entry_id = str(uuid.uuid4()).replace('-', '')
                new_name = decision['new_name']
                item_data['entry_id'] = new_entry_id
                item_data['title'] = new_name
                if 'options' in item_data and 'name' in item_data['options']:
                    item_data['options']['name'] = new_name
                if 'unique_id' in item_data and item_data['unique_id'] is not None:
                     item_data['unique_id'] = new_entry_id
                entries.append(item_data)
                save_json(filepath, config_entries)
                return f"Helfer als '{new_name}' in core.config_entries importiert."
    elif item_type_internal == 'storage_item':
        storage_key = manifest_item['storage_key']
        config = STORAGE_FILES_MAP.get(manifest_item['id'].split('::')[0])
        if not config: raise Exception(f"Unbekannter Storage-Typ: {manifest_item['id']}")
        file_key = config['file_key']
        is_dict = config['is_dict']
        storage_path = os.path.join(STORAGE_PATH, file_key)
        with FILE_LOCKS[file_key]:
            storage_file = load_json(storage_path) or {'data': {config['storage_key']: [] if not is_dict else {}}}
            if is_dict:
                storage_data = storage_file['data'][config['storage_key']]
                if action == 'overwrite':
                    storage_data[manifest_item['item_id']] = item_data
                    save_json(storage_path, storage_file)
                    return f"Eintrag '{item_data.get('alias')}' in {file_key} überschrieben."
                elif action == 'rename':
                    new_id = str(uuid.uuid4())
                    item_data['id'] = new_id
                    item_data['alias'] = decision['new_name']
                    if 'unique_id' in item_data:
                        item_data['unique_id'] = new_id
                    storage_data[new_id] = item_data
                    save_json(storage_path, storage_file)
                    return f"Eintrag als '{decision['new_name']}' in {file_key} importiert."
            else:
                storage_data = storage_file['data'][config['storage_key']]
                if action == 'overwrite':
                    found = False
                    for i, entry in enumerate(storage_data):
                        if entry.get('id') == manifest_item['item_id']:
                            storage_data[i] = item_data
                            found = True
                            break
                    if not found: storage_data.append(item_data)
                    save_json(storage_path, storage_file)
                    return f"Eintrag '{item_data.get('alias') or item_data.get('name')}' in {file_key} überschrieben."
                elif action == 'rename':
                    new_id = str(uuid.uuid4())
                    item_data['id'] = new_id
                    item_data['name'] = decision['new_name']
                    item_data['alias'] = decision['new_name']
                    if 'unique_id' in item_data:
                        item_data['unique_id'] = new_id
                    storage_data.append(item_data)
                    save_json(storage_path, storage_file)
                    return f"Eintrag als '{decision['new_name']}' in {file_key} importiert."
    elif item_type_internal == 'yaml_item':
        yaml_file = manifest_item['yaml_list_file']
        yaml_path = os.path.join(CONFIG_PATH, yaml_file)
        with FILE_LOCKS[yaml_file]:
            data = load_yaml(yaml_path) or []
            item_id = manifest_item['item_id']
            if isinstance(data, list):
                if action == 'overwrite':
                    found = False
                    for i, entry in enumerate(data):
                        if entry.get('id') == item_id:
                            data[i] = item_data
                            found = True
                            break
                    if not found: data.append(item_data)
                    save_yaml(yaml_path, data)
                    return f"Eintrag in {yaml_file} überschrieben."
                elif action == 'rename':
                    new_id = str(uuid.uuid4())
                    item_data['id'] = new_id
                    if 'alias' in item_data: item_data['alias'] = decision['new_name']
                    if 'name' in item_data: item_data['name'] = decision['new_name']
                    if 'unique_id' in item_data:
                        item_data['unique_id'] = new_id
                    data.append(item_data)
                    save_yaml(yaml_path, data)
                    return f"Eintrag als '{decision['new_name']}' in {yaml_file} importiert."
            elif isinstance(data, dict):
                if action == 'overwrite':
                    data[item_id] = item_data
                    save_yaml(yaml_path, data)
                    return f"Eintrag '{item_id}' in {yaml_file} überschrieben."
                elif action == 'rename':
                    new_key = decision['new_name'].lower().replace(' ', '_')
                    if 'alias' in item_data: item_data['alias'] = decision['new_name']
                    if 'name' in item_data: item_data['name'] = decision['new_name']
                    if 'unique_id' in item_data:
                        item_data['unique_id'] = str(uuid.uuid4())
                    data[new_key] = item_data
                    save_yaml(yaml_path, data)
                    return f"Eintrag als '{new_key}' in {yaml_file} importiert."
    return f"Aktion '{action}' für '{manifest_item['id']}' übersprungen."
@app.route('/api/execute_import', methods=['POST'])
def api_execute_import():
    app.logger.info("Execute Import API aufgerufen")
    if 'file' not in request.files:
        return jsonify({"error": "Keine Datei im Request (file)"}), 400
    if 'decisions' not in request.form:
        return jsonify({"error": "Keine Entscheidungen im Request (decisions)"}), 400
    file = request.files['file']
    try:
        decisions = json.loads(request.form.get('decisions'))
    except Exception as e:
        return jsonify({"error": f"Entscheidungen konnten nicht gelesen werden: {e}"}), 400
    results = []
    try:
        with zipfile.ZipFile(file, 'r') as zf:
            if 'export_manifest.json' not in zf.namelist():
                return jsonify({"error": "ZIP-Datei ist kein gültiges Backup (manifest.json fehlt)"}), 400
            manifest_data = zf.read('export_manifest.json')
            manifest = json.loads(manifest_data)
            manifest_dict = {item['zip_path']: item for item in manifest}
            for decision in decisions:
                action = decision['action']
                if action == 'skip':
                    results.append(f"'{decision['id']}' übersprungen.")
                    continue
                zip_path = decision['zip_path']
                if zip_path not in manifest_dict:
                    results.append(f"Fehler: '{zip_path}' nicht im Manifest gefunden.")
                    continue
                manifest_item = manifest_dict[zip_path]
                try:
                    item_data_str = zf.read(zip_path).decode('utf-8')
                    item_data = None
                    if manifest_item['type'] not in ['yaml', 'blueprint']:
                        if zip_path.endswith('.json'):
                            item_data = json.loads(item_data_str)
                        else:
                            item_data = load_yaml_from_string(item_data_str)
                    else:
                        item_data = item_data_str
                    result_msg = execute_import_decision(manifest_item, item_data, decision, zf)
                    results.append(result_msg)
                except Exception as e:
                    app.logger.error(f"Fehler bei Import von {decision['id']}: {e}")
                    results.append(f"Fehler bei Import von {decision['id']}: {e}")
        app.logger.info(f"Import abgeschlossen. {len(results)} Aktionen verarbeitet.")
        return jsonify({
            "message": "Import abgeschlossen. Bitte starten Sie Home Assistant neu.",
            "details": results
        })
    except zipfile.BadZipFile:
        return jsonify({"error": "Ungültige ZIP-Datei"}), 400
    except Exception as e:
        app.logger.error(f"API Fehler /api/execute_import: {e}")
        return jsonify({"error": f"Import-Ausführung fehlgeschlagen: {e}"}), 500
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8099)

