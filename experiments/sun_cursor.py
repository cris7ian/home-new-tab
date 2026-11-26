"""Show progress along the daylight or overnight arc."""


def solar_cursor(js):
    start = js.index('    function paintSun(now) {')
    end = js.index('    function paintMoon(now) {', start)
    anchor = '      return { civilDay, rise, set, windows };'
    if js.count(anchor) != 1:
        raise ValueError('Expected one solar-day result')
    js = js[:start] + CURSOR + js[end:]
    return js.replace(anchor, '''      // Start each night at a sunset and pair it with the next nearby sunrise.
      const nightWindows = [event(begin, -1, -1), set]
        .filter((sunset) => sunset !== null)
        .map((sunset) => [sunset, event(sunset, +1, 1)]);
      return { civilDay, rise, set, windows, nightWindows };''')


CURSOR = '''    function paintSun(now) {
      const view = displayedPlace();
      const zone = view?.zone || deviceZone();
      if (view) {
        const civilDay = localDay(now, zone);
        if (!sun || sun.civilDay !== civilDay || sun.zone !== zone) {
          sun = { ...sunForDay(civilDay, { ...view, zone }), zone };
        }
      }
      const ms = now.getTime();
      const contains = ([start, end]) => start !== null && end !== null && start <= ms && ms < end;
      const daylight = sun?.windows.find(contains);
      const night = daylight ? null : sun?.nightWindows.find(contains);
      const label = instant => instant == null ? '—' : time(instant, zone);
      paintTime($('sunrise'), label(night ? night[1] : sun?.rise));
      paintTime($('sunset'), label(night ? night[0] : sun?.set));

      const interval = daylight || night;
      const caption = $('night-progress');
      if (!interval) {
        marker.setAttribute('visibility', 'hidden');
        marker.removeAttribute('data-state');
        write(caption, sun ? 'No complete solar cycle nearby' : '');
        return;
      }
      const [start, end] = interval;
      const progress = (ms - start) / (end - start);
      showCursor(progress, night ? 'night' : 'day');
      const remaining = Math.ceil((end - ms) / minute);
      const hours = Math.floor(remaining / 60);
      const minutes = remaining % 60;
      write(caption, night ? `${hours ? `${hours}h ` : ''}${minutes}m to sunrise` : '');
    }

    function showCursor(t, state) {
      const x = 20 + 280 * t;
      const height = Math.max(17, 236 * t * (1 - t));
      marker.setAttribute('transform', `translate(${x.toFixed(2)} ${(78 - height).toFixed(2)})`);
      marker.setAttribute('data-state', state);
      marker.removeAttribute('visibility');
    }

'''
