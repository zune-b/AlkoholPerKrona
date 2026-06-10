/* alkoholperkrona — map + rank list. No build step, no framework:
   the data file is tiny and the page is one screen. */

(async function () {
  "use strict";

  const FALLBACK_VOLUME_CL = 40; // rank volume-less beers as if 40 cl

  // Price tiers (SEK): green ≤55, yellow 56-79, red ≥80. Stale or null beer = "stale".
  const tierOf = (v) => {
    if (v.stale || !v.cheapest_beer) return "stale";
    const p = v.cheapest_beer.price_sek;
    if (p <= 55) return "cheap";
    if (p <= 79) return "mid";
    return "expensive";
  };

  // ---------- data ----------

  let venues;
  try {
    const resp = await fetch("./restaurants.json", { cache: "no-store" });
    venues = await resp.json();
  } catch (err) {
    document.getElementById("ranks").innerHTML =
      '<li style="padding:16px;color:#9b988f">Kunde inte ladda prisdata. Försök igen senare.</li>';
    return;
  }

  const rankValue = (v) => {
    const b = v.cheapest_beer;
    if (!b) return Infinity;
    return b.kr_per_cl ?? b.price_sek / FALLBACK_VOLUME_CL;
  };

  const sorted = [...venues].sort((a, b) => {
    if (!!a.stale !== !!b.stale) return a.stale ? 1 : -1;
    return rankValue(a) - rankValue(b);
  });

  const best = sorted.find((v) => !v.stale && v.cheapest_beer) || null;

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
  sorted.forEach((v, i) => {
    const b = v.cheapest_beer;
    const isBest = best && v.id === best.id;
    const cls = ["bubble", `bubble--${tierOf(v)}`, isBest ? "bubble--best" : ""]
      .filter(Boolean)
      .join(" ");
    const label = b ? `${b.price_sek}:-` : "–";
    const crown = isBest ? '<span class="bubble__crown">👑</span>' : "";
    const icon = L.divIcon({
      className: "price-marker",
      html: `<div class="${cls}" style="animation-delay:${200 + i * 60}ms">${crown}${esc(label)}</div>`,
      iconSize: [0, 0],
      iconAnchor: [0, 0],
      popupAnchor: [0, -46],
    });
    const m = L.marker([v.lat, v.lon], { icon, riseOnHover: true })
      .addTo(map)
      .bindPopup(popupHtml(v, isBest), { closeButton: true, maxWidth: 280 });
    m.on("popupopen", () => setActiveRow(v.id));
    m.on("popupclose", () => setActiveRow(null));
    markers.set(v.id, m);
  });

  const isMobile = () => window.matchMedia("(max-width: 880px)").matches;
  const fitAll = () => {
    const bounds = L.latLngBounds(venues.map((v) => [v.lat, v.lon]));
    map.fitBounds(bounds, {
      paddingTopLeft: isMobile() ? [30, 90] : [40, 90],
      paddingBottomRight: isMobile() ? [30, 120] : [parseInt(getComputedStyle(document.documentElement).getPropertyValue("--panel-w")) + 60 || 460, 60],
    });
  };
  fitAll();

  // ---------- rank list ----------

  const ranks = document.getElementById("ranks");
  ranks.innerHTML = sorted
    .map((v, i) => {
      const b = v.cheapest_beer;
      const percl = b && b.kr_per_cl ? `${b.kr_per_cl.toFixed(2)} kr/cl` : b ? "okänd volym" : "";
      return `
      <li class="row row--${tierOf(v)}" style="--i:${i}" tabindex="0" role="button" data-id="${esc(v.id)}">
        <span class="row__rank">${i + 1}</span>
        <span class="row__name">${esc(v.name)}${v.stale ? " ⚠" : ""}</span>
        <span class="row__price">${b ? `${b.price_sek} kr` : "–"}<span class="row__percl">${esc(percl)}</span></span>
        <span class="row__beer">${b ? esc(b.name) : "inget pris publicerat"}</span>
      </li>`;
    })
    .join("");

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

  // ---------- helpers ----------

  function popupHtml(v, isBest) {
    const b = v.cheapest_beer;
    const updated = relTime(new Date(v.last_updated));
    const staleBadge = v.stale ? '<span class="pop__stale">senast kända pris</span>' : "";
    const bestBadge = isBest ? " 👑" : "";
    if (!b) {
      return `<p class="pop__name">${esc(v.name)}</p>
        <p class="pop__beer">Publicerar inga ölpriser online${staleBadge}</p>
        <p class="pop__meta"><a href="${esc(v.source_url)}" target="_blank" rel="noopener">öppna meny ↗</a></p>`;
    }
    const vol = b.volume_cl ? ` · ${b.volume_cl} cl` : "";
    const percl = b.kr_per_cl ? `${b.kr_per_cl.toFixed(2)} kr/cl` : "";
    return `<p class="pop__name">${esc(v.name)}${bestBadge}</p>
      <p class="pop__beer">${esc(b.name)}${vol}${staleBadge}</p>
      <p class="pop__price"><span class="pop__kr">${b.price_sek} kr</span><span class="pop__per">${esc(percl)}</span></p>
      <p class="pop__meta"><span>uppdaterad ${esc(updated)}</span><a href="${esc(v.source_url)}" target="_blank" rel="noopener">öppna meny ↗</a></p>`;
  }

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
