# Home New Tab

## Install in Chrome on macOS

1. Open [the private repository](https://github.com/cris7ian/home-new-tab) while signed in to GitHub.
2. Select **Code → Download ZIP**. Extract it to a folder you plan to keep.
3. Open `chrome://extensions` in your regular Chrome profile.
4. Enable **Developer mode** and select **Load unpacked**.
5. Select the **`extension`** folder inside the extracted folder, not the repository root.
6. Press **⌘T**. If Chrome asks whether to keep the change, select **Keep it**.

Use the sliders icon to switch between Atlas, Orbital and Grid. Select a city clock to rotate the globe. Select **ISS** to center the station. In Weather, select your city or choose **Use my location**. Chrome asks for location access only if you choose that option. Incognito new tabs are not overridden.

The folder must stay on your Mac. To update, replace its files with the newer version and click **Reload** at `chrome://extensions`.

## Build the extension and previews

Run `python3 experiments/build_globe.py`. This updates the unpacked `extension/` package and the pages in `experiments/preview-local/`, but does not change the public site. The extension contains its scripts, fonts and map; weather, city search and ISS positions need an internet connection. No account or API keys are needed.

## Original public website

A monochrome new-tab page. A static HTML file contains the map, fonts, and astronomy calculations. Weather forecasts and city search use Open-Meteo. The date and masthead clock use the device timezone. The selected city controls weather and solar times.

## Preview

```sh
python3 build.py
python3 -m http.server 4173 --bind 127.0.0.1 --directory public
```

Open `http://localhost:4173/`, or open `public/index.html` directly. To preview on a trusted local network, bind the server to its LAN address instead. Browser permissions normally disable automatic location on plain HTTP except for `localhost`; use city search in that case. When you use browser location, the page rounds the coordinates before sending them to the weather provider. The last location choice stays in your browser. The default is a preset city if its timezone matches the device; otherwise it is Madrid.

This project has no server-side application or runtime build dependencies. It does not change browser new-tab settings.

## Production

`https://home.salsaparapizza.com/` serves `public/` through production-server's Caddy origin. The site was registered with `newsite home --from [production-directory]`.

**`public/` is live.** Build future previews in a separate directory or project copy. Verify the preview before replacing the live `public/index.html`.

## Sources

- [Natural Earth](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/timezones/) (public domain). Boundaries are a simplified reference layer; city clocks use the browser's timezone rules.
- [Open-Meteo](https://open-meteo.com/) for weather and place search.
- [Astronomy Engine](https://github.com/cosinekitty/astronomy) 2.1.19 (MIT) for solar events and lunar phases.
- [Bodoni Moda](https://fonts.google.com/specimen/Bodoni+Moda) and [DM Mono](https://fonts.google.com/specimen/DM+Mono), under the SIL Open Font License.
