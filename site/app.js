/* alkoholperkrona — map + rank list + filters + history + happy hour.
   No build step, no framework: the data files are tiny and the page is
   one screen. */

(async function () {
  "use strict";

  const FALLBACK_VOLUME_CL = 40; // rank volume-less beers as if 40 cl
  // Reference: a standard 33 cl lager at Systembolaget ≈ 15 kr ≈ 0.45 kr/cl.
  const SYSTEMBOLAGET_KR_PER_CL = 0.45;
  const WALK_M_PER_MIN = 80;

  // Price tiers (SEK): green ≤55, yellow 56-79, red ≥80. Stale or null beer = "stale".
  const tierOf = (v) => {
    if (v.stale || !v.cheapest_beer) return "stale";
    const p = v.cheapest_beer.price_sek;
    if (p <= 55) return "cheap";
    if (p <= 79) return "mid";
    return "expensive";
  };

  // ---------- data ----------

  const loadJson = async (url, fallback) => {
    try {
      const resp = await fetch(url, { cache: "no-store" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch {
      return fallback;
    }
  };

  const venues = await loadJson("./restaurants.json", null);
  if (!venues) {
    document.getElementById("ranks").innerHTML =
      '<li style="padding:16px;color:#9b988f">Kunde inte ladda prisdata. Försök igen senare.</li>';
    return;
  }
  const history = await loadJson("./history.json", {});
  const happyHours = await loadJson("./happy_hours.json", []);
  const hhById = new Map(happyHours.map((h) => [h.id, h]));

  const rankValue = (v) => {
    const b = v.cheapest_beer;
    if (!b) return Infinity;
    return b.kr_per_cl ?? b.price_sek / FALLBACK_VOLUME_CL;
  };

  const byValue = (a, b) => {
    if (!!a.stale !== !!b.stale) return a.stale ? 1 : -1;
    return rankValue(a) - rankValue(b);
  };

  const sortedByValue = [...venues].sort(byValue);
  const best = sortedByValue.find((v) => !v.stale && v.cheapest_beer) || null;

  // ---------- happy hour clock (Europe/Stockholm) ----------

  const WEEKDAYS = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 7 };
  const DAY_NAMES = ["", "mån", "tis", "ons", "tor", "fre", "lör", "sön"];

  function stockholmNow() {
    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/Stockholm",
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).formatToParts(new Date());
    const get = (t) => parts.find((p) => p.type === t)?.value || "";
    return { day: WEEKDAYS[get("weekday")] || 0, time: `${get("hour")}:${get("minute")}` };
  }

  function hhActive(hh) {
    if (!hh) return false;
    const { day, time } = stockholmNow();
    return hh.days.includes(day) && time >= hh.start && time < hh.end;
  }

  function hhLabel(hh) {
    const days = hh.days.map((d) => DAY_NAMES[d]);
    const contiguous =
      hh.days.length > 2 && hh.days.every((d, i) => i === 0 || d === hh.days[i - 1] + 1);
    const span = contiguous ? `${days[0]}–${days[days.length - 1]}` : days.join(", ");
    return `${span} ${hh.start}–${hh.end}`;
  }

  // ---------- stats ----------

  const fresh = venues.filter((v) => !v.stale && v.cheapest_beer);
  const cheapest = fresh.length
    ? Math.min(...fresh.map((v) => v.cheapest_beer.price_sek))
    : null;

  countUp(document.getElementById("stat-venues"), venues.length);
  if (cheapest !== null) countUp(document.getElementById("stat-cheapest"), cheapest);

  const newest = venues
    .map((v) => new Date(v.last_updated))
    .filter((d) => !Number.isNaN(d.getTime()))
    .sort((a, b) => b - a)[0];
  document.getElementById("stat-updated").textContent = newest ? relTime(newest) : "–";

  // ---------- map ----------

  const map = L.map("map", {
    zoomControl: false,
    attributionControl: true,
    minZoom: 11,
    maxZoom: 19,
  });
  L.control.zoom({ position: "bottomright" }).addTo(map);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(map);

  const markers = new Map();
  sortedByValue.forEach((v, i) => {
    const b = v.cheapest_beer;
    const isBest = best && v.id === best.id;
    const live = hhActive(hhById.get(v.id));
    const cls = ["bubble", `bubble--${tierOf(v)}`, isBest ? "bubble--best" : ""]
      .filter(Boolean)
      .join(" ");
    const label = b ? `${b.price_sek}:-` : "–";
    const crown = isBest ? '<span class="bubble__crown">👑</span>' : "";
    const beers = live ? '<span class="bubble__hh">🍻</span>' : "";
    const icon = L.divIcon({
      className: "price-marker",
      html: `<div class="${cls}" style="animation-delay:${200 + i * 60}ms">${crown}${beers}${esc(label)}</div>`,
      iconSize: [0, 0],
      iconAnchor: [0, 0],
      popupAnchor: [0, -46],
    });
    const m = L.marker([v.lat, v.lon], { icon, riseOnHover: true })
      .addTo(map)
      .bindPopup(() => popupHtml(v, isBest), { closeButton: true, maxWidth: 300 });
    m.on("popupopen", () => setActiveRow(v.id));
    m.on("popupclose", () => setActiveRow(null));
    markers.set(v.id, m);
  });

  const isMobile = () => window.matchMedia("(max-width: 880px)").matches;
  const panelPad = () =>
    parseInt(getComputedStyle(document.documentElement).getPropertyValue("--panel-w")) + 60 || 460;
  map.fitBounds(L.latLngBounds(venues.map((v) => [v.lat, v.lon])), {
    paddingTopLeft: isMobile() ? [30, 90] : [40, 90],
    paddingBottomRight: isMobile() ? [30, 120] : [panelPad(), 60],
  });

  // ---------- geolocation / "nära mig" ----------

  let userPos = null; // {lat, lon}
  let userMarker = null;
  let sortMode = "value"; // "value" | "distance"

  const haversineM = (a, b) => {
    const R = 6371000;
    const dLat = ((b.lat - a.lat) * Math.PI) / 180;
    const dLon = ((b.lon - a.lon) * Math.PI) / 180;
    const la1 = (a.lat * Math.PI) / 180;
    const la2 = (b.lat * Math.PI) / 180;
    const h =
      Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  };

  const distLabel = (m) => {
    const walk = Math.max(1, Math.round(m / WALK_M_PER_MIN));
    return m < 1000
      ? `${Math.round(m)} m · ~${walk} min`
      : `${(m / 1000).toFixed(1)} km · ~${walk} min`;
  };

  const locateBtn = document.getElementById("locate");
  locateBtn.addEventListener("click", () => {
    if (!navigator.geolocation) return;
    locateBtn.classList.add("locate--busy");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        userPos = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        locateBtn.classList.remove("locate--busy");
        locateBtn.classList.add("locate--on");
        document.getElementById("mode-distance").disabled = false;
        if (userMarker) userMarker.remove();
        userMarker = L.marker([userPos.lat, userPos.lon], {
          icon: L.divIcon({
            className: "",
            html: '<div class="you"><div class="you__dot"></div></div>',
            iconSize: [0, 0],
          }),
          interactive: false,
        }).addTo(map);
        setSortMode("distance");
        map.flyTo([userPos.lat, userPos.lon], 14, { duration: 0.8 });
      },
      () => locateBtn.classList.remove("locate--busy"),
      { enableHighAccuracy: true, timeout: 8000 },
    );
  });

  document.getElementById("mode-value").addEventListener("click", () => setSortMode("value"));
  document
    .getElementById("mode-distance")
    .addEventListener("click", () => setSortMode("distance"));

  function setSortMode(mode) {
    sortMode = mode;
    document.getElementById("mode-value").classList.toggle("seg--active", mode === "value");
    document
      .getElementById("mode-distance")
      .classList.toggle("seg--active", mode === "distance");
    render();
  }

  // ---------- filters ----------

  let tierFilter = "all"; // all | cheap | mid | expensive | hh
  let hideStale = false;
  let query = "";

  if (happyHours.length === 0) {
    document.querySelector('[data-filter="hh"]')?.remove();
  }

  document.getElementById("filters").addEventListener("click", (e) => {
    const chip = e.target.closest(".fchip");
    if (!chip) return;
    if (chip.dataset.toggle === "stale") {
      hideStale = !hideStale;
      chip.classList.toggle("fchip--active", hideStale);
    } else {
      tierFilter = chip.dataset.filter;
      document
        .querySelectorAll(".fchip[data-filter]")
        .forEach((c) => c.classList.toggle("fchip--active", c === chip));
    }
    render();
  });

  document.getElementById("search").addEventListener("input", (e) => {
    query = e.target.value.trim().toLowerCase();
    render();
  });

  const passesFilter = (v) => {
    if (hideStale && v.stale) return false;
    if (tierFilter === "hh" && !hhById.has(v.id)) return false;
    if (tierFilter !== "all" && tierFilter !== "hh" && tierOf(v) !== tierFilter) return false;
    if (query) {
      const hay = `${v.name} ${v.cheapest_beer?.name || ""}`.toLowerCase();
      if (!hay.includes(query)) return false;
    }
    return true;
  };

  // ---------- rank list (one render pipeline) ----------

  const ranks = document.getElementById("ranks");

  function render() {
    let list = venues.filter(passesFilter);
    if (sortMode === "distance" && userPos) {
      list = list.sort((a, b) => haversineM(userPos, a) - haversineM(userPos, b));
    } else {
      list = list.sort(byValue);
    }

    // markers follow the filter
    venues.forEach((v) => {
      const m = markers.get(v.id);
      if (!m) return;
      const visible = passesFilter(v);
      if (visible && !map.hasLayer(m)) m.addTo(map);
      if (!visible && map.hasLayer(m)) m.remove();
    });

    if (list.length === 0) {
      ranks.innerHTML = '<li class="ranks__empty">Inget matchar filtret.</li>';
      return;
    }

    ranks.innerHTML = list
      .map((v, i) => {
        const b = v.cheapest_beer;
        const hh = hhById.get(v.id);
        const live = hhActive(hh);
        const sub =
          sortMode === "distance" && userPos
            ? distLabel(haversineM(userPos, v))
            : b && b.kr_per_cl
              ? `${b.kr_per_cl.toFixed(2)} kr/cl`
              : b
                ? "okänd volym"
                : "";
        return `
        <li class="row row--${tierOf(v)}" style="--i:${i}" tabindex="0" role="button" data-id="${esc(v.id)}">
          <span class="row__rank">${i + 1}</span>
          <span class="row__name">${esc(v.name)}${v.stale ? " ⚠" : ""}${live ? ' <span class="row__hh">🍻 nu</span>' : ""}</span>
          <span class="row__price">${b ? `${b.price_sek} kr` : "–"}<span class="row__percl">${esc(sub)}</span></span>
          <span class="row__beer">${b ? esc(b.name) : "inget pris publicerat"}</span>
        </li>`;
      })
      .join("");
  }
  render();
  // refresh the happy-hour "live" state every minute
  setInterval(render, 60000);

  ranks.addEventListener("click", (e) => activateRow(e.target.closest(".row")));
  ranks.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      activateRow(e.target.closest(".row"));
    }
  });

  function activateRow(row) {
    if (!row) return;
    const v = venues.find((x) => x.id === row.dataset.id);
    if (!v) return;
    if (isMobile()) panelOpen(false);
    map.flyTo([v.lat, v.lon], Math.max(map.getZoom(), 15), { duration: 0.8 });
    setTimeout(() => markers.get(v.id)?.openPopup(), 850);
  }

  function setActiveRow(id) {
    ranks.querySelectorAll(".row--active").forEach((r) => r.classList.remove("row--active"));
    if (!id) return;
    ranks.querySelector(`.row[data-id="${CSS.escape(id)}"]`)?.classList.add("row--active");
  }

  // ---------- mobile bottom sheet ----------

  const panel = document.getElementById("panel");
  const toggle = document.getElementById("panel-toggle");
  function panelOpen(open) {
    panel.classList.toggle("panel--open", open);
    toggle.setAttribute("aria-expanded", String(open));
  }
  toggle.addEventListener("click", () => {
    if (isMobile()) panelOpen(!panel.classList.contains("panel--open"));
  });

  // ---------- popup ----------

  function sparklineSvg(series) {
    if (!series || series.length < 2) return "";
    const tail = series.slice(-30);
    const prices = tail.map((p) => p[1]);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const W = 132;
    const H = 30;
    const x = (i) => 2 + (i * (W - 4)) / (tail.length - 1);
    const y = (p) => (max === min ? H / 2 : 3 + ((max - p) * (H - 6)) / (max - min));
    const pts = tail.map((p, i) => `${x(i).toFixed(1)},${y(p[1]).toFixed(1)}`).join(" ");
    const last = tail[tail.length - 1];
    const first = tail[0];
    const delta = last[1] - first[1];
    const trend = delta > 0 ? `↗ +${delta} kr` : delta < 0 ? `↘ ${delta} kr` : "→ stabilt";
    return `
      <div class="pop__spark">
        <svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true">
          <polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="1.6"
            stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="${x(tail.length - 1).toFixed(1)}" cy="${y(last[1]).toFixed(1)}" r="2.4" fill="currentColor"/>
        </svg>
        <span class="pop__spark-label">${tail.length} mätningar · ${esc(trend)}</span>
      </div>`;
  }

  function popupHtml(v, isBest) {
    const b = v.cheapest_beer;
    const updated = relTime(new Date(v.last_updated));
    const staleBadge = v.stale ? '<span class="pop__stale">senast kända pris</span>' : "";
    const bestBadge = isBest ? " 👑" : "";
    const hh = hhById.get(v.id);
    const hhHtml = hh
      ? `<p class="pop__happy ${hhActive(hh) ? "pop__happy--live" : ""}">
           🍻 Happy hour: ${esc(hhLabel(hh))}${hh.deal ? ` · ${esc(hh.deal)}` : ""}
           ${hhActive(hh) ? '<span class="pop__live">pågår nu</span>' : ""}
         </p>`
      : "";
    if (!b) {
      return `<p class="pop__name">${esc(v.name)}</p>
        <p class="pop__beer">Publicerar inga ölpriser online${staleBadge}</p>${hhHtml}
        <p class="pop__meta"><a href="${esc(v.source_url)}" target="_blank" rel="noopener">öppna meny ↗</a></p>`;
    }
    const vol = b.volume_cl ? ` · ${b.volume_cl} cl` : "";
    const percl = b.kr_per_cl ? `${b.kr_per_cl.toFixed(2)} kr/cl` : "";
    const sysIdx = b.kr_per_cl
      ? `<span class="pop__sys">×${(b.kr_per_cl / SYSTEMBOLAGET_KR_PER_CL).toFixed(1)} mot Systembolaget</span>`
      : "";
    const dist = userPos != null ? `<span>${esc(distLabel(haversineM(userPos, v)))}</span>` : "";
    return `<p class="pop__name">${esc(v.name)}${bestBadge}</p>
      <p class="pop__beer">${esc(b.name)}${vol}${staleBadge}</p>
      <p class="pop__price"><span class="pop__kr">${b.price_sek} kr</span><span class="pop__per">${esc(percl)}</span></p>
      ${sysIdx ? `<p class="pop__sysrow">${sysIdx}</p>` : ""}
      ${hhHtml}${sparklineSvg(history[v.id])}
      <p class="pop__meta">${dist}<span>uppdaterad ${esc(updated)}</span><a href="${esc(v.source_url)}" target="_blank" rel="noopener">öppna meny ↗</a></p>`;
  }

  // ---------- helpers ----------

  function relTime(date) {
    if (Number.isNaN(date.getTime())) return "–";
    const days = Math.round((Date.now() - date.getTime()) / 86400000);
    const rtf = new Intl.RelativeTimeFormat("sv", { numeric: "auto" });
    if (Math.abs(days) < 1) return "idag";
    if (Math.abs(days) < 30) return rtf.format(-days, "day");
    return rtf.format(-Math.round(days / 30), "month");
  }

  function countUp(el, target) {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.textContent = target;
      return;
    }
    const t0 = performance.now();
    const dur = 900;
    (function tick(t) {
      const p = Math.min((t - t0) / dur, 1);
      el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(tick);
    })(t0);
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]),
    );
  }
})();
