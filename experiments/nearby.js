/* Nearby names from GeoNames cities5000 (CC BY 4.0), reduced to position and name. */
(() => {
  'use strict';
  const source = '/* @CITY_GZIP@ */';
  let cities;
  async function load() {
    const compressed = Uint8Array.from(atob(source), c => c.charCodeAt(0));
    const stream = new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Response(stream).json();
  }
  window.HomeNearbyCity = async (lat, lon, accuracy) => {
    if (!Number.isFinite(accuracy) || accuracy > 8_000) return '';
    try {
      const places = await (cities ??= load());
      const rad = Math.PI / 180;
      // Find the first plausible latitude in the sorted table. Then use great-circle distance.
      let low = 0, high = places.length;
      const latitudeWindow = .2;
      while (low < high) {
        const middle = (low + high) >>> 1;
        if (places[middle][0] < lat - latitudeWindow) low = middle + 1;
        else high = middle;
      }
      let closest = '', distance = 18;
      for (let i = low; i < places.length && places[i][0] <= lat + latitudeWindow; i++) {
        const [y, x, name] = places[i];
        const a = Math.sin((y - lat) * rad / 2) ** 2 + Math.cos(lat * rad) * Math.cos(y * rad) * Math.sin((x - lon) * rad / 2) ** 2;
        const km = 12_742 * Math.asin(Math.sqrt(Math.min(1, a)));
        if (km >= distance) continue;
        closest = name;
        distance = km;
      }
      return closest;
    } catch { return ''; }
  };
})();
