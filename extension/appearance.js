(() => {
  'use strict';
  const root = document.documentElement;
  const designs = new Set(['atlas', 'orbital', 'grid']);
  const key = 'home-new-tab.appearance.v1';
  const themeKey = 'home-new-tab.theme.v1';
  const themes = new Set(['system', 'light', 'dark']);
  const systemDark = matchMedia('(prefers-color-scheme: dark)');
  let preferred = 'system';
  const chosen = new URLSearchParams(location.search).get('design');
  let stored;
  try { stored = localStorage.getItem(key); } catch { /* Storage can be disabled. */ }
  const fixed = root.dataset.fixedDesign === 'true';
  const initial = (fixed ? root.dataset.design : [chosen, stored, root.dataset.design].find(value => designs.has(value))) || 'grid';
  root.dataset.design = initial;
  if (root.dataset.presentation === 'center') {
    try {
      const saved = localStorage.getItem(themeKey);
      if (themes.has(saved)) preferred = saved;
    } catch { /* Use the system preference. */ }
    const paintTheme = () => {
      root.dataset.theme = preferred === 'system' ? (systemDark.matches ? 'dark' : 'light') : preferred;
    };
    paintTheme();
    systemDark.addEventListener('change', paintTheme);
    window.addEventListener('storage', (event) => {
      if (event.key !== themeKey && event.key !== null) return;
      preferred = themes.has(event.newValue) ? event.newValue : 'system';
      const control = document.getElementById('theme');
      if (control) control.value = preferred;
      paintTheme();
    });
    document.addEventListener('DOMContentLoaded', () => {
      const control = document.getElementById('theme');
      control.value = preferred;
      control.addEventListener('change', () => {
        if (!themes.has(control.value)) return;
        preferred = control.value;
        try { localStorage.setItem(themeKey, preferred); } catch { /* Keep the in-tab preference. */ }
        paintTheme();
      });
    }, { once: true });
  }
  const setup = () => {
    const open = document.getElementById('settings-open');
    const dialog = document.getElementById('settings');
    const select = document.getElementById('appearance');
    if (select) select.value = initial;
    select?.addEventListener('change', () => {
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
