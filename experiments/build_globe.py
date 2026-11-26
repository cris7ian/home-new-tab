"""Build the three LAN previews and the unpacked Chrome extension. Does not touch production."""
from base64 import b64encode
import html
import json
from pathlib import Path
import re

from local_weather import local_weather

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXT = ROOT / 'extension'
PREVIEW = HERE / 'preview-local'
SRC = ROOT / 'src'
VENDOR = ROOT / 'vendor'
GLOBE = HERE / 'globe'
SOLAR = HERE / 'solar'
DESIGNS = {'atlas': 'Atlas', 'orbital': 'Orbital', 'grid': 'Grid'}


def read(path):
    return path.read_text(encoding='utf-8')


def change(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected a single template anchor: {old}')
    return text.replace(old, new)


def font(name, path, weight=500, style='normal'):
    data = b64encode(path.read_bytes()).decode('ascii')
    return f"@font-face{{font-family:'{name}';src:url(data:font/woff2;base64,{data}) format('woff2');font-style:{style};font-weight:{weight};font-display:swap}}"


def css():
    f = HERE / 'fonts'
    return '\n'.join((font('Newsreader', f / 'newsreader.woff2'),
        font('Newsreader', f / 'newsreader-italic.woff2', style='italic'),
        font('Space Grotesk', f / 'space.woff2'), font('Barlow Condensed', f / 'barlow.woff2', 600),
        font('IBM Plex Mono', f / 'plex.woff2', 400), font('DM Mono', VENDOR / 'dm-mono.woff2', 400),
        read(SRC / 'style.css'), read(HERE / 'variants.css'), read(SOLAR / 'solar.css')))


def app():
    js = read(SRC / 'app.js')
    # Keep the flat public site independent. The new dashboard shares its data logic.
    result = change(change(change(change(change(change(js,
        "hour: '2-digit', minute: '2-digit', hourCycle: 'h23'", "hour: 'numeric', minute: '2-digit', hourCycle: 'h12'"),
        "const time = (instant, zone) => formatter(zone, timeOptions).format(instant);",
        "const time = (instant, zone) => clockText(parts(instant, zone, timeOptions));\n    const clockText = ({hour, minute, dayPeriod}) => `${hour}:${minute} ${dayPeriod.toUpperCase()}`;\n    function paintTime(node, value) {\n      const [clock, period] = value.split(' ');\n      if (node.dataset.value === value) return;\n      node.dataset.value = value;\n      node.replaceChildren(document.createTextNode(clock), ...(period ? [document.createTextNode(' '), html('span', 'meridiem', period)] : []));\n    }"),
        "$('map-pins').replaceChildren(...pins);", "$('map-pins').replaceChildren(...pins);\n      window.AlmanacGlobe?.setPlace(place, cities);"),
        "write($('local-time'), `${local.hour}:${local.minute}`);", "paintTime($('local-time'), clockText(local));"),
        "write(clockTime, `${cityTime.hour}:${cityTime.minute}`);", "paintTime(clockTime, clockText(cityTime));"),
        "locate.addEventListener('click', () => {", "locate.addEventListener('click', async () => {\n      if (globalThis.chrome?.runtime?.id && chrome.permissions) {\n        try {\n          const granted = await chrome.permissions.request({ permissions: ['geolocation'] });\n          if (!dialog.open) return;\n          if (!granted) { write(status, 'Location permission denied. Search for a city.'); return; }\n        } catch { write(status, 'Location unavailable. Search for a city.'); return; }\n      }" )
    for event in ('sunrise', 'sunset'):
        instant = 'rise' if event == 'sunrise' else 'set'
        result = change(result, f"write($('{event}'), label(sun?.{instant}));", f"paintTime($('{event}'), label(sun?.{instant}));")
    return local_weather(result)


GLOBE_MARKUP = '''<div id="globe-stage"><canvas id="globe" aria-label="Interactive Earth with time zones, day and night, and ISS position. Use arrow keys to rotate." tabindex="0"></canvas></div><div class="globe-controls"><div><button id="globe-home" type="button" aria-label="Center selected city" title="Center selected city"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 1v4m0 14v4M1 12h4m14 0h4"/></svg></button><button id="globe-iss" type="button" aria-label="Center the International Space Station" title="Center the International Space Station">ISS</button></div><span id="iss-status"></span></div><svg hidden aria-hidden="true"><g id="map-pins"></g></svg>'''
SETTINGS_BUTTON = '''<button type="button" class="icon-button" id="settings-open" aria-label="Appearance and data sources" title="Appearance and data sources" aria-haspopup="dialog"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="M5 6h14M5 12h14M5 18h14"/><path d="M9 4v4m6 2v4m-4 2v4" stroke-width="2"/></svg></button>'''
SETTINGS = '''<dialog id="settings" aria-labelledby="settings-label"><div class="settings-title"><h2 id="settings-label">Settings</h2><button class="icon-button" type="button" id="settings-close" aria-label="Close settings">×</button></div><label for="appearance">Appearance</label><select id="appearance"><option value="atlas">Atlas</option><option value="orbital">Orbital</option><option value="grid">Grid</option></select><details><summary>Data sources</summary><p>Weather by <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo</a> (<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>). Temperatures are rounded. City search uses <a href="https://www.geonames.org/" target="_blank" rel="noopener noreferrer">GeoNames</a> via Open-Meteo.</p><p>ISS positions by <a href="https://wheretheiss.at/" target="_blank" rel="noopener noreferrer">Where the ISS at?</a>. Boundaries by Natural Earth.</p></details></dialog>'''


def page(design, styles, scripts, fixed=False):
    source = read(SRC / 'page.html')
    fixed_attr = ' data-fixed-design="true"' if fixed else ''
    source = change(source, '<html lang="en">', f'<html lang="en" data-design="{design}"{fixed_attr}>')
    source = change(source, '<style>/* @FONTS@ */\n/* @CSS@ */</style>', styles)
    globe = GLOBE_MARKUP.replace('id="globe-home"', 'id="globe-home" data-managed="true"').replace('Center selected city', 'Return to my location')
    source = change(source, '<!-- @MAP@ -->', globe)
    source = change(source, '<span id="place-name">Madrid</span>', '<span id="place-name">Set location</span>')
    source = change(source, '  </main>', read(SOLAR / 'panel.html') + '\n  </main>')
    source = change(source, 'stroke-width=".85"><circle r="8.6"', 'stroke-width=".85"><circle class="sun-halo" r="10.2" stroke-dasharray="1 2"/><circle r="8.6"')
    source = change(source, 'stroke-width=".7"><circle r="7"', 'stroke-width=".7"><circle class="sun-halo" r="9.6" fill="none" stroke-dasharray="1 2"/><circle r="7"')
    settings_button = SETTINGS_BUTTON.replace('Appearance and data sources', 'Data sources') if fixed else SETTINGS_BUTTON
    source = change(source, '<span class="eyebrow zone" id="local-zone"></span>', f'<div></div><div class="masthead-right"><span class="eyebrow zone" id="local-zone"></span>{settings_button}</div>')
    source = change(source, '<footer class="credits"><a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo</a></footer>', '')
    settings = SETTINGS if not fixed else re.sub(r'<label for="appearance">.*?</select>', '', SETTINGS)
    source = change(source, '<script>/* @ASTRONOMY@ */</script>\n<script>/* @APP@ */</script>', settings + '\n' + scripts)
    return source


def main():
    EXT.mkdir(exist_ok=True)
    PREVIEW.mkdir(exist_ok=True)
    assets = {'appearance.js': read(HERE / 'appearance.js'), 'astronomy.js': read(VENDOR / 'astronomy.browser.min.js')}
    for name in json.loads(read(GLOBE / 'scripts.json')):
        name_path = Path(name)
        if name_path.is_absolute() or '..' in name_path.parts or name_path.name in assets:
            raise ValueError(f'Invalid or duplicate globe asset: {name}')
        assets[name_path.name] = read(GLOBE / name_path)
    assets['dashboard.js'] = app()
    assets['solar.js'] = read(SOLAR / 'solar.js')
    style = css()
    licenses = [*sorted((HERE / 'fonts').glob('*-OFL.txt')), VENDOR / 'dm-mono-OFL.txt', *sorted(GLOBE.glob('*.LICENSE'))]
    notices = 'Natural Earth v5.1.2 map data: public domain.\n\n' + '\n\n'.join(f'{p.name}\n{read(p)}' for p in licenses)
    (EXT / 'NOTICES.txt').write_text(notices, encoding='utf-8')
    for name, value in assets.items():
        if re.search(r'</script', value, re.I):
            raise ValueError(f'Script terminator in {name}')
        (EXT / name).write_text(value, encoding='utf-8')
    (EXT / 'home.css').write_text(style, encoding='utf-8')
    (EXT / 'manifest.json').write_text(read(HERE / 'manifest.json'), encoding='utf-8')
    (EXT / 'newtab.html').write_text(page('grid', '<link rel="stylesheet" href="home.css">', '\n'.join(f'<script defer src="{name}"></script>' for name in assets), fixed=True), encoding='utf-8')
    inline = '\n'.join(f'<script>\n{value}\n</script>' for value in assets.values())
    footer = '\n<!--\n' + notices.replace('--', '—') + '\n-->\n'
    (PREVIEW / 'grid-release.html').write_text(page('grid', f'<style>{style}</style>', inline, fixed=True) + footer, encoding='utf-8')
    for design in DESIGNS:
        (PREVIEW / f'{design}.html').write_text(page(design, f'<style>{style}</style>', inline) + footer, encoding='utf-8')
    links = ''.join(f'<li><a href="{name}.html?design={name}">{html.escape(label)}</a></li>' for name, label in DESIGNS.items())
    (PREVIEW / 'index.html').write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Home — Proposals</title><style>body{{margin:9vh auto;width:min(80%,600px);font:24px/1.8 Georgia;background:#fafafa;color:#111}}a{{color:inherit}}li{{border-top:1px solid #ccc;padding:8px}}ul{{padding:0;list-style:none}}</style><h1>Home</h1><ul>{links}</ul></html>', encoding='utf-8')
    print('Built 3 proposals and extension/ (production unchanged)')


if __name__ == '__main__':
    main()
