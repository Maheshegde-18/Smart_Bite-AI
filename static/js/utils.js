/**
 * SmartBite AI — Shared Utility Functions
 * Used across all pages for formatting, charts, toasts, and exports.
 */

'use strict';

/* ============================================================
   Number Formatting
   ============================================================ */

/**
 * Format a number with comma separators and fixed decimal places.
 * @param {number} n - The number to format.
 * @param {number} [decimals=1] - Number of decimal places.
 * @returns {string} Formatted number string.
 */
function formatNumber(n, decimals = 1) {
  if (n === null || n === undefined || isNaN(n)) return '—';
  return Number(n).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/* ============================================================
   Toast Notifications
   ============================================================ */

/**
 * Create and show a Bootstrap 5 toast notification.
 * Requires a <div class="toast-container"> in the page.
 * @param {string} message - Text to display.
 * @param {'success'|'error'|'warning'|'info'} [type='success'] - Toast type.
 */
function showToast(message, type = 'success') {
  // Ensure container exists
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
  }

  const iconMap = {
    success: '✅',
    error:   '❌',
    warning: '⚠️',
    info:    'ℹ️',
  };

  const toastId = `toast-${Date.now()}`;
  const toastEl = document.createElement('div');
  toastEl.id = toastId;
  toastEl.className = `toast align-items-center ${type}`;
  toastEl.setAttribute('role', 'alert');
  toastEl.setAttribute('aria-live', 'assertive');
  toastEl.setAttribute('aria-atomic', 'true');
  toastEl.setAttribute('data-bs-delay', '4000');

  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body d-flex align-items-center gap-2">
        <span>${iconMap[type] || iconMap.info}</span>
        <span>${message}</span>
      </div>
      <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  container.appendChild(toastEl);

  const bsToast = new bootstrap.Toast(toastEl);
  bsToast.show();

  // Remove from DOM after hidden
  toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

/* ============================================================
   Spinner Helpers
   ============================================================ */

/**
 * Replace the content of an element with a loading spinner.
 * Stores original content in a data attribute for restoration.
 * @param {string} elementId - ID of the element.
 */
function showSpinner(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.dataset.originalContent = el.innerHTML;
  el.innerHTML = `
    <div class="spinner-wrapper">
      <div class="loading-spinner"></div>
      <span>Loading…</span>
    </div>
  `;
}

/**
 * Restore an element's content after a spinner was shown.
 * @param {string} elementId - ID of the element.
 */
function hideSpinner(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  if (el.dataset.originalContent !== undefined) {
    el.innerHTML = el.dataset.originalContent;
    delete el.dataset.originalContent;
  }
}

/* ============================================================
   CSV Export
   ============================================================ */

/**
 * Export an HTML <table> to a downloadable CSV file.
 * @param {string} tableId - ID of the <table> element.
 * @param {string} [filename='export.csv'] - Download filename.
 */
function exportTableToCSV(tableId, filename = 'export.csv') {
  const table = document.getElementById(tableId);
  if (!table) {
    showToast('Table not found for export.', 'error');
    return;
  }

  const rows = Array.from(table.querySelectorAll('tr'));
  const csv = rows.map(row => {
    const cells = Array.from(row.querySelectorAll('th, td'));
    return cells.map(cell => {
      // Escape double quotes and wrap in quotes if needed
      let val = cell.innerText.replace(/"/g, '""');
      if (val.includes(',') || val.includes('\n') || val.includes('"')) {
        val = `"${val}"`;
      }
      return val;
    }).join(',');
  }).join('\n');

  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href     = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  showToast(`Exported as ${filename}`, 'success');
}

/* ============================================================
   Label Helpers
   ============================================================ */

/**
 * Get a human-readable weather label.
 * @param {number} code - 0, 1, or 2.
 * @returns {string}
 */
function getWeatherLabel(code) {
  const map = { 0: 'Sunny', 1: 'Cloudy', 2: 'Rainy' };
  return map[code] ?? 'Unknown';
}

/**
 * Get a human-readable meal type label.
 * @param {number} code - 0, 1, or 2.
 * @returns {string}
 */
function getMealTypeLabel(code) {
  const map = { 0: 'Breakfast', 1: 'Lunch', 2: 'Dinner' };
  return map[code] ?? 'Unknown';
}

/**
 * Get a short day-of-week label.
 * @param {number} code - 0 (Mon) through 6 (Sun).
 * @returns {string}
 */
function getDayLabel(code) {
  const map = { 0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun' };
  return map[code] ?? 'Unknown';
}

/* ============================================================
   Chart.js Defaults & Colour Palette
   ============================================================ */

/**
 * Default Chart.js colour palette and shared configuration.
 */
const chartDefaults = {
  colors: [
    '#38bdf8', // sky blue
    '#10b981', // emerald green
    '#f59e0b', // amber
    '#8b5cf6', // violet
    '#ef4444', // red
    '#06b6d4', // cyan
    '#f97316', // orange
    '#84cc16', // lime
    '#ec4899', // pink
    '#6366f1', // indigo
  ],

  fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",

  defaultOptions: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          font: { family: "'Inter', 'Segoe UI', system-ui, sans-serif", size: 12 },
          color: '#64748b',
        },
      },
      tooltip: {
        backgroundColor: '#1e293b',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        borderColor: '#334155',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
      },
    },
    scales: {
      x: {
        ticks: { color: '#64748b', font: { size: 11 } },
        grid:  { color: '#f1f5f9' },
      },
      y: {
        ticks: { color: '#64748b', font: { size: 11 } },
        grid:  { color: '#f1f5f9' },
      },
    },
  },
};

/* ============================================================
   Chart.js Wrapper Functions
   ============================================================ */

/** Destroy an existing Chart instance on a canvas if one exists. */
function _destroyChart(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
}

/**
 * Create (or replace) a Chart.js line chart.
 * @param {string}   canvasId  - ID of the <canvas> element.
 * @param {string[]} labels    - X-axis labels.
 * @param {object[]} datasets  - Chart.js dataset objects.
 * @param {object}   [options] - Additional Chart.js options (merged with defaults).
 * @returns {Chart} The Chart instance.
 */
function createLineChart(canvasId, labels, datasets, options = {}) {
  _destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  // Apply default colour if not set
  datasets.forEach((ds, i) => {
    const colour = chartDefaults.colors[i % chartDefaults.colors.length];
    ds.borderColor     = ds.borderColor     ?? colour;
    ds.backgroundColor = ds.backgroundColor ?? colour + '33'; // 20% opacity
    ds.borderWidth     = ds.borderWidth     ?? 2;
    ds.pointRadius     = ds.pointRadius     ?? 3;
    ds.tension         = ds.tension         ?? 0.4;
    ds.fill            = ds.fill            ?? false;
  });

  const mergedOptions = _mergeDeep(
    JSON.parse(JSON.stringify(chartDefaults.defaultOptions)),
    options
  );

  return new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: mergedOptions,
  });
}

/**
 * Create (or replace) a Chart.js bar chart.
 * @param {string}   canvasId  - ID of the <canvas> element.
 * @param {string[]} labels    - X-axis labels.
 * @param {object[]} datasets  - Chart.js dataset objects.
 * @param {object}   [options] - Additional Chart.js options (merged with defaults).
 * @returns {Chart} The Chart instance.
 */
function createBarChart(canvasId, labels, datasets, options = {}) {
  _destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  datasets.forEach((ds, i) => {
    const colour = chartDefaults.colors[i % chartDefaults.colors.length];
    ds.backgroundColor = ds.backgroundColor ?? colour + 'cc'; // 80% opacity
    ds.borderColor     = ds.borderColor     ?? colour;
    ds.borderWidth     = ds.borderWidth     ?? 1;
    ds.borderRadius    = ds.borderRadius    ?? 4;
  });

  const mergedOptions = _mergeDeep(
    JSON.parse(JSON.stringify(chartDefaults.defaultOptions)),
    options
  );

  return new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: mergedOptions,
  });
}

/**
 * Create (or replace) a Chart.js doughnut chart.
 * @param {string}   canvasId - ID of the <canvas> element.
 * @param {string[]} labels   - Segment labels.
 * @param {number[]} data     - Segment values.
 * @param {string[]} [colors] - Array of colour strings (defaults to chartDefaults.colors).
 * @returns {Chart} The Chart instance.
 */
function createDoughnutChart(canvasId, labels, data, colors) {
  _destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  const resolvedColors = colors ?? chartDefaults.colors.slice(0, data.length);

  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: resolvedColors,
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: { family: chartDefaults.fontFamily, size: 12 },
            color: '#64748b',
            padding: 16,
          },
        },
        tooltip: chartDefaults.defaultOptions.plugins.tooltip,
      },
    },
  });
}

/**
 * Create (or replace) a Chart.js scatter chart.
 * @param {string}   canvasId  - ID of the <canvas> element.
 * @param {object[]} datasets  - Chart.js scatter dataset objects (data: [{x,y},...]).
 * @param {object}   [options] - Additional Chart.js options (merged with defaults).
 * @returns {Chart} The Chart instance.
 */
function createScatterChart(canvasId, datasets, options = {}) {
  _destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  datasets.forEach((ds, i) => {
    const colour = chartDefaults.colors[i % chartDefaults.colors.length];
    ds.backgroundColor = ds.backgroundColor ?? colour + 'aa';
    ds.borderColor     = ds.borderColor     ?? colour;
    ds.pointRadius     = ds.pointRadius     ?? 4;
    ds.pointHoverRadius = ds.pointHoverRadius ?? 6;
  });

  const mergedOptions = _mergeDeep(
    JSON.parse(JSON.stringify(chartDefaults.defaultOptions)),
    options
  );

  return new Chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: mergedOptions,
  });
}

/* ============================================================
   Internal Helpers
   ============================================================ */

/**
 * Deep-merge two plain objects (target is mutated, source wins on conflict).
 * Arrays from source overwrite arrays in target.
 */
function _mergeDeep(target, source) {
  for (const key of Object.keys(source)) {
    const sv = source[key];
    const tv = target[key];
    if (
      sv && typeof sv === 'object' && !Array.isArray(sv) &&
      tv && typeof tv === 'object' && !Array.isArray(tv)
    ) {
      _mergeDeep(tv, sv);
    } else {
      target[key] = sv;
    }
  }
  return target;
}
