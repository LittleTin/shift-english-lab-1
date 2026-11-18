(function () {
  'use strict';
  const version = window.SHIFT_CATALOG?.version;
  if (!/^\d+\.\d+\.\d+$/.test(version || '')) return;
  for (const label of document.querySelectorAll('[data-site-version]')) {
    label.textContent = ' / VERSION ' + version;
  }
})();
