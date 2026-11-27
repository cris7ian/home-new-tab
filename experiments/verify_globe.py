"""Run `uv run --with playwright python experiments/verify_globe.py` after build."""
import argparse
from datetime import datetime
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from playwright.sync_api import Error, expect, sync_playwright

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / 'artifacts'
CLK = re.compile(r'^\d{1,2}:\d{2} (AM|PM)$')
NUMBER = re.compile(r'^-?\d+$')
DESIGNS = {'atlas': 'Newsreader', 'orbital': 'Space Grotesk', 'grid': 'Barlow Condensed'}
BASE = 'http://127.0.0.1:4174/'


def manual_weather(page):
    page.locator('#weather-place').click()
    page.locator('#city-query').fill('Madrid')
    page.locator('#city-search button[type=submit]').click()
    page.locator('#city-results button').filter(has_text=re.compile('Madrid.*Spain')).first.click(timeout=17000)
    expect(page.locator('#place-name')).to_contain_text('Madrid')
    expect(page.locator('#weather-temp')).to_have_text(NUMBER, timeout=17000)


def collect_errors(page, errors):
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' and 'Content Security Policy' in message.text else None)


def wait_frame(page):
    page.evaluate('document.fonts.ready')
    page.evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')


def check(page, design):
    expect(page).to_have_title('Pale Blue Dot Tab')
    expect(page.locator('html')).to_have_attribute('data-design', design)
    expect(page.locator('#local-time')).to_have_text(CLK)
    expect(page.locator('#sunrise')).to_have_text(CLK)
    expect(page.locator('#sunset')).to_have_text(CLK)
    expect(page.locator('#clocks button')).to_have_count(8)
    for clock in page.locator('.clock-time').all():
        expect(clock).to_have_text(CLK)
    expect(page.locator('#weather-temp')).to_have_text(NUMBER, timeout=17000)
    expect(page.get_by_role('link', name='Open-Meteo', exact=True)).not_to_be_visible()
    wait_frame(page)
    assert page.evaluate('document.documentElement.scrollWidth === innerWidth')
    assert page.evaluate("document.fonts.check('" + ('600' if design == 'grid' else '500') + " 32px \"" + DESIGNS[design] + "\"')")
    assert page.locator('#globe').evaluate('(el) => el.width > 150 && el.height > 150')
    assert re.search(r'\d', page.locator('#moon-percent').inner_text())
    expect(page.locator('#solar-system')).to_have_count(0)
    if page.locator('html').get_attribute('data-presentation') == 'center':
        expect(page.locator('#year-progress, table')).to_have_count(0)
        assert page.locator('#clocks').bounding_box()['y'] >= page.locator('#globe').bounding_box()['y'] + page.locator('#globe').bounding_box()['height']
        return
    expect(page.locator('#year-progress')).to_be_visible()
    expect(page.locator('.year-month')).to_have_count(12)
    expect(page.locator('.year-square[data-state=today]')).to_have_count(1)
    assert page.locator('.year-square').count() in (365, 366)
    atlas = page.locator('.atlas').bounding_box()
    year = page.locator('#year-progress').bounding_box()
    moon = page.locator('.lunar-art').bounding_box()
    phase = page.locator('#moon-phase').bounding_box()
    assert phase['y'] >= moon['y'] + moon['height']
    icon = page.locator('#weather-icon').bounding_box()
    width = page.evaluate('innerWidth')
    if width > 900:
        assert abs(atlas['y'] - year['y']) < 2 and year['x'] >= atlas['x'] + atlas['width'] - 2
        assert moon['width'] >= 155 and icon['width'] >= 72
    else:
        assert year['y'] >= atlas['y'] + atlas['height'] - 2 and moon['width'] >= 155 and icon['width'] >= 43


def status(page):
    expect(page.locator('#globe-iss')).to_have_attribute('aria-disabled', 'false', timeout=17000)
    expect(page.locator('#iss-status')).to_be_empty()


def globe_focus(page):
    globe = page.locator('#globe')
    globe.click()
    expect(globe).to_be_focused()
    expect(globe).to_have_css('outline-style', 'none')
    page.keyboard.press('ArrowRight')
    expect(globe).to_have_css('outline-style', 'solid')
    globe.click()
    expect(globe).to_have_css('outline-style', 'none')
    page.keyboard.press('Tab')
    expect(page.locator('#globe-home')).to_be_focused()
    page.keyboard.press('Shift+Tab')
    expect(globe).to_be_focused()
    expect(globe).to_have_css('outline-style', 'solid')


def leap_year(browser):
    page = browser.new_page(viewport={'width': 320, 'height': 640}, timezone_id='America/New_York')
    page.clock.install(time=datetime.fromisoformat('2028-02-29T23:59:45-05:00'))
    page.goto(f'{BASE}grid-release.html')
    expect(page.locator('.year-square')).to_have_count(366)
    expect(page.locator('.year-count')).to_have_text('060 / 366')
    expect(page.locator('.year-square[data-state=today]')).to_have_attribute('title', '29 February 2028')
    page.clock.fast_forward(35_000)
    expect(page.locator('.year-count')).to_have_text('061 / 366')
    expect(page.locator('.year-square[data-state=today]')).to_have_attribute('title', '1 March 2028')
    assert page.evaluate('document.documentElement.scrollWidth === innerWidth')
    page.close()


def type_proposal(browser, errors):
    for width, height in ((1440, 900), (390, 844), (320, 720)):
        page = browser.new_page(viewport={'width': width, 'height': height}, timezone_id='Europe/Madrid')
        collect_errors(page, errors)
        assert page.goto(f'{BASE}type.html').ok
        manual_weather(page)
        expect(page.locator('#clocks .clock')).to_have_count(8)
        expect(page.locator('#clocks button')).to_have_count(0)
        expect(page.locator('#globe')).to_have_count(0)
        expect(page.locator('.sun-pictogram')).to_have_count(2)
        expect(page.locator('#sunset')).to_have_text(CLK)
        expect(page.locator('.year-percent')).to_have_text(re.compile(r'^\d+%$'))
        expect(page.locator('.year-days')).to_be_hidden()
        wait_frame(page)
        problems = page.evaluate('''() => [...document.querySelectorAll('.masthead, main *')]
          .filter(el => el instanceof HTMLElement && el.getClientRects().length)
          .filter(el => ['Top','Right','Bottom','Left'].some(side => parseFloat(getComputedStyle(el)[`border${side}Width`]) > 0))
          .map(el => el.className)''')
        assert not problems, problems
        assert page.evaluate('document.documentElement.scrollWidth === innerWidth')
        if width != 320:
            page.screenshot(path=ARTIFACTS / f'type-{width}.png', full_page=True)
        page.close()


def globe_proposal(browser, errors):
    for width, height in ((1440, 900), (390, 844), (320, 720)):
        page = browser.new_page(viewport={'width': width, 'height': height}, timezone_id='Europe/Madrid')
        collect_errors(page, errors)
        assert page.goto(f'{BASE}globe.html').ok
        manual_weather(page)
        expect(page.locator('#year-progress, table')).to_have_count(0)
        expect(page.locator('#clocks button')).to_have_count(8)
        expect(page.locator('#sunrise')).to_have_text(CLK)
        expect(page.locator('#sunset')).to_have_text(CLK)
        status(page)
        wait_frame(page)
        assert page.evaluate('document.documentElement.scrollWidth === innerWidth')
        globe = page.locator('#globe').bounding_box()
        cities = page.locator('#clocks').bounding_box()
        weather = page.locator('.weather').bounding_box()
        sun = page.locator('.sun').bounding_box()
        moon = page.locator('.moon').bounding_box()
        phase = page.locator('#moon-phase')
        assert phase.evaluate('el => getComputedStyle(el).whiteSpace === "nowrap" && el.scrollWidth <= el.clientWidth && parseFloat(getComputedStyle(el).fontSize) <= 23')
        assert sun['y'] >= weather['y'] + weather['height'] - 1
        assert cities['y'] >= globe['y'] + globe['height']
        if width > 650:
            assert weather['x'] < globe['x'] < moon['x']
            assert abs(globe['x'] + globe['width'] / 2 - width / 2) < 15
            assert cities['y'] + cities['height'] <= height - 34
        else:
            assert moon['y'] < globe['y'] and weather['y'] < globe['y']
        if width != 320:
            page.screenshot(path=ARTIFACTS / f'globe-{width}.png', full_page=True)
        if width == 1440:
            city_rotation(page)
        page.close()


def city_rotation(page):
    tokyo = page.locator('#clocks').get_by_role('button', name=re.compile('Tokyo'))
    before = page.locator('#globe').evaluate('(el) => el.toDataURL()')
    local = page.locator('#place-name').inner_text()
    explore_weather = page.locator('html').get_attribute('data-presentation') == 'center'
    home_sunrise = page.locator('#sunrise').inner_text()
    if explore_weather:
        with page.expect_request(lambda req: 'latitude=35.68' in req.url and 'longitude=139.69' in req.url):
            tokyo.click()
        expect(page.locator('#weather-temp')).to_have_text(NUMBER, timeout=17000)
        expect(page.locator('#place-name')).to_have_text('Tokyo')
        assert page.locator('#sunrise').inner_text() != home_sunrise
    else:
        tokyo.click()
        expect(page.locator('#place-name')).to_have_text(local)
    expect(tokyo).to_have_attribute('aria-pressed', 'true')
    page.wait_for_function('(before) => document.querySelector("#globe").toDataURL() !== before', arg=before, timeout=4000)
    page.locator('#globe-home').click()
    expect(tokyo).to_have_attribute('aria-pressed', 'false')
    expect(page.locator('#place-name')).to_have_text(local)
    expect(page.locator('#sunrise')).to_have_text(home_sunrise)


def configurable_clocks(page, peer=None):
    page.clock.set_fixed_time(datetime.fromisoformat('2026-11-26T12:00:00+00:00'))
    page.route('https://api.open-meteo.com/v1/forecast?**', lambda route: route.fulfill(json={
        'timezone': 'Asia/Kathmandu', 'current': {'temperature_2m': 19, 'weather_code': 0, 'is_day': 1},
    }))
    page.route('https://geocoding-api.open-meteo.com/v1/search?**', lambda route: route.fulfill(json={
        'results': [
            {'name': 'Kathmandu', 'country': 'Nepal', 'latitude': 27.7172,
             'longitude': 85.324, 'timezone': 'Asia/Kathmandu'},
            {'name': 'Caracas', 'country': 'Venezuela', 'latitude': 10.488,
             'longitude': -66.879, 'timezone': 'America/Caracas'},
        ],
    }))
    clocks = page.locator('#clocks')
    expect(clocks.locator('.clock-city')).to_have_text([
        'Los Angeles', 'New York', 'Caracas', 'London', 'Madrid', 'Dubai', 'Tokyo', 'Sydney',
    ])
    expect(clocks.get_by_role('button', name=re.compile('Caracas')).locator('.clock-time')).to_have_text(
        re.compile(r'^0?8:00 AM$'))
    home = page.locator('#place-name').inner_text()
    page.locator('#settings-open').click()
    page.get_by_role('button', name='Add city', exact=True).click()
    expect(page.get_by_role('button', name='Use my location')).to_be_hidden()
    page.locator('#city-query').fill('Kathmandu')
    page.locator('#city-search button[type=submit]').click()
    page.get_by_role('button', name='Add Caracas, Venezuela').click()
    expect(page.locator('#location-status')).to_contain_text('already in your city clocks')
    page.get_by_role('button', name='Add Kathmandu, Nepal').click()
    expect(page.locator('#add-city-clock')).to_be_focused()
    expect(page.locator('#settings')).to_be_visible()
    expect(clocks.locator('.clock-city')).to_have_text([
        'Los Angeles', 'New York', 'Caracas', 'London', 'Madrid', 'Dubai', 'Kathmandu', 'Tokyo', 'Sydney',
    ])
    expect(page.locator('#city-clock-list li span').nth(6)).to_have_text('Kathmandu, Nepal')
    if peer:
        expect(peer.locator('#clocks .clock-city').nth(6)).to_have_text('Kathmandu')
    page.get_by_role('button', name='Close settings').click()
    expect(page.locator('#place-name')).to_have_text(home)
    assert page.evaluate('document.documentElement.scrollWidth === innerWidth')
    page.reload()
    kathmandu = clocks.get_by_role('button', name=re.compile('Kathmandu'))
    expect(kathmandu.locator('.clock-time')).to_have_text(re.compile(r'^0?5:45 PM$'))
    with page.expect_request(lambda req: 'latitude=27.72' in req.url and 'longitude=85.32' in req.url):
        kathmandu.click()
    expect(page.locator('#place-name')).to_have_text('Kathmandu')
    expect(page.locator('#weather-place')).to_have_attribute('aria-label', 'Change weather location: Kathmandu, Nepal')
    expect(page.locator('#weather-temp')).to_have_text('19')
    page.locator('#settings-open').click()
    page.get_by_role('button', name='Remove Kathmandu, Nepal').click()
    expect(page.locator('#place-name')).to_have_text(home)
    remove_buttons = page.locator('#city-clock-list button')
    for remaining in range(7, -1, -1):
        remove_buttons.first.click()
        expect(remove_buttons).to_have_count(remaining)
    expect(page.locator('#city-clocks-empty')).to_be_visible()
    expect(clocks).to_be_hidden()
    page.reload()
    expect(clocks.locator('.clock-city')).to_have_count(0)


def city_clock_sort(browser):
    page = browser.new_page()
    page.clock.install(time=datetime.fromisoformat('2026-10-03T16:29:45+00:00'))
    page.add_init_script("""localStorage.setItem('home-new-tab.city-clocks.v1', JSON.stringify([
      {name: 'Brisbane', lat: -27.47, lon: 153.03, zone: 'Australia/Brisbane'},
      {name: 'Adelaide', lat: -34.93, lon: 138.60, zone: 'Australia/Adelaide'},
      {name: 'St. John’s', lat: 47.56, lon: -52.71, zone: 'America/St_Johns'},
      {name: 'Caracas', lat: 10.48, lon: -66.88, zone: 'America/Caracas'},
      {name: 'Accra', lat: 5.60, lon: -0.19, zone: 'Africa/Accra'}
    ]));""")
    page.route('https://api.open-meteo.com/v1/forecast?**', lambda route: route.fulfill(json={
        'current': {'temperature_2m': 19, 'weather_code': 0, 'is_day': 0},
    }))
    page.goto(f'{BASE}globe.html')
    clocks = page.locator('#clocks .clock-city')
    expect(clocks).to_have_text(['Caracas', 'St. John’s', 'Accra', 'Adelaide', 'Brisbane'])
    adelaide = page.locator('#clocks').get_by_role('button', name=re.compile('Adelaide'))
    adelaide.click()
    page.clock.fast_forward(30_000)
    expect(clocks).to_have_text(['Caracas', 'St. John’s', 'Accra', 'Brisbane', 'Adelaide'])
    expect(adelaide).to_be_focused()
    expect(adelaide).to_have_attribute('aria-pressed', 'true')
    page.close()


def clock_proposals(browser, errors):
    for name in ('shoulders', 'meridian', 'inline'):
        for width, height in ((1440, 900), (390, 844), (320, 720)):
            page = browser.new_page(viewport={'width': width, 'height': height}, timezone_id='Europe/Madrid')
            collect_errors(page, errors)
            assert page.goto(f'{BASE}globe-{name}.html').ok
            manual_weather(page)
            check(page, 'grid')
            clock = page.locator('.current-clock').bounding_box()
            date = page.locator('.date-block').bounding_box()
            globe = page.locator('#globe').bounding_box()
            assert date['x'] < clock['x']
            if name == 'meridian':
                assert page.locator('.date-line .current-clock').count() == 1
                assert date['x'] + date['width'] <= clock['x']
                assert date['y'] + date['height'] <= globe['y']
                assert clock['y'] + clock['height'] <= globe['y']
                assert page.locator('.date-line h1').evaluate('el => parseFloat(getComputedStyle(el).fontSize) >= 35')
                expect(page.locator('#moon-surface')).to_have_attribute('href', re.compile('^data:image/jpeg;base64,'))
            else:
                assert clock['y'] < globe['y']
            if width == 1440:
                expect(page.locator('#local-zone')).not_to_be_empty()
                status(page)
                page.screenshot(path=ARTIFACTS / f'clock-{name}.png', full_page=True)
                city_rotation(page)
            if width == 390:
                page.screenshot(path=ARTIFACTS / f'clock-{name}-mobile.png', full_page=True)
            page.close()


def theme_behavior(page):
    root = page.locator('html')
    page.emulate_media(color_scheme='light')
    expect(root).to_have_attribute('data-theme', 'light')
    page.locator('#settings-open').click()
    picker = page.locator('#theme')
    expect(picker).to_have_value('system')
    before = page.locator('#globe').evaluate('(el) => el.toDataURL()')
    page.emulate_media(color_scheme='dark')
    expect(root).to_have_attribute('data-theme', 'dark')
    page.wait_for_function('(before) => document.querySelector("#globe").toDataURL() !== before', arg=before)
    assert page.locator('body').evaluate('el => getComputedStyle(el).backgroundColor') == 'rgb(20, 20, 20)'
    picker.select_option('light')
    expect(root).to_have_attribute('data-theme', 'light')
    picker.select_option('dark')
    page.emulate_media(color_scheme='light')
    expect(root).to_have_attribute('data-theme', 'dark')
    page.reload()
    expect(root).to_have_attribute('data-theme', 'dark')
    page.locator('#settings-open').click()
    expect(picker).to_have_value('dark')
    picker.select_option('system')
    expect(root).to_have_attribute('data-theme', 'light')
    page.keyboard.press('Escape')


COLOR_THEMES = {
    'gruvbox': 'rgb(40, 40, 40)',
    'deep-ocean': 'rgb(7, 24, 39)',
    'tokyo-night': 'rgb(26, 27, 38)',
    'dracula': 'rgb(40, 42, 54)',
    'oxblood': 'rgb(17, 13, 16)',
    'unit-01': 'rgb(29, 19, 42)',
}


def color_themes(page, peer=None):
    root = page.locator('html')
    picker = page.locator('#theme')
    globe = page.locator('#globe')
    page.locator('#settings-open').click()
    previous = globe.evaluate('(el) => el.toDataURL()')
    for name, background in COLOR_THEMES.items():
        picker.select_option(name)
        expect(root).to_have_attribute('data-theme', name)
        expect(page.locator('body')).to_have_css('background-color', background)
        expect(page.locator('#settings')).to_have_css('background-color', background)
        expect(picker).to_have_css('color-scheme', 'dark')
        page.wait_for_function('(before) => document.querySelector("#globe").toDataURL() !== before', arg=previous)
        previous = globe.evaluate('(el) => el.toDataURL()')
        if peer:
            expect(peer.locator('html')).to_have_attribute('data-theme', name)
    page.emulate_media(color_scheme='light')
    page.reload()
    expect(root).to_have_attribute('data-theme', 'unit-01')
    page.locator('#settings-open').click()
    expect(picker).to_have_value('unit-01')
    picker.select_option('system')
    expect(root).to_have_attribute('data-theme', 'light')
    if peer:
        expect(peer.locator('html')).to_have_attribute('data-theme', 'light')
    page.keyboard.press('Escape')


def early_theme(browser):
    for system, saved, expected in (
        ('dark', 'system', 'dark'),
        ('light', 'dark', 'dark'),
        ('dark', 'light', 'light'),
        ('light', 'tokyo-night', 'tokyo-night'),
        ('light', 'invalid', 'light'),
    ):
        page = browser.new_page(color_scheme=system)
        page.add_init_script(f"localStorage.setItem('home-new-tab.theme.v1', '{saved}');")
        url = f'{BASE}globe.html'

        def early_markup(route):
            response = route.fetch()
            head, body = response.text().split('</head>', 1)
            route.fulfill(response=response, body=head + '</head>' + body.split('<script', 1)[0])

        page.route(url, early_markup)
        assert page.goto(url).ok
        background = {'dark': 'rgb(20, 20, 20)', 'light': 'rgb(250, 250, 250)', **COLOR_THEMES}[expected]
        assert page.locator('body').evaluate('el => getComputedStyle(el).backgroundColor') == background, (system, saved)
        assert page.locator('html').evaluate('el => getComputedStyle(el).backgroundColor') == background, (system, saved)
        expect(page.locator('html')).to_have_attribute('data-theme', expected)
        page.close()


def stable_clock(browser):
    page = browser.new_page(viewport={'width': 1440, 'height': 900}, timezone_id='Europe/Madrid')
    page.clock.install(time=datetime.fromisoformat('2028-03-01T09:59:45+01:00'))
    page.goto(f'{BASE}globe.html')
    readout = page.locator('#local-time')
    expect(readout).to_have_text('09:59 AM')
    wait_frame(page)
    assert 'IBM Plex Mono' in readout.evaluate('el => getComputedStyle(el).fontFamily')
    before = readout.bounding_box()
    date = page.locator('.date-block').bounding_box()
    page.clock.fast_forward(17_000)
    expect(readout).to_have_text('10:00 AM')
    assert readout.bounding_box() == before and page.locator('.date-block').bounding_box() == date
    page.close()


def geo_sun_regression(browser, errors):
    context = browser.new_context(timezone_id='Europe/Madrid',
        geolocation={'latitude': 41.3874, 'longitude': 2.1686, 'accuracy': 30}, permissions=['geolocation'])
    page = context.new_page()
    collect_errors(page, errors)
    page.clock.install(time=datetime.fromisoformat('2026-11-26T16:00:00+01:00'))
    with page.expect_request(lambda request: 'latitude=41.39' in request.url and 'longitude=2.17' in request.url, timeout=16000):
        assert page.goto(f'{BASE}globe.html').ok
    expect(page.locator('#place-name')).to_have_text('Near Barcelona')
    sun = page.locator('#sun-marker')
    countdown = page.locator('#night-progress')
    sunrise = page.locator('#sunrise')
    sunset = page.locator('#sunset')

    def cursor_x():
        return float(sun.get_attribute('transform').split()[0].removeprefix('translate('))

    def minutes_left():
        match = re.fullmatch(r'(?:(\d+)h )?(\d+)m to sunrise', countdown.inner_text())
        assert match
        return 60 * int(match[1] or 0) + int(match[2])

    expect(sun).to_have_attribute('data-state', 'day')
    expect(countdown).to_be_hidden()
    assert sunrise.bounding_box()['x'] < sunset.bounding_box()['x']
    page.clock.fast_forward(4 * 3_600_000)
    expect(sun).to_have_attribute('data-state', 'night')
    expect(sun).to_be_visible()
    expect(sun.locator('.sun-night-glyph')).to_be_visible()
    expect(sun.locator('.sun-halo')).to_be_hidden()
    assert sunset.bounding_box()['x'] < sunrise.bounding_box()['x']
    start_x = cursor_x()
    start_minutes = minutes_left()
    assert 20 < start_x < 160
    page.clock.fast_forward(3_600_000)
    assert cursor_x() > start_x
    assert abs(minutes_left() - (start_minutes - 60)) <= 1
    page.clock.fast_forward((3 * 60 - 1) * 60_000)
    before_midnight = cursor_x()
    bounds = (sunset.inner_text(), sunrise.inner_text())
    page.clock.fast_forward(2 * 60_000)
    expect(sun).to_have_attribute('data-state', 'night')
    assert 0 < cursor_x() - before_midnight < 2
    assert bounds == (sunset.inner_text(), sunrise.inner_text())
    page.clock.fast_forward(6 * 3_600_000)
    expect(sun).to_have_attribute('data-state', 'night')
    assert 240 < cursor_x() < 300
    page.clock.fast_forward(6 * 3_600_000)
    expect(sun).to_have_attribute('data-state', 'day')
    expect(countdown).to_be_hidden()
    expect(sun.locator('.sun-night-glyph')).to_be_hidden()
    expect(sun.locator('.sun-halo')).to_be_visible()
    assert sunrise.bounding_box()['x'] < sunset.bounding_box()['x']
    assert float(sun.get_attribute('transform').split()[1].strip(')')) < 78
    first = sun.get_attribute('transform')
    page.clock.fast_forward(3_600_000)
    expect(sun).not_to_have_attribute('transform', first)
    polar_search = re.compile(r'geocoding-api\.open-meteo\.com/v1/search\?name=Longyearbyen&')
    page.route(polar_search, lambda route: route.fulfill(json={'results': [
        {'name': 'Longyearbyen', 'country': 'Svalbard and Jan Mayen', 'latitude': 78.22,
         'longitude': 15.65, 'timezone': 'Arctic/Longyearbyen'},
    ]}))
    page.locator('#weather-place').click()
    page.locator('#city-query').fill('Longyearbyen')
    page.locator('#city-search button[type=submit]').click()
    page.get_by_role('button', name='Longyearbyen, Svalbard and Jan Mayen').click()
    expect(page.locator('#place-name')).to_have_text('Longyearbyen')
    expect(countdown).to_have_text('No complete solar cycle nearby')
    expect(sun).to_be_hidden()
    expect(sunrise).to_have_text('—')
    expect(sunset).to_have_text('—')
    manual_weather(page)
    page.reload()
    expect(page.locator('#place-name')).to_contain_text('Madrid')
    assert page.evaluate('localStorage.getItem("home-new-tab.location-mode.v1")') == 'manual'
    context.close()


def website_link(browser):
    expected = (
        ('Add to Chrome',
         'https://chromewebstore.google.com/detail/home-new-tab/pgeahicgbpcfobknhbgjhlldjpapbgol'),
        ('GitHub', 'https://github.com/cris7ian/pale-blue-dot-tab#install-in-chrome'),
    )
    for width, height in ((1440, 900), (320, 720)):
        page = browser.new_page(viewport={'width': width, 'height': height})
        page.goto(f'{BASE}globe.html')
        boxes = []
        for name, href in expected:
            link = page.get_by_role('link', name=name, exact=True)
            expect(link).to_be_visible()
            expect(link).to_have_attribute('href', href)
            expect(link).to_have_attribute('target', '_blank')
            expect(link).to_have_attribute('rel', 'noopener noreferrer')
            boxes.append(link.bounding_box())
        assert page.evaluate('document.documentElement.scrollWidth === innerWidth')
        settings_box = page.locator('#settings-open').bounding_box()
        assert boxes[0]['x'] + boxes[0]['width'] <= boxes[1]['x']
        assert boxes[-1]['x'] + boxes[-1]['width'] <= settings_box['x']
        page.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chromium', type=Path)
    parser.add_argument('--web-url', help='Also smoke test the deployed globe page')
    args = parser.parse_args()
    browser_args = {'executable_path': str(args.chromium)} if args.chromium else {'channel': 'chromium'}
    ARTIFACTS.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**browser_args)
        early_theme(browser)
        theme_page = browser.new_page(viewport={'width': 320, 'height': 720}, color_scheme='light')
        theme_page.goto(f'{BASE}globe.html')
        color_themes(theme_page)
        theme_page.close()
        print('Website: all six color palettes, globe redraw, mobile settings and persistence')
        for design in DESIGNS:
            desktop = browser.new_context(viewport={'width': 1440, 'height': 900}, timezone_id='Europe/Madrid')
            page = desktop.new_page()
            collect_errors(page, errors)
            page.goto(f'{BASE}{design}.html?design={design}')
            manual_weather(page)
            check(page, design)
            status(page)
            page.screenshot(path=ARTIFACTS / f'{design}-desktop.png', full_page=True)

            city_rotation(page)
            page.locator('#globe-iss').click()
            page.locator('#globe-home').click()
            desktop.close()
            mobile = browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True, timezone_id='Europe/Madrid')
            phone = mobile.new_page()
            collect_errors(phone, errors)
            phone.goto(f'{BASE}{design}.html?design={design}')
            manual_weather(phone)
            check(phone, design)
            status(phone)
            phone.screenshot(path=ARTIFACTS / f'{design}-mobile.png', full_page=True)

            mobile.close()
            print(f'{design}: desktop, mobile, 12-hour labels, live data and city rotation')
        for url in (f'{BASE}grid-release.html', args.web_url):
            if not url:
                continue
            console_count = len(errors)
            location = browser.new_context(viewport={'width': 390, 'height': 844},
                has_touch=True, is_mobile=True, timezone_id='Europe/Madrid',
                geolocation={'latitude': 41.3874, 'longitude': 2.1686}, permissions=['geolocation'])
            page = location.new_page()
            collect_errors(page, errors)
            with page.expect_request(lambda r: 'latitude=41.39' in r.url and 'longitude=2.17' in r.url, timeout=17000):
                assert page.goto(url).ok
            expect(page.locator('#weather-temp')).to_have_text(NUMBER, timeout=17000)
            check(page, 'grid')
            city_rotation(page)
            assert len(errors) == console_count
            location.close()
            print(f'{url}: Grid release, auto-location with prior permission and unchanged local weather during globe exploration')
        leap_year(browser)
        print('Year grid: 366 squares on leap year, local midnight rollover, and 320 px fit')
        type_proposal(browser, errors)
        print('Type & icons: live data, no panel borders, and no overflow at 1440, 390 and 320 px')
        globe_proposal(browser, errors)
        print('Globe proposal: centered Earth, live ISS, city rotation, bottom clocks, no tables or year grid')
        clock_proposals(browser, errors)
        print('Clock layouts: three placements, desktop and mobile fit, city weather/sun and return to home')
        stable_clock(browser)
        print('Monospace clock: no date or time layout shift from 09:59 to 10:00')
        geo_sun_regression(browser, errors)
        print('Location and sun: nearby city label, overnight countdown and midnight continuity, daytime movement and polar night')
        website_link(browser)
        print('Website: installation link is visible on desktop and mobile')
        page = browser.new_page(viewport={'width': 320, 'height': 720})
        collect_errors(page, errors)
        page.goto(f'{BASE}globe.html')
        configurable_clocks(page)
        page.close()
        city_clock_sort(browser)
        print('City clocks: Caracas time, add, duplicate prevention, weather, removal and persistence on mobile')
        browser.close()
        extension = str(HERE.parent / 'extension')
        with TemporaryDirectory(prefix='home-chrome-') as profile:
            with p.chromium.launch_persistent_context(profile, **browser_args, timezone_id='Europe/Madrid',
                    args=[f'--disable-extensions-except={extension}', f'--load-extension={extension}']) as ctx:
                page = ctx.new_page()
                collect_errors(page, errors)
                try:
                    page.goto('chrome://newtab/', wait_until='commit', timeout=12000)
                except Error as error:
                    if 'ERR_ABORTED' not in str(error):
                        raise
                page.wait_for_selector('#globe', timeout=15000)
                expect(page.locator('.masthead-link')).to_have_count(0)
                assert page.evaluate('location.protocol') == 'chrome-extension:'
                assert page.evaluate('Boolean(chrome.runtime.id)')
                assert page.evaluate('chrome.permissions.contains({permissions:["geolocation"]})')
                await_coords = {'latitude': 41.3874, 'longitude': 2.1686, 'accuracy': 30}
                ctx.set_geolocation(await_coords)
                page.reload()
                expect(page.locator('#place-name')).to_have_text('Set location')
                assert page.evaluate('localStorage.getItem("home-new-tab.location-mode.v1")') is None
                page.locator('#weather-place').click()
                page.locator('#locate').click()
                expect(page.locator('#place-name')).to_have_text('Near Barcelona', timeout=17000)
                page.reload()
                expect(page.locator('#place-name')).to_have_text('Near Barcelona', timeout=17000)
                print('Unpacked MV3: required Chrome geolocation works only after the user clicks Use my location')
                manual_weather(page)
                check(page, 'grid')
                status(page)
                city_rotation(page)
                theme_behavior(page)
                page.locator('#settings-open').click()
                page.locator('#settings summary').click()
                expect(page.get_by_role('link', name='Open-Meteo', exact=True)).to_be_visible()
                page.keyboard.press('Escape')
                second = ctx.new_page()
                try:
                    second.goto('chrome://newtab/', wait_until='commit', timeout=12000)
                except Error as error:
                    if 'ERR_ABORTED' not in str(error):
                        raise
                check(second, 'grid')
                expect(second.locator('#place-name')).to_contain_text('Madrid')
                print('Unpacked MV3: Chrome new-tab override, system and saved themes, globe redraw, and persistent weather location')
                page.emulate_media(color_scheme='light')
                color_themes(second, peer=page)
                print('Unpacked MV3: six color palettes redraw the globe and synchronize across new tabs')
                globe_focus(second)
                configurable_clocks(second, peer=page)
                print('Unpacked MV3: configurable city clocks and synchronization across new tabs')
    assert not errors, errors


if __name__ == '__main__':
    main()
