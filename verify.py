"""Browser checks. Run with `uv run --with playwright python verify.py`."""
import os
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = 'http://127.0.0.1:4173/'
LAN = os.environ.get('ALMANAC_LAN_URL', BASE)
SHOTS = Path(os.environ.get('ALMANAC_SCREENSHOTS', Path(__file__).resolve().parent / '.preview'))
SHOTS.mkdir(parents=True, exist_ok=True)
clock = re.compile(r'^\d\d:\d\d$')
number = re.compile(r'^-?\d+$')
errors = []


def visit(context, url):
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    response = page.goto(url)
    assert response and response.ok
    page.evaluate('document.fonts.ready')
    return page


def basics(page):
    expect(page).to_have_title('Home')
    expect(page.locator('.masthead')).not_to_contain_text('Almanac')
    expect(page.locator('#local-zone')).not_to_be_empty()
    expect(page.locator('#clocks button')).to_have_count(8)
    assert page.locator('#map-pins').locator('circle').count() >= 8
    for selector in ('#local-time', '#sunrise', '#sunset', '#clocks button:first-child .clock-time'):
        expect(page.locator(selector)).to_have_text(clock)
    expect(page.locator('#moon-percent')).to_have_text(re.compile(r'^\d{1,3}%$'))
    expect(page.locator('#moon-phase')).not_to_have_text('—')
    assert page.locator('#moon-lit').get_attribute('d') not in (None, '', 'M0 0')
    assert page.evaluate("document.fonts.check('500 30px Bodoni Moda')")
    assert page.evaluate('document.documentElement.scrollWidth === innerWidth')


with sync_playwright() as pw:
    options = {'executable_path': os.environ['CHROMIUM']} if 'CHROMIUM' in os.environ else {}
    browser = pw.chromium.launch(**options)
    desktop = browser.new_context(viewport={'width': 1440, 'height': 900}, timezone_id='Europe/Madrid')
    page = visit(desktop, BASE)
    basics(page)
    expect(page.locator('#weather-temp')).to_have_text(number, timeout=18000)
    expect(page.locator('#place-name')).to_have_text('Madrid')
    original_solar = page.locator('#sunrise').inner_text()
    page.screenshot(path=SHOTS / 'almanac-desktop.png', full_page=True)

    tokyo = page.locator('#clocks button').filter(has_text='Tokyo')
    tokyo.click()
    expect(page.locator('#place-name')).to_have_text('Tokyo')
    expect(page.locator('#weather-temp')).to_have_text(number, timeout=18000)
    assert page.locator('#sunrise').inner_text() != original_solar
    page.reload()
    expect(page.locator('#place-name')).to_have_text('Tokyo')
    expect(tokyo).to_have_attribute('aria-pressed', 'true')
    page.locator('#weather-place').click()
    expect(page.locator('#location-dialog')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#location-dialog')).not_to_be_visible()
    expect(page.locator('#weather-place')).to_be_focused()
    print('Desktop: live forecast, sun, moon, city selection, persistence and dialog keyboard handling')

    mobile = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2, timezone_id='Europe/Madrid')
    phone = visit(mobile, LAN)
    basics(phone)
    expect(phone.locator('#weather-temp')).to_have_text(number, timeout=18000)
    phone.screenshot(path=SHOTS / 'almanac-mobile.png', full_page=True)
    phone.locator('#weather-place').tap()
    phone.locator('#city-query').fill('Valencia')
    phone.locator('#city-search button[type=submit]').tap()
    result = phone.locator('#city-results button').filter(has_text='Valencia').first
    expect(result).to_be_visible(timeout=18000)
    result.tap()
    expect(phone.locator('#place-name')).to_contain_text('Valencia')
    expect(phone.locator('#weather-temp')).to_have_text(number, timeout=18000)
    assert phone.evaluate('document.documentElement.scrollWidth === innerWidth')
    print('Phone (390 px, touch emulation): no overflow; live city search and forecast via LAN')

    gps = browser.new_context(geolocation={'latitude': 41.3874, 'longitude': 2.1686}, permissions=['geolocation'], timezone_id='Europe/Madrid')
    page = visit(gps, BASE)
    page.locator('#weather-place').click()
    with page.expect_request(re.compile(r'api\.open-meteo\.com/v1/forecast\?'), timeout=18000) as request:
        page.locator('#locate').click()
    assert 'latitude=41.39' in request.value.url and 'longitude=2.17' in request.value.url, request.value.url
    expect(page.locator('#location-dialog')).not_to_be_visible()
    expect(page.locator('#weather-temp')).to_have_text(number, timeout=18000)
    print('Loopback secure context: browser geolocation with simulated coordinates and live forecast')

    offline = browser.new_context(viewport={'width': 320, 'height': 720}, timezone_id='Europe/Madrid')
    offline.route('https://**/*', lambda route: route.abort())
    small = visit(offline, BASE)
    basics(small)
    expect(small.locator('#weather-condition')).to_have_text(re.compile('unavailable', re.I), timeout=18000)
    print('Small phone (320 px): astronomy, map and clocks still work without the weather provider')

    portable = browser.new_context(timezone_id='Europe/Madrid')
    file_page = portable.new_page()
    file_page.on('pageerror', lambda error: errors.append(str(error)))
    file_page.clock.set_fixed_time(datetime.fromisoformat('2026-09-30T00:15:00+02:00'))
    file_page.goto((Path(__file__).resolve().parent / 'public' / 'index.html').as_uri())
    file_page.evaluate('document.fonts.ready')
    basics(file_page)
    expect(file_page.locator('#weather-temp')).to_have_text(number, timeout=18000)
    expect(file_page.locator('#sun-marker')).to_be_hidden()
    expect(file_page.locator('.sun-noon')).to_be_visible()
    file_page.clock.set_fixed_time(datetime.fromisoformat('2026-09-30T12:15:00+02:00'))
    expect(file_page.locator('#sun-marker')).to_be_visible()
    expect(file_page.locator('.sun-noon')).to_be_hidden()
    print('Standalone file: live weather and both day/night solar illustrations')

assert not errors, errors
print('No page errors')
