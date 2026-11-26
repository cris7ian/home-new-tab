(() => {
  'use strict';

  function start() {
    const $ = (id) => document.getElementById(id);
    const svgNS = 'http://www.w3.org/2000/svg';
    const storageKey = 'local-almanac.place.v1';
    const minute = 60_000;
    const day = 24 * 60 * minute;
    const cities = [
      { name: 'Los Angeles', lat: 34.05, lon: -118.24, zone: 'America/Los_Angeles' },
      { name: 'New York', lat: 40.71, lon: -74.01, zone: 'America/New_York' },
      { name: 'São Paulo', lat: -23.55, lon: -46.63, zone: 'America/Sao_Paulo' },
      { name: 'London', lat: 51.51, lon: -0.13, zone: 'Europe/London' },
      { name: 'Madrid', lat: 40.42, lon: -3.70, zone: 'Europe/Madrid' },
      { name: 'Dubai', lat: 25.20, lon: 55.27, zone: 'Asia/Dubai' },
      { name: 'Tokyo', lat: 35.68, lon: 139.69, zone: 'Asia/Tokyo' },
      { name: 'Sydney', lat: -33.87, lon: 151.21, zone: 'Australia/Sydney' },
    ];
    const madrid = cities.find((city) => city.name === 'Madrid');
    const dialog = $('location-dialog');
    const query = $('city-query');
    const results = $('city-results');
    const status = $('location-status');
    const locate = $('locate');
    const weatherIcon = $('weather-icon');
    const marker = $('sun-marker');
    const formatterCache = new Map();
    let weatherRequest;
    let weatherDue = 0;
    let locationRequest;
    let locationVersion = 0;
    let sun;
    let moonMinute;

    function formatter(zone, options) {
      const key = JSON.stringify([zone, options]);
      if (!formatterCache.has(key)) {
        formatterCache.set(key, new Intl.DateTimeFormat('en-GB', { ...options, timeZone: zone }));
      }
      return formatterCache.get(key);
    }

    const timeOptions = { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' };
    const dateOptions = { year: 'numeric', month: '2-digit', day: '2-digit' };
    const deviceZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone;
    const time = (instant, zone) => formatter(zone, timeOptions).format(instant);
    const parts = (instant, zone, options) => Object.fromEntries(
      formatter(zone, options).formatToParts(instant).map(({ type, value }) => [type, value]),
    );
    const write = (node, text) => { if (node.textContent !== text) node.textContent = text; };

    function validZone(zone) {
      if (typeof zone !== 'string' || !zone) return false;
      try {
        formatter(zone, timeOptions);
        return true;
      } catch {
        return false;
      }
    }

    function validCoordinates(lat, lon) {
      return Number.isFinite(lat) && Math.abs(lat) <= 90 && Number.isFinite(lon) && Math.abs(lon) <= 180;
    }

    function readPlace() {
      try {
        const saved = JSON.parse(localStorage.getItem(storageKey));
        if (saved && typeof saved.name === 'string' && saved.name.trim() &&
            validCoordinates(saved.lat, saved.lon) && (saved.gps === true || validZone(saved.zone))) {
          return { ...saved, zone: validZone(saved.zone) ? saved.zone : null };
        }
      } catch { /* Storage can be disabled. */ }
      // Use a preset only for a matching device time zone; otherwise use Madrid.
      const zone = deviceZone();
      return cities.find((city) => Intl.DateTimeFormat('en', { timeZone: city.zone })
        .resolvedOptions().timeZone === zone) || madrid;
    }

    let place = readPlace();

    function savePlace() {
      try { localStorage.setItem(storageKey, JSON.stringify(place)); } catch { /* Keep the in-page selection. */ }
    }

    function html(tag, className, text) {
      const element = document.createElement(tag);
      if (className) element.className = className;
      if (text !== undefined) element.textContent = text;
      return element;
    }

    function svg(tag, attributes) {
      const element = document.createElementNS(svgNS, tag);
      for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
      return element;
    }

    const clocks = cities.map((city) => {
      const button = html('button', 'clock');
      button.type = 'button';
      const clockTime = html('span', 'clock-time');
      const offset = html('span', 'clock-offset');
      button.append(html('span', 'clock-city', city.name), clockTime, offset);
      button.addEventListener('click', () => selectPlace(city));
      return { city, button, clockTime, offset };
    });
    $('clocks').replaceChildren(...clocks.map(({ button }) => button));

    function matchingCity(location) {
      return cities.find((city) => city.name === location.name &&
        Math.abs(city.lat - location.lat) < 0.1 && Math.abs(city.lon - location.lon) < 0.1);
    }

    function renderPlace() {
      const label = place.label || place.name;
      write($('place-name'), label);
      $('weather-place').setAttribute('aria-label', `Change weather location: ${label}`);
      const selected = matchingCity(place);
      for (const { city, button } of clocks) {
        button.classList.toggle('active', city === selected);
        button.setAttribute('aria-pressed', String(city === selected));
      }
      const points = cities.includes(selected) ? cities : [...cities, place];
      const active = selected || place;
      const pins = [];
      for (const point of points) {
        const position = { cx: (point.lon + 180) * 2, cy: (85 - point.lat) * 2 };
        const pin = svg('circle', { ...position, r: 2.6, class: 'pin', 'vector-effect': 'non-scaling-stroke' });
        const title = svg('title', {});
        title.textContent = point.label || point.name;
        pin.append(title);
        if (point === active) {
          const ring = svg('circle', { ...position, r: 6.5, class: 'pin active',
            'vector-effect': 'non-scaling-stroke' });
          ring.style.fill = 'none';
          ring.append(title.cloneNode(true));
          pins.push(ring);
        }
        pins.push(pin);
      }
      $('map-pins').replaceChildren(...pins);
    }

    function selectPlace(next) {
      weatherRequest?.abort();
      place = next;
      savePlace();
      sun = null;
      renderPlace();
      paintSun(new Date());
      write($('weather-temp'), '—');
      write($('weather-condition'), '');
      weatherIcon.replaceChildren();
      refreshWeather(true);
    }

    const conditions = {
      0: ['Clear sky', 'clear'], 1: ['Mainly clear', 'partly'], 2: ['Partly cloudy', 'partly'],
      3: ['Overcast', 'cloud'], 45: ['Fog', 'fog'], 48: ['Depositing rime fog', 'fog'],
      51: ['Light drizzle', 'drizzle'], 53: ['Moderate drizzle', 'drizzle'], 55: ['Dense drizzle', 'drizzle'],
      56: ['Light freezing drizzle', 'sleet'], 57: ['Dense freezing drizzle', 'sleet'],
      61: ['Slight rain', 'rain'], 63: ['Moderate rain', 'rain'], 65: ['Heavy rain', 'rain'],
      66: ['Light freezing rain', 'sleet'], 67: ['Heavy freezing rain', 'sleet'],
      71: ['Slight snowfall', 'snow'], 73: ['Moderate snowfall', 'snow'], 75: ['Heavy snowfall', 'snow'],
      77: ['Snow grains', 'snow'], 80: ['Slight rain showers', 'rain'],
      81: ['Moderate rain showers', 'rain'], 82: ['Violent rain showers', 'rain'],
      85: ['Slight snow showers', 'snow'], 86: ['Heavy snow showers', 'snow'],
      95: ['Thunderstorm', 'storm'], 96: ['Thunderstorm with slight hail', 'storm'],
      99: ['Thunderstorm with heavy hail', 'storm'],
    };

    function drawWeather(kind, isDay) {
      const sunGlyph = 'M24 12V7m0 34v-5M12 24H7m34 0h-5M15.5 15.5 12 12m24 24-3.5-3.5m0-17 3.5-3.5M12 36l3.5-3.5 M24 16a8 8 0 1 1 0 16 8 8 0 1 1 0-16';
      const moonGlyph = 'M29 7a17 17 0 1 0 12 23A15 15 0 0 1 29 7Z';
      const cloud = 'M12 32a6.5 6.5 0 0 1-.5-13A11 11 0 0 1 33 18a7 7 0 1 1 1 14Z';
      const partlyCloud = 'M11 37a6 6 0 0 1-.5-12A9 9 0 0 1 28 24a6.5 6.5 0 1 1 2 13Z';
      const accents = {
        fog: 'M9 37h30M14 42h20', drizzle: 'M15 37l-1 2m10-2-1 2m10-2-1 2',
        rain: 'M15 36l-3 6m12-6-3 6m12-6-3 6', sleet: 'M15 36l-3 6m12-3h5m-2.5-2.5v5m8-5.5-3 6',
        snow: 'M12 39h6m-3-3v6m-2-5 4 4m0-4-4 4m10 0h6m-3-3v6m-2-5 4 4m0-4-4 4m9-4h6m-3-3v6m-2-5 4 4m0-4-4 4',
        storm: 'M24 32l-5 6h8l-5 7',
      };
      let shape;
      if (kind === 'clear') shape = isDay ? sunGlyph : moonGlyph;
      else if (kind === 'partly') {
        const behind = isDay ? 'M25 13a7 7 0 0 1 13 5m-7-9V6m9 6 3-2m-1 11h3' : 'M25 13a10 10 0 0 1 8-6 9 9 0 0 0 9 11 11 11 0 0 1-4 4';
        shape = `${behind} ${partlyCloud}`;
      } else if (kind) shape = `${cloud} ${accents[kind] || ''}`;
      weatherIcon.replaceChildren(...(shape ? [svg('path', {
        d: shape, fill: 'none', stroke: 'currentColor', 'stroke-width': 1.5,
        'stroke-linecap': 'round', 'stroke-linejoin': 'round',
      })] : []));
    }

    async function fetchJSON(url, controller) {
      const timeout = setTimeout(() => controller.abort(), 10_000);
      try {
        const response = await fetch(url, { signal: controller.signal, credentials: 'omit', referrerPolicy: 'no-referrer' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
      } finally {
        clearTimeout(timeout);
      }
    }

    async function refreshWeather(force = false) {
      if (!force && (weatherRequest || Date.now() < weatherDue || document.hidden)) return;
      const controller = new AbortController();
      const target = place;
      weatherRequest = controller;
      const url = new URL('https://api.open-meteo.com/v1/forecast');
      url.search = new URLSearchParams({
        latitude: target.lat.toFixed(2), longitude: target.lon.toFixed(2),
        current: 'temperature_2m,weather_code,is_day', temperature_unit: 'celsius', timezone: 'auto',
      });
      try {
        const data = await fetchJSON(url, controller);
        if (weatherRequest !== controller) return;
        if (target.gps && validZone(data.timezone) && data.timezone !== target.zone) {
          target.zone = data.timezone;
          savePlace();
          sun = null;
          paintSun(new Date());
        }
        const current = data.current;
        if (!current || !Number.isFinite(current.temperature_2m)) throw new Error('Missing current weather');
        const [description, kind] = conditions[current.weather_code] || ['Condition unavailable', null];
        write($('weather-temp'), String(Math.round(current.temperature_2m)));
        write($('weather-condition'), description);
        drawWeather(kind, current.is_day !== 0);
        weatherDue = Date.now() + 15 * minute;
      } catch {
        if (weatherRequest !== controller) return;
        write($('weather-temp'), '—');
        write($('weather-condition'), 'Weather unavailable');
        drawWeather(null);
        weatherDue = Date.now() + minute;
      } finally {
        if (weatherRequest === controller) weatherRequest = null;
      }
    }

    function resetLocationWork() {
      locationVersion += 1;
      locationRequest?.abort();
      locationRequest = null;
      locate.disabled = false;
      return locationVersion;
    }

    function closeLocation() {
      resetLocationWork();
      dialog.close();
    }

    $('weather-place').addEventListener('click', () => {
      if (dialog.open) return;
      resetLocationWork();
      query.value = '';
      results.replaceChildren();
      write(status, '');
      dialog.showModal();
      query.focus();
    });
    $('location-close').addEventListener('click', closeLocation);
    dialog.addEventListener('close', () => { if (!dialog.open) resetLocationWork(); });
    query.addEventListener('input', () => {
      resetLocationWork();
      results.replaceChildren();
      write(status, '');
    });

    locate.addEventListener('click', () => {
      const version = resetLocationWork();
      results.replaceChildren();
      if (!navigator.geolocation) {
        write(status, 'Location unavailable. Search for a city.');
        return;
      }
      locate.disabled = true;
      write(status, 'Finding your location…');
      const current = () => version === locationVersion && dialog.open;
      const failure = (error) => {
        if (!current()) return;
        locate.disabled = false;
        write(status, error?.code === 1 ? 'Location permission denied. Search for a city.' :
          'Location unavailable. Search for a city.');
      };
      try {
        navigator.geolocation.getCurrentPosition(({ coords }) => {
          if (!current()) return;
          if (!validCoordinates(coords.latitude, coords.longitude)) { failure(); return; }
          selectPlace({ name: 'Current location', lat: Number(coords.latitude.toFixed(2)),
            lon: Number(coords.longitude.toFixed(2)), zone: null, gps: true });
          closeLocation();
        }, failure, { enableHighAccuracy: false, timeout: 10_000, maximumAge: 5 * minute });
      } catch { failure(); }
    });

    $('city-search').addEventListener('submit', async (event) => {
      event.preventDefault();
      const version = resetLocationWork();
      results.replaceChildren();
      const name = query.value.trim();
      if (name.length < 2) {
        write(status, 'Enter at least two characters.');
        return;
      }
      write(status, 'Searching…');
      const url = new URL('https://geocoding-api.open-meteo.com/v1/search');
      url.search = new URLSearchParams({ name, count: '8', language: 'en', format: 'json' });
      const controller = new AbortController();
      locationRequest = controller;
      const current = () => version === locationVersion && dialog.open;
      try {
        const data = await fetchJSON(url, controller);
        if (!current()) return;
        const matches = (data.results || []).filter((item) => typeof item.name === 'string' &&
          validCoordinates(item.latitude, item.longitude) && validZone(item.timezone));
        const labels = matches.map((item) => [item.name, item.admin1, item.country || item.country_code]);
        const baseLabels = labels.map(placeLabel);
        for (const [index, item] of matches.entries()) {
          const label = baseLabels.some((value, i) => i !== index && value === baseLabels[index]) ?
            placeLabel([item.name, item.admin2, ...labels[index].slice(1)]) : baseLabels[index];
          const button = html('button', '', label);
          button.type = 'button';
          button.addEventListener('click', () => {
            selectPlace({ name: item.name, label, lat: item.latitude, lon: item.longitude, zone: item.timezone });
            closeLocation();
          });
          const row = html('li');
          row.append(button);
          results.append(row);
        }
        write(status, matches.length ? '' : 'No cities found.');
      } catch {
        if (current()) write(status, 'City search unavailable. Try again.');
      } finally {
        if (locationRequest === controller) locationRequest = null;
      }
    });

    function placeLabel(parts) {
      return [...new Set(parts.filter(Boolean))].join(', ');
    }

    function localDay(instant, zone) {
      const { year, month, day: date } = parts(instant, zone, dateOptions);
      return Date.UTC(Number(year), Number(month) - 1, Number(date));
    }

    function startOfDay(civilDay, zone) {
      // Find the first instant in this civil date without assuming a fixed UTC offset.
      let low = civilDay - day;
      let high = civilDay + day;
      while (high - low > 1) {
        const middle = Math.floor((low + high) / 2);
        if (localDay(middle, zone) < civilDay) low = middle;
        else high = middle;
      }
      return high;
    }

    function sunForDay(civilDay, location) {
      const begin = startOfDay(civilDay, location.zone);
      const end = startOfDay(civilDay + day, location.zone);
      const observer = new Astronomy.Observer(location.lat, location.lon, 0);
      function event(start, direction, limitDays) {
        return Astronomy.SearchRiseSet(Astronomy.Body.Sun, observer, direction, new Date(start), limitDays)
          ?.date.getTime() ?? null;
      }
      function inDay(direction) {
        const crossing = event(begin, direction, (end - begin) / day);
        return crossing !== null && crossing >= begin && crossing < end ? crossing : null;
      }
      const rise = inDay(+1);
      const set = inDay(-1);
      const windows = [];
      if (rise !== null && set !== null && rise < set) windows.push([rise, set]);
      else {
        // Daylight can cross civil midnight. Polar days with no nearby pair have no marker.
        if (set !== null) windows.push([event(set, +1, -1), set]);
        if (rise !== null) windows.push([rise, event(rise, -1, 1)]);
      }
      return { civilDay, rise, set, windows };
    }

    function paintSun(now) {
      if (place.zone) {
        const civilDay = localDay(now, place.zone);
        if (!sun || sun.civilDay !== civilDay) sun = sunForDay(civilDay, place);
      }
      const label = (instant) => instant == null ? '—' : time(instant, place.zone);
      write($('sunrise'), label(sun?.rise));
      write($('sunset'), label(sun?.set));
      const ms = now.getTime();
      const window = sun?.windows.find(([rise, set]) => rise !== null && set !== null && rise <= ms && ms <= set);
      if (window) {
        const t = (ms - window[0]) / (window[1] - window[0]);
        // Quadratic Bézier: M 20 78 Q 160 -40 300 78, with time linear in x.
        marker.setAttribute('transform', `translate(${(20 + 280 * t).toFixed(2)} ${(78 - 236 * t * (1 - t)).toFixed(2)})`);
        marker.removeAttribute('visibility');
      } else {
        marker.setAttribute('visibility', 'hidden');
      }
    }

    function paintMoon(now) {
      const bucket = Math.floor(now / minute);
      if (moonMinute === bucket) return;
      moonMinute = bucket;
      const angle = Astronomy.MoonPhase(now);
      const fraction = Math.max(0, Math.min(1, Astronomy.Illumination(Astronomy.Body.Moon, now).phase_fraction));
      let phase;
      if (angle < 6 || angle >= 354) phase = 'New Moon';
      else if (angle < 84) phase = 'Waxing Crescent';
      else if (angle < 96) phase = 'First Quarter';
      else if (angle < 174) phase = 'Waxing Gibbous';
      else if (angle < 186) phase = 'Full Moon';
      else if (angle < 264) phase = 'Waning Gibbous';
      else if (angle < 276) phase = 'Last Quarter';
      else phase = 'Waning Crescent';
      write($('moon-phase'), phase);
      write($('moon-percent'), `${Math.round(100 * fraction)}%`);

      // Limb is a semicircle. The projected terminator has horizontal radius r × |1 − 2f|.
      const wax = angle < 180;
      const rx = 49 * Math.abs(1 - 2 * fraction);
      const sweep = Number(wax === (fraction >= 0.5));
      const terminator = rx < 0.0001 ? 'L 64 15' : `A ${rx.toFixed(5)} 49 0 0 ${sweep} 64 15`;
      $('moon-lit').setAttribute('d', `M 64 15 A 49 49 0 0 ${Number(wax)} 64 113 ${terminator} Z`);
    }

    function tick() {
      const now = new Date();
      const zone = deviceZone();
      const local = parts(now, zone, { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
        ...timeOptions, timeZoneName: 'short' });
      write($('day'), local.day);
      write($('month'), local.month);
      write($('weekday'), local.weekday);
      write($('year'), local.year);
      write($('local-time'), `${local.hour}:${local.minute}`);
      write($('local-zone'), local.timeZoneName);
      for (const { city, clockTime, offset } of clocks) {
        const cityTime = parts(now, city.zone, { ...timeOptions, timeZoneName: 'shortOffset' });
        write(clockTime, `${cityTime.hour}:${cityTime.minute}`);
        write(offset, cityTime.timeZoneName.replace(/^GMT/, 'UTC'));
      }
      paintSun(now);
      paintMoon(now);
    }

    function wake() {
      if (document.hidden) return;
      tick();
      refreshWeather();
    }

    renderPlace();
    tick();
    refreshWeather(true);
    setInterval(() => { if (!document.hidden) tick(); }, 1000);
    setInterval(() => refreshWeather(), minute);
    window.addEventListener('focus', wake);
    window.addEventListener('pageshow', wake);
    document.addEventListener('visibilitychange', wake);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
