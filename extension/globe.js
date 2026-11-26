/* Local Almanac globe preview. The page supplies Astronomy Engine and the controls. */
(() => {
  'use strict';

  const ISS_URL = 'https://api.wheretheiss.at/v1/satellites/25544/positions';
  const POLL = 15_000, MAX_AGE = 45_000, TIMEOUT = 8_000;
  const EARTH_RADIUS_KM = 6371;
  const DEFAULTS = {
    water: '#e2e2e2', land: '#bdbdbd', coast: '#747474', grid: '#a4a4a4',
    zones: '#656565', night: 'rgba(18,18,18,.52)', edge: '#525252',
    pin: '#202020', iss: '#fff'
  };
  const clamp = (n, low, high) => Math.max(low, Math.min(high, n));
  const wrap = lon => ((lon + 180) % 360 + 360) % 360 - 180;
  const coords = p => [wrap(p.lon), p.lat];
  const valid = p => p && Number.isFinite(p.lon) && Number.isFinite(p.lat) && Math.abs(p.lat) <= 90;
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  let usePlace = null, queued = null, recenter = null;
  window.AlmanacGlobe = {
    setPlace(place, cities) {
      if (!valid(place)) return;
      if (usePlace) usePlace(place, cities);
      else queued = [place, cities];
    },
    centerPlace() { recenter?.(); }
  };

  function init() {
    const canvas = document.getElementById('globe');
    const stage = document.getElementById('globe-stage');
    const issButton = document.getElementById('globe-iss');
    const homeButton = document.getElementById('globe-home');
    const status = document.getElementById('iss-status');
    const d3 = window.d3, data = window.AlmanacGlobeData;
    if (!canvas || !stage || !d3?.geoOrthographic || !data) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const projection = d3.geoOrthographic().clipAngle(90).precision(.4);
    const path = d3.geoPath(projection, ctx);
    const nightCircle = d3.geoCircle().radius(90).precision(2);
    const grid = d3.geoGraticule().step([30, 30]).stepMajor([90, 90])();
    const bayer = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
    const textures = new Map();
    function ink(color, threshold) {
      const key = `${color}:${threshold}`;
      if (textures.has(key)) return textures.get(key);
      const tile = document.createElement('canvas');
      tile.width = tile.height = 8;
      const pixels = tile.getContext('2d');
      pixels.fillStyle = color;
      bayer.forEach((value, i) => {
        if (value < threshold) pixels.fillRect((i % 4) * 2, Math.floor(i / 4) * 2, 1, 1);
      });
      const pattern = ctx.createPattern(tile, 'repeat');
      textures.set(key, pattern);
      return pattern;
    }

    let width = 0, height = 0, ratioX = 1, ratioY = 1, radius = 1;
    let frame = null, rotation = null, drag = null, center = [0, 0];
    let selected = null, pins = [], following = false;
    let sunSlot = null, night = null, terminator = null;
    let iss = null, trace = null, pollTimer = null, ageTimer = null, sunTimer = null;
    let inflight = null, failed = false;

    canvas.style.touchAction = 'none';
    canvas.setAttribute('aria-keyshortcuts', 'ArrowLeft ArrowRight ArrowUp ArrowDown Home');
    canvas.setAttribute('aria-description', 'World time zone boundaries and current night side. Drag or use the arrow keys to rotate. Home centers the selected city.');
    issButton?.setAttribute('aria-label', 'Follow the International Space Station');
    issButton?.setAttribute('aria-pressed', 'false');
    if (status) issButton?.setAttribute('aria-describedby', status.id);

    function resize() {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      if (!width || !height) return;
      const scale = Math.min(3, window.devicePixelRatio || 1);
      const pw = Math.max(1, Math.round(width * scale));
      const ph = Math.max(1, Math.round(height * scale));
      if (canvas.width !== pw) canvas.width = pw;
      if (canvas.height !== ph) canvas.height = ph;
      ratioX = pw / width;
      ratioY = ph / height;
      radius = Math.min(width, height) * .448;
      projection.scale(radius).translate([width / 2, height / 2]);
      schedule();
    }

    function schedule() {
      if (frame === null) frame = requestAnimationFrame(render);
    }

    function rotateTo(target, immediate = false) {
      const distance = d3.geoDistance(center, target);
      if (immediate || motion.matches || distance < .009) {
        center = target;
        rotation = null;
      } else {
        let interpolate = d3.geoInterpolate(center, target);
        if (distance > Math.PI - 1e-7) {
          // Antipodes have no unique shortest arc. Choose the east-going one.
          const waypoint = [wrap(center[0] + 90), 0];
          const first = d3.geoInterpolate(center, waypoint);
          const second = d3.geoInterpolate(waypoint, target);
          interpolate = t => t < .5 ? first(2 * t) : second(2 * t - 1);
        }
        rotation = {interpolate, target, start: performance.now(), duration: 370 + 470 * distance / Math.PI};
      }
      schedule();
    }

    function sunlight(now) {
      const slot = Math.floor(now / 30_000);
      if (slot === sunSlot) return;
      const a = window.Astronomy;
      if (!a) return;
      sunSlot = slot;
      const time = new Date(now);
      // Convert the geocentric Sun vector to the equator of date, then rotate
      // right ascension into Earth-fixed longitude using Greenwich sidereal time.
      const vector = a.GeoVector(a.Body.Sun, time, true);
      const sun = a.EquatorFromVector(a.RotateVector(a.Rotation_EQJ_EQD(time), vector));
      const lon = wrap((sun.ra - a.SiderealTime(time)) * 15);
      night = nightCircle.center([wrap(lon + 180), -sun.dec])();
      terminator = {type: 'LineString', coordinates: night.coordinates[0]};
    }

    const liveIss = () => iss && Date.now() - iss.timestamp * 1000 < MAX_AGE ? iss : null;
    const line = (points, geometry = 'LineString') => ({type: geometry, coordinates: points});

    function render(now) {
      frame = null;
      if (!width || !height) return;
      if (rotation) {
        const t = clamp((now - rotation.start) / rotation.duration, 0, 1);
        if (motion.matches || t === 1) {
          center = rotation.target;
          rotation = null;
        } else {
          center = rotation.interpolate(t * t * (3 - 2 * t));
          schedule();
        }
      }
      sunlight(Date.now());
      const computed = getComputedStyle(canvas);
      const c = Object.fromEntries(Object.entries(DEFAULTS).map(([key, color]) => [key,
        computed.getPropertyValue(`--globe-${key}`).trim() || color]));
      projection.rotate([-center[0], -center[1], 0]);
      ctx.setTransform(ratioX, 0, 0, ratioY, 0, 0);
      ctx.clearRect(0, 0, width, height);
      const x = width / 2, y = height / 2;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';

      function disc() {
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, 2 * Math.PI);
      }
      function fill(geometry, color) {
        if (!geometry) return;
        ctx.beginPath();
        path(geometry);
        ctx.fillStyle = color;
        ctx.fill();
      }
      function stroke(geometry, color, weight, alpha = 1, dash = []) {
        if (!geometry) return;
        ctx.beginPath();
        path(geometry);
        ctx.strokeStyle = color;
        ctx.lineWidth = weight;
        ctx.globalAlpha = alpha;
        ctx.setLineDash(dash);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
      }
      function point(px, py, size, color) {
        ctx.beginPath();
        ctx.arc(px, py, size, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();
      }
      function caption(text, px, py, color) {
        if (!text || radius < 95) return;
        ctx.font = '600 10px ui-monospace, monospace';
        ctx.textBaseline = 'middle';
        const right = px + ctx.measureText(text).width + 16 < width - 4;
        ctx.textAlign = right ? 'left' : 'right';
        const offset = right ? 10 : -10;
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = c.water;
        ctx.strokeText(text, px + offset, py);
        ctx.fillStyle = color;
        ctx.fillText(text, px + offset, py);
      }

      ctx.save();
      disc();
      ctx.fillStyle = c.water;
      ctx.fill();
      ctx.clip();
      fill(data.land, c.land);
      const grain = document.documentElement.dataset.design === 'grid';
      if (grain) {
        fill(data.land, ink('rgba(0,0,0,.40)', 13));
        ctx.fillStyle = ink('rgba(0,0,0,.12)', 4);
        ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
      }
      stroke(grid, c.grid, .55, .55);
      stroke(data.zoneWater, c.zones, .65, .65, [2.2, 2.35]);
      stroke(data.zoneLand, c.zones, .7, .77);
      stroke(data.coast, c.coast, .85, .93);

      // The limb vignette reveals curvature without competing with the solar edge.
      const shading = ctx.createRadialGradient(x - radius * .18, y - radius * .24, radius * .12,
        x, y, radius);
      shading.addColorStop(0, 'rgba(255,255,255,.14)');
      shading.addColorStop(.61, 'rgba(128,128,128,0)');
      shading.addColorStop(1, 'rgba(0,0,0,.17)');
      ctx.fillStyle = shading;
      ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
      fill(night, c.night);
      if (grain) fill(night, ink('rgba(255,255,255,.48)', 8));
      stroke(terminator, c.water, .75, .47);

      const station = liveIss();
      if (station) stroke(trace, c.iss, 1.35, .78, [3, 3.5]);
      function visible(p) {
        return d3.geoDistance(center, p) < Math.PI / 2;
      }
      for (const p of pins) {
        const pos = coords(p);
        if (selected && pos[0] === coords(selected)[0] && pos[1] === selected.lat) continue;
        if (!visible(pos)) continue;
        const [px, py] = projection(pos);
        point(px, py, 2.75, c.water);
        point(px, py, 1.75, c.pin);
      }
      if (selected && visible(coords(selected))) {
        const [px, py] = projection(coords(selected));
        point(px, py, 6, c.water);
        point(px, py, 4.8, c.pin);
        point(px, py, 1.8, c.water);
        caption(String(selected.name || ''), px, py, c.pin);
      }
      ctx.restore();
      disc();
      ctx.strokeStyle = c.edge;
      ctx.lineWidth = 1;
      ctx.stroke();

      if (station) {
        const pos = [station.longitude, station.latitude];
        const nearSide = visible(pos);
        const [sx, sy] = projection(pos);
        const elevation = 1 + station.altitude / EARTH_RADIUS_KM;
        const px = x + (sx - x) * elevation, py = y + (sy - y) * elevation;
        // On the far side an elevated marker is visible only beyond the limb.
        // Keep the entire glyph outside the silhouette to avoid painting over it.
        if (nearSide || Math.hypot(px - x, py - y) > radius + 7) {
          if (nearSide && Math.hypot(px - sx, py - sy) > 5) {
            ctx.beginPath();
            ctx.moveTo(sx, sy);
            ctx.lineTo(px, py);
            ctx.strokeStyle = c.iss;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
          ctx.beginPath();
          ctx.moveTo(px, py - 5);
          ctx.lineTo(px + 5, py);
          ctx.lineTo(px, py + 5);
          ctx.lineTo(px - 5, py);
          ctx.closePath();
          ctx.fillStyle = c.iss;
          ctx.fill();
          ctx.strokeStyle = '#222';
          ctx.lineWidth = 1.25;
          ctx.stroke();
        }
      }
    }

    function stopFollowing() {
      following = false;
      issButton?.setAttribute('aria-pressed', 'false');
    }

    function returnHome() {
      stopFollowing();
      if (selected) rotateTo(coords(selected));
    }
    recenter = returnHome;

    usePlace = (place, cities) => {
      const first = selected === null;
      const changed = first || selected.lat !== place.lat || coords(selected)[0] !== coords(place)[0];
      selected = place;
      pins = Array.isArray(cities) ? cities.filter(valid) : [];
      if (changed) {
        stopFollowing();
        rotateTo(coords(place), first);
      } else schedule();
    };
    if (queued) {
      usePlace(...queued);
      queued = null;
    }

    canvas.addEventListener('pointerdown', e => {
      if (!e.isPrimary || e.button !== 0 || drag) return;
      canvas.setPointerCapture(e.pointerId);
      canvas.focus({preventScroll: true});
      rotation = null;
      stopFollowing();
      drag = {id: e.pointerId, x: e.clientX, y: e.clientY};
    });
    canvas.addEventListener('pointermove', e => {
      if (e.pointerId !== drag?.id) return;
      const speed = 68 / radius;
      center = [wrap(center[0] - (e.clientX - drag.x) * speed),
        clamp(center[1] + (e.clientY - drag.y) * speed, -90, 90)];
      drag.x = e.clientX;
      drag.y = e.clientY;
      schedule();
    });
    for (const event of ['pointerup', 'pointercancel', 'lostpointercapture']) {
      canvas.addEventListener(event, e => { if (e.pointerId === drag?.id) drag = null; });
    }
    canvas.addEventListener('keydown', e => {
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      if (e.key === 'Home') {
        e.preventDefault();
        returnHome();
        return;
      }
      const offset = {ArrowLeft: [-12, 0], ArrowRight: [12, 0], ArrowUp: [0, 12], ArrowDown: [0, -12]}[e.key];
      if (!Array.isArray(offset)) return;
      e.preventDefault();
      stopFollowing();
      const base = rotation?.target || center;
      rotateTo([wrap(base[0] + offset[0]), clamp(base[1] + offset[1], -90, 90)]);
    });
    if (homeButton?.dataset.managed !== 'true') homeButton?.addEventListener('click', returnHome);
    issButton?.addEventListener('click', () => {
      const position = liveIss();
      if (!position) return;
      if (following && selected) returnHome();
      else {
        following = true;
        issButton.setAttribute('aria-pressed', 'true');
        rotateTo([position.longitude, position.latitude]);
      }
    });

    function report() {
      const active = Boolean(liveIss());
      const text = failed ? (active ? 'ISS · retrying' : 'ISS · unavailable') : (active ? '' : 'ISS · connecting');
      if (status && status.textContent !== text) status.textContent = text;
      issButton?.setAttribute('aria-disabled', String(!active));
      if (!active) stopFollowing();
    }

    function sample(p) {
      return p && p.id === 25544 && p.units === 'kilometers' &&
        Number.isFinite(p.timestamp) && Number.isFinite(p.latitude) && Math.abs(p.latitude) <= 90 &&
        Number.isFinite(p.longitude) && Math.abs(p.longitude) <= 180 &&
        Number.isFinite(p.altitude) && p.altitude > 0 && p.altitude < 1000;
    }

    async function poll() {
      if (document.hidden || inflight) return;
      const start = performance.now();
      const controller = new AbortController();
      inflight = controller;
      const timeout = setTimeout(() => controller.abort(), TIMEOUT);
      try {
        const stamp = Math.floor(Date.now() / 1000);
        const timestamps = Array.from({length: 10}, (_, i) => stamp - (9 - i) * 45);
        const response = await fetch(`${ISS_URL}?timestamps=${timestamps.join(',')}`, {
          signal: controller.signal, cache: 'no-store', credentials: 'omit'
        });
        if (!response.ok) throw new Error(`ISS HTTP ${response.status}`);
        const readings = await response.json();
        if (!Array.isArray(readings)) throw new Error('Invalid ISS response');
        const points = readings.filter(p => sample(p) && timestamps.includes(p.timestamp))
          .sort((a, b) => a.timestamp - b.timestamp);
        const newest = points.at(-1);
        if (!newest || Math.abs(Date.now() - newest.timestamp * 1000) >= MAX_AGE || newest.timestamp !== stamp) {
          throw new Error('No fresh ISS position');
        }
        iss = newest;
        trace = points.length > 1 ? line(points.map(p => [p.longitude, p.latitude])) : null;
        failed = false;
        if (following) rotateTo([iss.longitude, iss.latitude]);
        clearTimeout(ageTimer);
        ageTimer = setTimeout(() => {
          failed = true;
          report();
          schedule();
        }, Math.max(0, iss.timestamp * 1000 + MAX_AGE - Date.now()));
      } catch {
        if (!document.hidden) failed = true;
      } finally {
        clearTimeout(timeout);
        inflight = null;
        report();
        schedule();
        if (!document.hidden) pollTimer = setTimeout(poll, Math.max(0, POLL - (performance.now() - start)));
      }
    }

    new ResizeObserver(resize).observe(stage);
    window.addEventListener('resize', resize, {passive: true});
    // Each design may change its monochrome palette by switching the root theme.
    const theme = new MutationObserver(schedule);
    for (const element of [document.documentElement, document.body, stage, canvas]) {
      theme.observe(element, {attributes: true, attributeFilter: ['class', 'style', 'data-theme', 'data-design']});
    }
    function visibility() {
      clearTimeout(pollTimer);
      clearInterval(sunTimer);
      if (document.hidden) {
        inflight?.abort();
        return;
      }
      if (iss && !liveIss()) failed = true;
      report();
      schedule();
      void poll();
      sunTimer = setInterval(schedule, 30_000);
    }
    document.addEventListener('visibilitychange', visibility);
    resize();
    report();
    visibility();
  }

  if (document.getElementById('globe')) init();
  else if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once: true});
})();
