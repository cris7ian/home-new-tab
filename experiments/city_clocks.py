"""Add configurable clocks to the centered dashboard."""
from pathlib import Path


def city_clocks(js, change):
    js = change(js,
        "{ name: 'São Paulo', lat: -23.55, lon: -46.63, zone: 'America/Sao_Paulo' }",
        "{ name: 'Caracas', lat: 10.48, lon: -66.88, zone: 'America/Caracas' }")
    js = change(js, 'const cities = [', 'const defaultCities = [')
    js = change(js, 'const madrid = cities.find', 'let cities = defaultCities;\n    const madrid = defaultCities.find')
    js = change(js, '    const clocks = cities.map((city) => {', '    function createClock(city) {')
    js = change(js, """      return { city, button, clockTime, offset };
    });
    $('clocks').replaceChildren(...clocks.map(({ button }) => button));""", """      if (city.label) button.title = city.label;
      return { city, button, clockTime, offset };
    }

    let clocks;""")
    js = change(js, """cities.find((city) => city.name === location.name &&
        Math.abs(city.lat - location.lat) < 0.1 && Math.abs(city.lon - location.lon) < 0.1)""",
        'cities.find((city) => sameCity(city, location))')
    js = change(js, """    function openLocation() {
      if (dialog.open) return;
      resetLocationWork();""", """    function openLocation(forClock = false) {
      if (dialog.open) return;
      resetLocationWork();
      addingClock = forClock;
      write($('location-title'), forClock ? 'Add city clock' : 'Location');
      $('location-close').setAttribute('aria-label', forClock ? 'Close city clock search' : 'Close location selector');
      locate.hidden = forClock;""")
    js = change(js, "$('weather-place').addEventListener('click', openLocation);",
        "$('weather-place').addEventListener('click', () => openLocation());")
    js = change(js, "          button.addEventListener('click', () => {\n            if (!current()) return;",
        "          button.addEventListener('click', async () => {\n            if (!current()) return;")
    js = change(js, """            const manual = { name: item.name, label, lat: item.latitude, lon: item.longitude, zone: item.timezone };
            locationMode('manual');""", """            const manual = { name: item.name, label, lat: item.latitude, lon: item.longitude, zone: item.timezone };
            if (addingClock) {
              const added = await editClocks(() => addClock(manual));
              if (!current()) return;
              if (added) closeLocation();
              else write(status, `${label} is already in your city clocks.`);
              return;
            }
            locationMode('manual');""")
    js = change(js, "          const button = html('button', '', label);",
        "          const button = html('button', '', addingClock ? `Add ${label}` : label);")
    js = change(js, """      for (const { city, clockTime, offset } of clocks) {
        const cityTime = parts(now, city.zone, { ...timeOptions, timeZoneName: 'shortOffset' });
        paintTime(clockTime, clockText(cityTime));
        write(offset, cityTime.timeZoneName.replace(/^GMT/, 'UTC'));
      }""", '      paintClocks(now);')
    controls = Path(__file__).with_name('city_clocks.js').read_text(encoding='utf-8')
    return change(js, '    renderHome();\n    renderGlobe();\n    tick();', controls + """
    renderHome();
    renderGlobe();
    tick();""")
