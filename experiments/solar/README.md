# Solar system panel

The plot is heliocentric and uses the mean ecliptic and equinox of J2000. It shows the view from ecliptic north: 0° points right and longitude increases counterclockwise. Only the angular positions represent the ephemeris. The circular guides, orbital radii, and body sizes are schematic.

The script uses Astronomy Engine `HelioVector` to get equatorial J2000 vectors and `Rotation_EQJ_ECL` to rotate them into the J2000 ecliptic. The browser clock supplies the observation instant. The header shows the local calendar date. The panel refreshes every 15 minutes while visible, and when returning to a visible tab after that interval or a date change.

Inline `panel.html` after the observatory. Include `solar.css` after the dashboard styles and `solar.js` after Astronomy Engine. The panel makes no network requests.
