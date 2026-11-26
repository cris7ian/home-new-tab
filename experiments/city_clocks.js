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
      clocks = cities.map((city, rosterIndex) => {
        const row = html('li');
        const name = city.label || city.name;
        const remove = html('button', '', 'Remove');
        remove.type = 'button';
        remove.setAttribute('aria-label', `Remove ${name}`);
        remove.addEventListener('click', () => editClocks(() => {
          const index = clocks.findIndex((clock) => clock.row === row);
          const remaining = readClocks().filter((entry) => !sameCity(entry, city));
          saveClocks(remaining);
          const next = clockList.children[Math.min(index, remaining.length - 1)]?.lastElementChild;
          (next || addClockButton).focus();
        }));
        row.append(html('span', '', name), remove);
        return { ...createClock(city), row, rosterIndex };
      });
      clockGrid.style.setProperty('--clock-count', clocks.length);
      $('city-clocks-empty').hidden = cities.length > 0;
      paintClocks(new Date(), true);
    }

    function paintClocks(now, rosterChanged = false) {
      for (const clock of clocks) {
        const cityTime = parts(now, clock.city.zone, { ...timeOptions, timeZoneName: 'shortOffset' });
        // shortOffset in en-GB gives GMT, GMT+5:45, GMT-3:30, etc.
        const zone = cityTime.timeZoneName;
        const [hours, minutes = '0'] = zone.slice(4).split(':');
        clock.offsetMinutes = (zone[3] === '-' ? -1 : 1) * (Number(hours) * 60 + Number(minutes));
        paintTime(clock.clockTime, clockText(cityTime));
        write(clock.offset, zone.replace(/^GMT/, 'UTC'));
      }
      const compare = (a, b) => a.offsetMinutes - b.offsetMinutes || a.rosterIndex - b.rosterIndex;
      const outOfOrder = clocks.some((clock, index) => index > 0 && compare(clocks[index - 1], clock) > 0);
      if (!rosterChanged && !outOfOrder) return;
      if (outOfOrder) clocks.sort(compare);
      const focused = document.activeElement;
      clockGrid.replaceChildren(...clocks.map(({ button }) => button));
      clockList.replaceChildren(...clocks.map(({ row }) => row));
      if (clockGrid.contains(focused) || clockList.contains(focused)) focused.focus({ preventScroll: true });
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
