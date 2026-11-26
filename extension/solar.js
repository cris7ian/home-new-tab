(() => {
  'use strict';

  function initSolarPanel() {
    const panel = document.getElementById('solar-system');
    if (!panel) return;

    const plot = panel.querySelector('.solar-plot');
    const [x0, y0, width, height] = plot.getAttribute('viewBox').split(/\s+/).map(Number);
    const cx = x0 + width / 2;
    const cy = y0 + height / 2;
    const marks = panel.querySelector('[data-solar-marks]');
    const date = panel.querySelector('[data-solar-date]');
    const status = panel.querySelector('[data-solar-status]');
    const sizes = [3.1, 3.7, 4, 3.4, 5.5, 4.8, 4.4, 4.4];
    const planets = [...panel.querySelectorAll('[data-planet]')].map((row, i) => ({
      name: row.dataset.planet,
      cell: row.querySelector('td'),
      number: i + 1,
      size: sizes[i],
      radius: Number(plot.querySelector(`[data-orbit="${row.dataset.planet}"]`).getAttribute('r')),
    }));
    const refreshMs = 15 * 60 * 1000;
    let renderedDay;
    let renderedBucket;

    function svg(tag, attrs, text) {
      const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
      for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
      if (text !== undefined) node.textContent = text;
      return node;
    }

    const radians = Math.PI / 180;
    const angles = [0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180];
    const box = (x, y, halfW, halfH = halfW) => [x - halfW, y - halfH, x + halfW, y + halfH];
    const overlaps = (a, b) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];

    function placeLabels(points) {
      const taken = [box(cx, cy, 30), ...points.map(p => box(p.x, p.y, p.size + 2))];
      for (const bearing of plot.querySelectorAll('.solar-bearings text')) {
        taken.push(box(Number(bearing.getAttribute('x')), Number(bearing.getAttribute('y')) - 4, 15, 8));
      }
      // Place the most constrained labels first, without moving the actual planet dots.
      for (const point of [...points].sort((a, b) => a.radius - b.radius)) {
        const direction = point.theta + Math.PI / 2;
        search: for (const offset of [17, 23, 31, 40]) {
          for (const angle of angles) {
            const bearing = direction + angle * radians;
            const lx = point.x + offset * Math.cos(bearing);
            const ly = point.y + offset * Math.sin(bearing);
            const bounds = box(lx, ly, 9, 9);
            if (bounds[0] < 7 || bounds[1] < 7 || bounds[2] > width - 7 || bounds[3] > height - 7) continue;
            if (taken.some(other => overlaps(bounds, other))) continue;
            point.label = { x: lx, y: ly };
            taken.push(bounds);
            break search;
          }
        }
      }
    }

    function paint(points) {
      placeLabels(points);
      const leaders = [];
      const dots = [];
      const labels = [];
      for (const p of points) {
        dots.push(svg('circle', { class: 'solar-point', 'data-body': p.name, cx: p.x, cy: p.y, r: p.size }));
        if (!p.label) continue;
        const { x, y } = p.label;
        leaders.push(svg('line', { class: 'solar-leader', x1: p.x, y1: p.y, x2: x, y2: y }));
        labels.push(svg('rect', { class: 'solar-tag', x: x - 8, y: y - 8, width: 16, height: 16 }));
        labels.push(svg('text', { class: 'solar-number', x, y: y + 4.6 }, p.number));
      }
      marks.replaceChildren(...leaders, ...dots, ...labels);
      for (const p of points) p.cell.textContent = `${((Math.round(p.lon * 10) % 3600) / 10).toFixed(1)}°`;
    }

    function update() {
      if (document.hidden) return;
      const now = new Date();
      const day = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      const bucket = Math.floor(now.getTime() / refreshMs);
      if (day === renderedDay && bucket === renderedBucket) return;

      const engine = globalThis.Astronomy;
      try {
        if (!engine) throw new Error('Astronomy Engine unavailable');
        const rotation = engine.Rotation_EQJ_ECL();
        const time = engine.MakeTime(now);
        const points = planets.map(p => {
          const equatorial = engine.HelioVector(engine.Body[p.name], time);
          const { lon } = engine.SphereFromVector(engine.RotateVector(rotation, equatorial));
          if (!Number.isFinite(lon)) throw new Error('Invalid heliocentric longitude');
          const theta = lon * radians;
          return { ...p, lon, theta, x: cx + p.radius * Math.cos(theta), y: cy - p.radius * Math.sin(theta) };
        });
        paint(points);
      } catch {
        marks.replaceChildren();
        for (const { cell } of planets) cell.textContent = '—';
        date.hidden = true;
        status.hidden = false;
        renderedBucket = undefined;
        return;
      }
      date.textContent = day;
      date.dateTime = day;
      status.hidden = true;
      date.hidden = false;
      renderedDay = day;
      renderedBucket = bucket;
    }

    update();
    setInterval(update, 60 * 1000);
    document.addEventListener('visibilitychange', update);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSolarPanel, { once: true });
  } else {
    initSolarPanel();
  }
})();
