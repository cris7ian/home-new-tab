# Home New Tab

A quieter new tab, with a view of the world. Home brings together an interactive globe, world clocks, weather, sunrise and sunset, and the Moon’s current phase. Follow the International Space Station, explore a city, or make the dashboard your own with your favorite clocks and theme.

![Globe-first dashboard with local weather, Moon and world clocks](docs/preview.png)

[Try Home in your browser](https://home.salsaparapizza.com/) · [Privacy policy](https://home.salsaparapizza.com/privacy.html)

## Install in Chrome

1. Open the [release](https://github.com/cris7ian/home-new-tab/releases/tag/v1.0.0) while signed in to GitHub.
2. Download `home-new-tab-v1.0.0.zip` and extract it to a folder you plan to keep.
3. Open `chrome://extensions`, enable **Developer mode**, and select **Load unpacked**.
4. Select the extracted `extension` folder.
5. Open a new tab and select **Keep it** if Chrome asks.

To update a manual installation, replace the files in the same folder and select **Reload** in `chrome://extensions`.

Choose a city for its weather and solar times, or select **Use my location** to use your device location. Chrome may show a location permission warning during installation, but Home does not read your location until you opt in. Weather, city search, and live ISS positions need an internet connection. No account or API key is needed to use Home.

## Develop

Build the extension and start a local preview:

```sh
python3 experiments/build_globe.py
python3 -m http.server 4174 --bind 127.0.0.1 --directory experiments/preview-local
```

Open [localhost:4174/globe.html](http://localhost:4174/globe.html). With the preview server running, run the tests with:

```sh
python3 -m unittest discover -s experiments
uv run --with playwright python experiments/verify_globe.py --chromium /path/to/chromium
```

The browser tests cover both the preview and the Chrome new-tab override. For hosting and release details, see [production](docs/production.md).

## Credits

- [Natural Earth](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/timezones/) for map boundaries (public domain).
- [Open-Meteo](https://open-meteo.com/) for weather and place search, and [Where the ISS at?](https://wheretheiss.at/) for ISS positions.
- [GeoNames cities5000](https://download.geonames.org/export/dump/) ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)) for nearby place labels. The bundled extract retains names and simplified coordinates.
- [Astronomy Engine](https://github.com/cosinekitty/astronomy) 2.1.19 (MIT) for solar events and lunar phases.
- [NASA’s Scientific Visualization Studio](https://svs.gsfc.nasa.gov/5001/) for the Moon mosaic, resized and contrast-adjusted.
- [Barlow Condensed](https://fonts.google.com/specimen/Barlow+Condensed) and [IBM Plex Mono](https://fonts.google.com/specimen/IBM+Plex+Mono), under the SIL Open Font License.
