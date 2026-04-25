/**
 * Gallery: manifest.json + optional JSON specs for ECharts (interactive).
 */
(function () {
  "use strict";

  const SECTION_ORDER = [
    "food_patterns",
    "weekly_alerts",
    "prediction_model",
    "clustering",
    "location_viz",
    "most_appreciated",
  ];

  const SECTION_TITLES = {
    food_patterns: "Food patterns",
    weekly_alerts: "Weekly alerts",
    prediction_model: "Prediction model",
    clustering: "Clustering",
    location_viz: "Location",
    most_appreciated: "Most appreciated",
  };

  const sectionsEl = document.getElementById("sections");
  const metaLine = document.getElementById("metaLine");
  const loadError = document.getElementById("loadError");
  const cleanups = [];

  function titleFromFilename(stem) {
    const parts = stem.replace(/^\d+_/, "").split("_");
    return parts
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(" ");
  }

  function groupBySection(paths) {
    const map = new Map();
    for (const p of paths) {
      const segs = p.split("/");
      if (segs.length < 2) continue;
      const cat = segs[0];
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat).push(p);
    }
    for (const [, list] of map) {
      list.sort();
    }
    return map;
  }

  function specUrlFromPng(rel, imageBase) {
    const base = (imageBase || "out").replace(/\/$/, "");
    const jsonRel = rel.replace(/\.png$/i, ".json");
    return base + "/data/" + jsonRel.replace(/\\/g, "/");
  }

  function initCardInteractive(figure, cap, rel, imageBase, fallbackTitle) {
    const pngSrc = (imageBase || "out").replace(/\/$/, "") + "/" + rel.replace(/\\/g, "/");
    const specUrl = specUrlFromPng(rel, imageBase);

    const wrap = document.createElement("div");
    wrap.className = "card__viz";

    const live = document.createElement("div");
    live.className = "card__echart";
    live.setAttribute("role", "img");
    live.setAttribute("aria-label", "Interactive chart: " + fallbackTitle);

    const details = document.createElement("details");
    details.className = "card__static";
    const sum = document.createElement("summary");
    sum.textContent = "Static PNG (matplotlib export)";
    const img = document.createElement("img");
    img.className = "card__img";
    img.src = pngSrc;
    img.alt = "Static chart: " + fallbackTitle;
    img.loading = "lazy";
    img.decoding = "async";
    details.appendChild(sum);
    details.appendChild(img);

    wrap.appendChild(live);
    wrap.appendChild(details);
    figure.appendChild(wrap);

    fetch(specUrl, { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("no spec");
        return r.json();
      })
      .then(function (spec) {
        if (!spec || !window.BuffetCharts || typeof window.BuffetCharts.mount !== "function") {
          throw new Error("no buffet charts");
        }
        if (spec.title && cap) {
          cap.textContent = spec.title;
        }
        if (spec.chart === "composite") {
          live.classList.add("card__echart--tall");
        }
        if (spec.chart === "heatmap") {
          const sc = document.createElement("div");
          sc.className = "card__echart-scroll";
          live.classList.add("card__echart--heatmap");
          wrap.removeChild(live);
          sc.appendChild(live);
          wrap.insertBefore(sc, details);
        }
        const cleanup = window.BuffetCharts.mount(live, spec);
        if (typeof cleanup === "function") cleanups.push(cleanup);
      })
      .catch(function () {
        live.classList.add("card__echart--hidden");
        details.open = true;
        img.loading = "eager";
      });
  }

  function render(manifest) {
    const base = (manifest.image_base || "out").replace(/\/$/, "");
    const graphs = manifest.graphs || [];
    if (metaLine) {
      if (manifest.generated_at_utc) {
        const d = new Date(manifest.generated_at_utc);
        const nice = d.toLocaleString(undefined, {
          dateStyle: "medium",
          timeStyle: "short",
        });
        metaLine.textContent = "Figures last generated · " + nice;
        metaLine.hidden = false;
      } else {
        metaLine.hidden = true;
      }
    }

    const byCat = groupBySection(graphs);
    const frag = document.createDocumentFragment();
    let sectionIndex = 0;

    for (const key of SECTION_ORDER) {
      const list = byCat.get(key);
      if (!list || !list.length) continue;

      const section = document.createElement("section");
      section.className = "section";
      section.id = key;
      section.style.setProperty("--s", String(sectionIndex++));
      const h2 = document.createElement("h2");
      h2.className = "section__title";
      h2.textContent = SECTION_TITLES[key] || key;
      section.appendChild(h2);

      const grid = document.createElement("div");
      grid.className = "section__grid";

      list.forEach(function (rel, i) {
        const fileName = rel.split("/").pop() || rel;
        const stem = fileName.replace(/\.png$/i, "");
        const title = titleFromFilename(stem);

        const art = document.createElement("article");
        art.className = "card";
        art.style.setProperty("--i", String(i % 5));

        const cap = document.createElement("h3");
        cap.className = "card__caption";
        cap.textContent = title;

        const fig = document.createElement("figure");
        fig.className = "card__figure";

        initCardInteractive(fig, cap, rel, base, title);

        art.appendChild(cap);
        art.appendChild(fig);
        grid.appendChild(art);
      });

      section.appendChild(grid);
      frag.appendChild(section);
    }

    sectionsEl.appendChild(frag);
  }

  function run() {
    fetch("manifest.json", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("manifest.json returned " + r.status);
        return r.json();
      })
      .then(function (manifest) {
        if (!manifest.graphs || !manifest.graphs.length) {
          throw new Error("No graphs listed in manifest — run python run_graphs.py");
        }
        render(manifest);
      })
      .catch(function (e) {
        if (loadError) {
          loadError.hidden = false;
          loadError.textContent =
            (e && e.message) || "Could not load gallery. Use a local server and run the graph pipeline first.";
        }
      });
  }

  window.addEventListener("beforeunload", function () {
    cleanups.forEach(function (fn) {
      try {
        fn();
      } catch (_e) {
        /* ignore */
      }
    });
  });

  run();
})();
