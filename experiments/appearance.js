(() => {
  'use strict';
  const root = document.documentElement;
  const designs = new Set(['atlas', 'orbital', 'grid']);
  const key = 'home-new-tab.appearance.v1';
  const chosen = new URLSearchParams(location.search).get('design');
  let stored;
  try { stored = localStorage.getItem(key); } catch { /* Storage can be disabled. */ }
  const initial = [chosen, stored, root.dataset.design].find(value => designs.has(value)) || 'atlas';
  root.dataset.design = initial;
  const setup = () => {
    const open = document.getElementById('settings-open');
    const dialog = document.getElementById('settings');
    const select = document.getElementById('appearance');
    select.value = initial;
    select.addEventListener('change', () => {
      if (!designs.has(select.value)) return;
      root.dataset.design = select.value;
      try { localStorage.setItem(key, select.value); } catch { /* Keep the in-tab selection. */ }
      history.replaceState(null, '', location.pathname);
      window.dispatchEvent(new Event('resize'));
    });
    open.addEventListener('click', () => dialog.showModal());
    document.getElementById('settings-close').addEventListener('click', () => dialog.close());
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup, { once: true });
  else setup();
})();
