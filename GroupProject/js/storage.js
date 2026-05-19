// === DATAFORGE STORAGE UTILITY ===
// Handles data sharing between pages using sessionStorage

const DataStore = {
  save(key, value) {
    try {
      sessionStorage.setItem('df_' + key, JSON.stringify(value));
    } catch(e) { console.warn('Storage error', e); }
  },
  load(key) {
    try {
      const v = sessionStorage.getItem('df_' + key);
      return v ? JSON.parse(v) : null;
    } catch(e) { return null; }
  },
  clear(key) { sessionStorage.removeItem('df_' + key); },
  clearAll() {
    Object.keys(sessionStorage)
      .filter(k => k.startsWith('df_'))
      .forEach(k => sessionStorage.removeItem(k));
  }
};

// Shared CSV → array-of-objects parser
function parseCSV(text) {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return { headers: [], rows: [] };
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
  const rows = lines.slice(1).map(line => {
    const vals = [];
    let cur = '', inQ = false;
    for (let i = 0; i < line.length; i++) {
      if (line[i] === '"') { inQ = !inQ; }
      else if (line[i] === ',' && !inQ) { vals.push(cur.trim()); cur = ''; }
      else cur += line[i];
    }
    vals.push(cur.trim());
    const obj = {};
    headers.forEach((h, i) => obj[h] = vals[i] !== undefined ? vals[i] : '');
    return obj;
  });
  return { headers, rows };
}

// Convert rows + headers back to CSV text
function toCSV(headers, rows) {
  const lines = [headers.join(',')];
  rows.forEach(row => {
    lines.push(headers.map(h => {
      const v = String(row[h] ?? '');
      return v.includes(',') ? `"${v}"` : v;
    }).join(','));
  });
  return lines.join('\n');
}

// Download helper
function downloadFile(filename, content, type = 'text/csv') {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

// Download JSON
function downloadJSON(filename, obj) {
  downloadFile(filename, JSON.stringify(obj, null, 2), 'application/json');
}

// Render a small preview table
function renderTable(container, headers, rows, maxRows = 10) {
  const shown = rows.slice(0, maxRows);
  let html = '<div class="data-table-wrap"><table class="data-table"><thead><tr>';
  headers.forEach(h => html += `<th>${h}</th>`);
  html += '</tr></thead><tbody>';
  shown.forEach(row => {
    html += '<tr>';
    headers.forEach(h => html += `<td>${row[h] ?? ''}</td>`);
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  if (rows.length > maxRows) html += `<p style="color:var(--text-muted);font-size:.8rem;margin-top:8px;">Showing ${maxRows} of ${rows.length} rows</p>`;
  container.innerHTML = html;
}

// Detect column types
function detectTypes(headers, rows) {
  const types = {};
  headers.forEach(h => {
    const vals = rows.map(r => r[h]).filter(v => v !== '' && v !== null && v !== undefined);
    const numCount = vals.filter(v => !isNaN(Number(v))).length;
    types[h] = numCount / vals.length > 0.8 ? 'numeric' : 'categorical';
  });
  return types;
}

// Compute basic stats for a numeric column
function colStats(rows, col) {
  const vals = rows.map(r => parseFloat(r[col])).filter(v => !isNaN(v));
  if (!vals.length) return null;
  const sum = vals.reduce((a, b) => a + b, 0);
  const mean = sum / vals.length;
  const sorted = [...vals].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)];
  const variance = vals.reduce((s, v) => s + (v - mean) ** 2, 0) / vals.length;
  return { min: sorted[0], max: sorted[sorted.length - 1], mean: +mean.toFixed(3), median, std: +Math.sqrt(variance).toFixed(3), count: vals.length };
}

// Count missing values per column
function countMissing(rows, headers) {
  const counts = {};
  headers.forEach(h => {
    counts[h] = rows.filter(r => r[h] === '' || r[h] === null || r[h] === undefined || r[h] === 'NaN').length;
  });
  return counts;
}
