# Home New Tab

![Globe-first dashboard with local weather, Moon and world clocks](docs/preview.png)

## Install in Chrome on macOS

1. Open the [v0.0.7 release](https://github.com/cris7ian/home-new-tab/releases/tag/v0.0.7) while signed in to GitHub.
2. Download **`home-new-tab-v0.0.7.zip`**. Extract it to a folder you plan to keep.
3. Open `chrome://extensions` in your regular Chrome profile.
4. Enable **Developer mode** and select **Load unpacked**.
5. Select the extracted **`extension`** folder. It contains `manifest.json`.
6. Press **⌘T**. If Chrome asks whether to keep the change, select **Keep it**.

Select a city clock to rotate the globe and view that city’s weather and sun. Select the target icon to return to your location, or select **ISS** to follow the station. In Weather, choose **Use my location** to let Chrome detect where you are, or pick a city manually. Chrome may show a location permission warning at installation. Home does not request device coordinates until you choose **Use my location** in the dashboard. Incognito new tabs are not overridden.

Open **Settings → Theme** to choose **System**, **Light**, or **Dark**. System follows your device appearance.

Open **Settings → City clocks** to add or remove cities from the bottom row. Your roster is saved in your browser.

The Sun moves along the arc from sunrise to sunset. At night, the Moon icon shows the current lunar phase, and its position shows progress from sunset to sunrise. A countdown shows the time until sunrise. A city selected manually stays selected until you choose **Use my location** again. Nearby city labels are resolved on-device and are approximate.

Keep the extracted folder on your Mac. To update an unpacked installation, replace its files without changing the folder path. Click **Reload** at `chrome://extensions` and accept the new location permission if Chrome asks. If Chrome disabled the extension during the update, enable it again. For a store installation, Chrome manages updates.

## Build the extension and previews

Run `python3 experiments/build_globe.py`. This updates the unpacked `extension/` package and the pages in `experiments/preview-local/`, but does not change the public site. `globe.html` is the web release artifact. The extension contains its scripts, fonts and map; weather, city search and ISS positions need an internet connection. No account or API keys are needed to use it.

## Website

The date and clock use the device timezone. Weather and solar times follow the selected city, or your location when no other city is selected.

## Preview

```sh
python3 experiments/build_globe.py
python3 -m http.server 4174 --bind 127.0.0.1 --directory experiments/preview-local
```

Open `http://localhost:4174/globe.html`. To preview on a trusted local network, bind the server to its LAN address instead. Browser permissions disable automatic location on plain HTTP except for loopback; use city search in that case. The page rounds your coordinates before sending them to the weather provider. Your last location choice stays in your browser.

The website does not change Chrome settings. The installed extension replaces Chrome’s normal new tab and works without the website. The solar-system code in `experiments/solar/` is a retired experiment, not part of the current build.

## Production

`https://home.salsaparapizza.com/` serves `public/` through production-server's Caddy origin. The site was registered with `newsite home --from [production-directory]`.

Push to `main` to update the website. GitHub Actions tests and builds the project before the `production-server-home-new-tab` runner publishes the dashboard and the [privacy policy](https://home.salsaparapizza.com/privacy.html). Pull requests run checks but do not deploy.

To redeploy the current `main`, run **CI and deploy → Run workflow** in GitHub Actions, or use `gh workflow run ci.yml --ref main`. Check the [deployed commit](https://home.salsaparapizza.com/deployment.json) after the run succeeds. This workflow does not publish Chrome extension releases.

**`public/` is live.** Do not run the legacy `build.py` against the production checkout.

## Chrome Web Store

The current release has two ZIPs. `home-new-tab-v0.0.7.zip` is for manual installation and contains an `extension/` folder. `home-new-tab-web-store-0.0.7.zip` is for the Developer Dashboard and has `manifest.json` at the ZIP root. Uploading the ZIP to the dashboard and submitting it for review are separate from publishing a GitHub release.

From the repo root, prepare a Store package and listing screenshots from a committed release:

```sh
uv run --with playwright --with pillow python experiments/store/prepare.py \
  --ref v0.0.7 --out experiments/artifacts/store-v0.0.7 \
  --chromium /path/to/chromium
```

## Sources

- [Natural Earth](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/timezones/) (public domain). Boundaries are a simplified reference layer; city clocks use the browser's timezone rules.
- [Open-Meteo](https://open-meteo.com/) for weather and place search.
- [Where the ISS at?](https://wheretheiss.at/) for live ISS positions.
- [GeoNames cities5000](https://download.geonames.org/export/dump/) ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)) for on-device nearby place labels. The bundled extract retains names and simplified coordinates.
- [Astronomy Engine](https://github.com/cosinekitty/astronomy) 2.1.19 (MIT) for solar events and lunar phases.
- [NASA’s Scientific Visualization Studio](https://svs.gsfc.nasa.gov/5001/) for the Lunar Reconnaissance Orbiter Moon mosaic. Resized and contrast-adjusted for the phase illustration.
- [Barlow Condensed](https://fonts.google.com/specimen/Barlow+Condensed) and [IBM Plex Mono](https://fonts.google.com/specimen/IBM+Plex+Mono), under the SIL Open Font License.
