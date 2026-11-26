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
    expect(page).to_have_title('Home')
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
    expect(page.locator('#globe-iss')).to_be_enabled(timeout=17000)
    expect(page.locator('#iss-status')).to_contain_text('live', timeout=17000)


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
                assert page.evaluate('location.protocol') == 'chrome-extension:'
                assert page.evaluate('Boolean(chrome.runtime.id)')
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
    assert not errors, errors


if __name__ == '__main__':
    main()
