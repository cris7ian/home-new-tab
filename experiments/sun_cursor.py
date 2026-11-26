"""Show the daylight path and mark its nearest endpoint at night."""


def solar_cursor(js):
    start = js.index('    function paintSun(now) {')
    end = js.index('    function paintMoon(now) {', start)
    anchor = '      return { civilDay, rise, set, windows };'
    if js.count(anchor) != 1:
        raise ValueError('Expected one solar-day result')
    js = js[:start] + CURSOR + js[end:]
    return js.replace(anchor, '''      const nightWindows = [[event(begin, -1, -2), rise], [set, event(end, +1, 2)]];
      return { civilDay, rise, set, windows, nightWindows, begin, end, observer };''')


CURSOR = '''    function paintSun(now) {
      const view = displayedPlace();
      const zone = view?.zone || deviceZone();
      if (view) {
        const civilDay = localDay(now, zone);
        if (!sun || sun.civilDay !== civilDay || sun.zone !== zone) {
          sun = { ...sunForDay(civilDay, { ...view, zone }), zone };
        }
      }
      const label = instant => instant == null ? '—' : time(instant, zone);
      paintTime($('sunrise'), label(sun?.rise));
      paintTime($('sunset'), label(sun?.set));
      if (!sun) {
        marker.setAttribute('visibility', 'hidden');
        marker.removeAttribute('data-state');
        return;
      }
      const ms = now.getTime();
      const contains = ([a, b]) => a !== null && b !== null && b > a && a <= ms && ms <= b;
      const day = sun.windows.find(contains);
      const night = sun.nightWindows.find(contains);
      if (day) {
        const [a, b] = day;
        const t = (ms - a) / (b - a);
        showCursor(t, 'day', Math.max(17, 236 * t * (1 - t)));
      } else if (night) {
        // Mark the relevant end of the daylight arc; do not plot a fake
        // above-horizon position for a Sun we cannot currently see.
        showCursor(night[1] === sun.rise ? 0 : 1, 'night', 17);
      } else {
        // Polar days and nights can have no crossing for weeks.
        const eq = Astronomy.Equator(Astronomy.Body.Sun, now, sun.observer, true, true);
        const hor = Astronomy.Horizon(now, sun.observer, eq.ra, eq.dec, 'normal');
        if (hor.altitude < 0) {
          marker.setAttribute('visibility', 'hidden');
          marker.removeAttribute('data-state');
          return;
        }
        const t = 0.5 - Math.sin(hor.azimuth * Math.PI / 180) * 0.38;
        showCursor(t, 'day', 17 + 35 * Math.min(1, hor.altitude / 60));
      }
    }

    function showCursor(t, state, height) {
      const x = 20 + 280 * t;
      marker.setAttribute('transform', `translate(${x.toFixed(2)} ${(78 - height).toFixed(2)})`);
      marker.setAttribute('data-state', state);
      marker.removeAttribute('visibility');
    }

'''
