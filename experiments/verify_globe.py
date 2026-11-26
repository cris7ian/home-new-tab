"""Run `uv run --with playwright python experiments/verify_globe.py` after build."""
import argparse
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
    expect(page.locator('#solar-system')).to_be_visible()


def status(page):
    expect(page.locator('#globe-iss')).to_be_enabled(timeout=17000)
    expect(page.locator('#iss-status')).to_contain_text('live', timeout=17000)


def city_rotation(page):
    tokyo = page.get_by_role('button', name=re.compile('Tokyo'))
    before = page.locator('#globe').evaluate('(el) => el.toDataURL()')
    local = page.locator('#place-name').inner_text()
    tokyo.click()
    expect(tokyo).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#place-name')).to_have_text(local)
    page.wait_for_function('(before) => document.querySelector("#globe").toDataURL() !== before', arg=before, timeout=4000)
    page.locator('#globe-home').click()
    expect(tokyo).to_have_attribute('aria-pressed', 'false')
    expect(page.locator('#place-name')).to_have_text(local)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chromium', type=Path)
    parser.add_argument('--web-url', help='Also smoke test a deployed Grid page')
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
                print('Unpacked MV3: Chrome new-tab override, fixed Grid, sources panel, and persistent weather location')
    assert not errors, errors


if __name__ == '__main__':
    main()
