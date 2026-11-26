    const clockKey = 'home-new-tab.city-clocks.v1';
    const clockGrid = $('clocks');
    const clockList = $('city-clock-list');
    const addClockButton = $('add-city-clock');
    let addingClock = false;
    let clockStorageAvailable = true;

    function sameCity(first, second) {
      return first.name === second.name &&
        Math.abs(first.lat - second.lat) < 0.1 && Math.abs(first.lon - second.lon) < 0.1;
    }

    function readClocks() {
      if (!clockStorageAvailable) return cities;
      try {
        const saved = JSON.parse(localStorage.getItem(clockKey));
        if (Array.isArray(saved) && saved.every((city) => city &&
            typeof city.name === 'string' && city.name.trim() &&
            validCoordinates(city.lat, city.lon) && validZone(city.zone))) return saved;
      } catch { /* Use the current roster if storage is unavailable. */ return cities; }
      return defaultCities;
    }

    function renderClocks() {
      clocks = cities.map(createClock);
      clockGrid.style.setProperty('--clock-count', clocks.length);
      clockGrid.replaceChildren(...clocks.map(({ button }) => button));

      clockList.replaceChildren(...cities.map((city, index) => {
        const row = html('li');
        const name = city.label || city.name;
        const remove = html('button', '', 'Remove');
        remove.type = 'button';
        remove.setAttribute('aria-label', `Remove ${name}`);
        remove.addEventListener('click', () => editClocks(() => {
          const remaining = readClocks().filter((entry) => !sameCity(entry, city));
          saveClocks(remaining);
          const next = clockList.children[Math.min(index, remaining.length - 1)]?.lastElementChild;
          (next || addClockButton).focus();
        }));
        row.append(html('span', '', name), remove);
        return row;
      }));
      $('city-clocks-empty').hidden = cities.length > 0;
    }

    function updateClocks(next) {
      cities = next;
      const removedExplored = explored && !cities.some((city) => sameCity(city, explored));
      if (removedExplored) explored = null;
      renderClocks();
      renderGlobe(Boolean(removedExplored));
      if (removedExplored) switchForecast();
      tick();
    }

    function saveClocks(next) {
      try {
        localStorage.setItem(clockKey, JSON.stringify(next));
      } catch { clockStorageAvailable = false; }
      updateClocks(next);
    }

    function editClocks(edit) {
      // Serialize edits across tabs where Web Locks are available.
      return navigator.locks ? navigator.locks.request(clockKey, edit) : edit();
    }

    function addClock(city) {
      const roster = readClocks();
      if (roster.some((entry) => sameCity(entry, city))) return false;
      saveClocks([...roster, city]);
      return true;
    }

    addClockButton.addEventListener('click', () => openLocation(true));
    window.addEventListener('storage', (event) => {
      if (event.storageArea === localStorage && (event.key === clockKey || event.key === null)) {
        updateClocks(readClocks());
      }
    });
    cities = readClocks();
    renderClocks();
