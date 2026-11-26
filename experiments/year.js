(() => {
  'use strict';
  const init = () => {
    const panel = document.getElementById('year-progress');
    if (!panel) return;
    const rows = panel.querySelector('.year-days');
    const progress = panel.querySelector('.year-count');
    const pct = panel.querySelector('.year-percent');
    const fullDate = new Intl.DateTimeFormat('en-GB', {dateStyle: 'long', timeZone: 'UTC'});
    const monthName = new Intl.DateTimeFormat('en-GB', {month: 'short', timeZone: 'UTC'});
    const dayMs = 86_400_000;
    let shown;
    const render = () => {
      if (document.hidden) return;
      const now = new Date();
      const year = now.getFullYear();
      const today = Date.UTC(year, now.getMonth(), now.getDate());
      if (shown === today) return;
      shown = today;
      const elapsed = (today - Date.UTC(year, 0, 1)) / dayMs + 1;
      const total = (Date.UTC(year + 1, 0, 1) - Date.UTC(year, 0, 1)) / dayMs;
      const percent = Math.round(elapsed / total * 100);
      progress.textContent = `${String(elapsed).padStart(3, '0')} / ${total}`;
      progress.setAttribute('aria-label', `Day ${elapsed} of ${total}`);
      pct.textContent = `${percent}%`;
      panel.querySelector('.year-number').textContent = year;
      const fragment = document.createDocumentFragment();
      for (let month = 0; month < 12; month++) {
        const line = document.createElement('div');
        line.className = 'year-month';
        const label = document.createElement('span');
        label.textContent = monthName.format(Date.UTC(year, month, 1));
        line.append(label);
        const days = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
        for (let d = 1; d <= days; d++) {
          const stamp = Date.UTC(year, month, d);
          const cell = document.createElement('span');
          cell.className = 'year-square';
          cell.dataset.state = stamp === today ? 'today' : stamp < today ? 'past' : 'future';
          cell.title = fullDate.format(stamp);
          line.append(cell);
        }
        fragment.append(line);
      }
      rows.replaceChildren(fragment);
    };
    render();
    setInterval(render, 1000 * 30);
    document.addEventListener('visibilitychange', render);
    window.addEventListener('focus', render);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once: true});
  else init();
})();
