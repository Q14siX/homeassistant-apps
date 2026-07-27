(() => {
  'use strict';
  const state = { items: [], pendingAction: null };
  const $ = (id) => document.getElementById(id);
  const list = $('extensionList');
  const empty = $('emptyState');
  const search = $('searchInput');
  const categoryFilter = $('categoryFilter');
  const sourceFilter = $('sourceFilter');
  const confirmDialog = $('confirmDialog');
  const restartDialog = $('restartDialog');
  const busy = $('busyOverlay');
  const busyText = $('busyText');

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

  function api(path, options = {}) {
    const method = String(options.method || 'GET').toUpperCase();
    const headers = new Headers(options.headers || {});
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      headers.set('X-CSRF-Token', csrfToken);
    }
    return fetch(path, { cache: 'no-store', ...options, headers });
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (char) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;'
    })[char]);
  }

  function formatDateTime(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
  }

  function renderUpdateStatus(data) {
    const card = $('updateCard');
    const banner = $('updateBanner');
    const stateNode = $('updateState');
    const messageNode = $('updateMessage');
    card.classList.remove('update-ready', 'update-current', 'update-error');

    if (data.checking) {
      stateNode.textContent = 'Prüfung …';
      messageNode.textContent = data.message || 'Neueste Version wird ermittelt.';
      banner.hidden = true;
      window.setTimeout(() => loadUpdateStatus(false), 3000);
      return;
    }
    if (data.enabled === false) {
      stateNode.textContent = 'Deaktiviert';
      messageNode.textContent = data.message || 'Automatische Prüfung ist deaktiviert.';
      banner.hidden = true;
      return;
    }
    if (!data.available && data.error) {
      card.classList.add('update-error');
      stateNode.textContent = 'Nicht verfügbar';
      messageNode.textContent = data.message || data.error;
      banner.hidden = true;
      return;
    }
    if (!data.checked_at) {
      stateNode.textContent = 'Ausstehend';
      messageNode.textContent = data.message || 'Die erste automatische Prüfung startet in Kürze.';
      banner.hidden = true;
      window.setTimeout(() => loadUpdateStatus(false), 5000);
      return;
    }

    const installed = data.installed_version || 'unbekannt';
    const latest = data.latest_version || installed;
    const checked = formatDateTime(data.checked_at);

    if (data.update_available) {
      card.classList.add('update-ready');
      stateNode.textContent = 'Update verfügbar';
      messageNode.textContent = `Installiert ${installed} · Verfügbar ${latest}${checked ? ` · geprüft ${checked}` : ''}`;
      $('updateBannerTitle').textContent = `Version ${latest} ist verfügbar.`;
      $('updateBannerText').textContent = data.auto_update
        ? `Installiert ist ${installed}. Die automatische Aktualisierung ist im Supervisor aktiviert.`
        : `Installiert ist ${installed}. Aktualisieren Sie die App unter Einstellungen → Apps.`;
      banner.hidden = false;
      return;
    }

    banner.hidden = true;
    if (!data.available || data.error) {
      card.classList.add('update-error');
      stateNode.textContent = data.available ? 'Mit Warnung geprüft' : 'Nicht verfügbar';
      messageNode.textContent = data.message || data.error || 'Update-Status konnte nicht geladen werden.';
      return;
    }

    card.classList.add('update-current');
    stateNode.textContent = 'Aktuell';
    messageNode.textContent = `Neueste Version ${latest}${checked ? ` · geprüft ${checked}` : ''}`;
  }

  async function loadUpdateStatus(force = false) {
    if (force) setBusy(true, 'App-Store und verfügbare Version werden geprüft …');
    try {
      const response = force
        ? await api('api/update-status/check', { method: 'POST' })
        : await api('api/update-status');
      const data = await parseJson(response);
      renderUpdateStatus(data);
      if (force) {
        toast(
          data.update_available
            ? `Neue App-Version ${data.latest_version} ist verfügbar.`
            : 'Die installierte App-Version ist aktuell.',
          data.update_available ? 'warning' : 'success'
        );
      }
    } catch (error) {
      renderUpdateStatus({ available: false, error: error.message, message: error.message });
      if (force) toast(error.message, 'error');
    } finally {
      if (force) setBusy(false);
    }
  }

  function formatBytes(bytes) {
    const value = Number(bytes || 0);
    if (value < 1024) return `${value} B`;
    const units = ['KB', 'MB', 'GB'];
    let size = value / 1024;
    let unit = units[0];
    for (let i = 1; i < units.length && size >= 1024; i += 1) {
      size /= 1024; unit = units[i];
    }
    return `${size.toLocaleString('de-DE', { maximumFractionDigits: 1 })} ${unit}`;
  }

  function toast(message, type = 'success', timeout = 6500) {
    const node = document.createElement('div');
    node.className = `toast ${type}`;
    node.textContent = message;
    $('toastStack').appendChild(node);
    window.setTimeout(() => node.remove(), timeout);
  }

  function setBusy(show, text = 'Vorgang wird ausgeführt …') {
    busyText.textContent = text;
    busy.hidden = !show;
  }

  async function parseJson(response) {
    let data;
    try { data = await response.json(); } catch (_) { data = {}; }
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `HTTP-Fehler ${response.status}`);
    }
    return data;
  }

  async function loadExtensions() {
    setBusy(true, 'Erweiterungen werden eingelesen …');
    try {
      const data = await parseJson(await api('api/extensions'));
      state.items = data.items || [];
      $('extensionCount').textContent = String(data.count ?? state.items.length);
      $('hacsState').textContent = data.hacs?.available ? 'Verbunden' : 'Dateisystemmodus';
      $('hacsMessage').textContent = data.hacs?.message || 'Keine Statusmeldung';
      render();
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      setBusy(false);
    }
  }

  function render() {
    const term = search.value.trim().toLowerCase();
    const category = categoryFilter.value;
    const source = sourceFilter.value;
    const filtered = state.items.filter((item) => {
      const matchesCategory = category === 'all' || item.category === category;
      const isHacs = item.source === 'hacs';
      const matchesSource = source === 'all'
        || (source === 'hacs' && isHacs)
        || (source === 'local' && !isHacs);
      const haystack = `${item.name} ${item.domain} ${item.repository} ${item.relative_path}`.toLowerCase();
      return matchesCategory && matchesSource && (!term || haystack.includes(term));
    });
    empty.hidden = filtered.length !== 0;
    list.innerHTML = filtered.map((item) => `
      <article class="extension-item" data-id="${escapeHtml(item.id)}">
        <div class="extension-main">
          <div class="extension-title-row">
            <span class="extension-title">${escapeHtml(item.name)}</span>
            <span class="badge">${escapeHtml(item.category_label)}</span>
            ${item.source === 'hacs' ? '<span class="badge hacs">HACS</span>' : '<span class="badge local">Lokal</span>'}
          </div>
          <div class="extension-meta">
            ${item.version ? `<span>Version ${escapeHtml(item.version)}</span>` : ''}
            ${item.repository ? `<span>${escapeHtml(item.repository)}</span>` : ''}
            <span>${formatBytes(item.size)}</span>
            <span class="extension-path">/${escapeHtml(item.relative_path)}</span>
          </div>
        </div>
        <div class="extension-actions">
          <button class="button secondary small" data-action="archive">Sichern</button>
          <button class="button secondary small" data-action="archive-delete">Sichern &amp; löschen</button>
          <button class="button ghost-danger small" data-action="delete">Löschen</button>
        </div>
      </article>
    `).join('');
  }

  function filenameFromResponse(response, fallback = 'hacs-erweiterung.zip') {
    const disposition = response.headers.get('content-disposition') || '';
    const utf = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf) return decodeURIComponent(utf[1]);
    const plain = disposition.match(/filename="?([^";]+)"?/i);
    return plain ? plain[1] : fallback;
  }

  async function downloadBlob(response) {
    if (!response.ok) {
      let data = {};
      try { data = await response.json(); } catch (_) {}
      throw new Error(data.error || `HTTP-Fehler ${response.status}`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filenameFromResponse(response);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function confirmAction(title, text, actionLabel, action) {
    $('confirmTitle').textContent = title;
    $('confirmText').textContent = text;
    $('confirmAction').textContent = actionLabel;
    state.pendingAction = action;
    confirmDialog.showModal();
  }

  list.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action]');
    const itemNode = event.target.closest('.extension-item');
    if (!button || !itemNode) return;
    const item = state.items.find((entry) => entry.id === itemNode.dataset.id);
    if (!item) return;
    const action = button.dataset.action;
    if (action === 'archive') {
      runArchive(item);
    } else if (action === 'archive-delete') {
      confirmAction(
        'Sichern und löschen?',
        `${item.name} wird als ZIP heruntergeladen und anschließend entfernt.`,
        'Sichern & löschen',
        () => runArchiveDelete(item)
      );
    } else if (action === 'delete') {
      confirmAction(
        'Erweiterung löschen?',
        `${item.name} wird aus der Home-Assistant-Konfiguration entfernt. Eine interne Sicherheitskopie wird angelegt, sofern dies in der App-Konfiguration aktiviert ist.`,
        'Endgültig löschen',
        () => runDelete(item)
      );
    }
  });

  confirmDialog.addEventListener('close', () => {
    if (confirmDialog.returnValue === 'confirm' && state.pendingAction) {
      const action = state.pendingAction;
      state.pendingAction = null;
      action();
    } else {
      state.pendingAction = null;
    }
  });

  async function runArchive(item) {
    setBusy(true, 'Sicherung wird erstellt …');
    try {
      await downloadBlob(await api(`api/extensions/${encodeURIComponent(item.id)}/archive`, { method: 'POST' }));
      toast(`${item.name} wurde gesichert.`);
    } catch (error) { toast(error.message, 'error'); }
    finally { setBusy(false); }
  }

  async function runArchiveDelete(item) {
    setBusy(true, 'Sicherung wird heruntergeladen …');
    try {
      const archiveResponse = await api(
        `api/extensions/${encodeURIComponent(item.id)}/archive`,
        { method: 'POST' }
      );
      await downloadBlob(archiveResponse);
      setBusy(true, 'Erweiterung wird gelöscht …');
      const result = await parseJson(await api(
        `api/extensions/${encodeURIComponent(item.id)}/delete`,
        { method: 'POST' }
      ));
      toast(`${item.name} wurde gesichert und gelöscht.`);
      if (result.warning) toast(result.warning, 'warning', 10000);
      await loadExtensions();
      restartDialog.showModal();
    } catch (error) {
      toast(`Vorgang abgebrochen: ${error.message}`, 'error', 10000);
    } finally {
      setBusy(false);
    }
  }

  async function runDelete(item) {
    setBusy(true, 'Erweiterung wird gelöscht …');
    try {
      const data = await parseJson(await api(`api/extensions/${encodeURIComponent(item.id)}/delete`, { method: 'POST' }));
      toast(`${item.name} wurde gelöscht.`);
      if (data.warning) toast(data.warning, 'warning', 10000);
      await loadExtensions();
      restartDialog.showModal();
    } catch (error) { toast(error.message, 'error'); }
    finally { setBusy(false); }
  }

  $('uploadForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const input = $('zipFile');
    if (!input.files.length) return;
    const data = new FormData(form);
    data.set('overwrite', $('overwrite').checked ? 'true' : 'false');
    setBusy(true, 'ZIP-Datei wird geprüft und installiert …');
    try {
      const result = await parseJson(await api('api/install', { method: 'POST', body: data }));
      toast(`${result.name} wurde als ${result.category_label} installiert.`);
      if (result.hacs_tracking_note) toast(result.hacs_tracking_note, 'warning', 11000);
      form.reset();
      $('fileLabel').textContent = 'Noch keine Datei ausgewählt';
      await loadExtensions();
      restartDialog.showModal();
    } catch (error) { toast(error.message, 'error', 10000); }
    finally { setBusy(false); }
  });

  $('zipFile').addEventListener('change', (event) => {
    $('fileLabel').textContent = event.target.files[0]?.name || 'Noch keine Datei ausgewählt';
  });

  const dropZone = $('dropZone');
  ['dragenter', 'dragover'].forEach((name) => dropZone.addEventListener(name, (event) => {
    event.preventDefault(); dropZone.classList.add('dragging');
  }));
  ['dragleave', 'drop'].forEach((name) => dropZone.addEventListener(name, (event) => {
    event.preventDefault(); dropZone.classList.remove('dragging');
  }));
  dropZone.addEventListener('drop', (event) => {
    if (!event.dataTransfer.files.length) return;
    const transfer = new DataTransfer();
    transfer.items.add(event.dataTransfer.files[0]);
    $('zipFile').files = transfer.files;
    $('fileLabel').textContent = transfer.files[0].name;
  });

  $('restartNow').addEventListener('click', async (event) => {
    event.preventDefault();
    setBusy(true, 'Home Assistant wird neu gestartet …');
    try {
      const data = await parseJson(await api('api/restart', { method: 'POST' }));
      toast(data.message || 'Home Assistant wird neu gestartet.');
      restartDialog.close();
    } catch (error) {
      toast(error.message, 'error');
      setBusy(false);
    }
  });

  search.addEventListener('input', render);
  categoryFilter.addEventListener('change', render);
  sourceFilter.addEventListener('change', render);
  $('refreshButton').addEventListener('click', loadExtensions);
  $('checkUpdatesButton').addEventListener('click', () => loadUpdateStatus(true));
  loadExtensions();
  loadUpdateStatus();
  window.setInterval(() => loadUpdateStatus(false), 5 * 60 * 1000);
})();
