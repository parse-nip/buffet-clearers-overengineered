/**
 * Map JSON specs (from chart_json / Python) to ECharts options — matches site "zine" palette.
 */
(function (global) {
  "use strict";

  if (typeof echarts === "undefined") {
    global.BuffetCharts = { error: "echarts not loaded" };
    return;
  }

  const T = {
    text: "#0f0f0f",
    sub: "#3a3530",
    accent: "#b32014",
    gold: "#c4921c",
    green: "#17806a",
    blue: "#1f4f82",
    border: "#c9bdb0",
    grid: "rgba(26, 22, 20, 0.12)",
  };

  /** Plasma-style scale (navy / purple / magenta / orange / yellow) — reference heatmap */
  const HEAT_PLASMA = ["#0d0887", "#5c01a4", "#9c179e", "#cc4778", "#ed7953", "#f9a825", "#f0f921"];
  const HEAT_DARK = {
    plot: "#121212",
    text: "#f3f2f0",
    muted: "#a8a6a1",
    gridLine: "rgba(255,255,255,0.06)",
    border: "rgba(255,255,255,0.12)",
    cellLine: "rgba(0,0,0,0.35)",
  };

  function buildHeatmapOption(spec) {
    const yCats = spec.yCategories || [];
    const xCats = spec.xCategories || [];
    const matrix = spec.data || [];
    const trip = [];
    for (let yi = 0; yi < matrix.length; yi++) {
      const row = matrix[yi] || [];
      for (let xi = 0; xi < row.length; xi++) {
        trip.push([xi, yi, row[xi]]);
      }
    }
    const flat = trip.map((d) => d[2]);
    const vmax = Math.max(1, ...flat);
    const xn = spec.xAxisName;
    const yn = spec.yAxisName;
    const xNameOpt = xn
      ? { name: xn, nameTextStyle: { color: HEAT_DARK.muted, fontSize: 11 }, nameLocation: "middle", nameGap: 32 }
      : {};
    const yNameOpt = yn
      ? { name: yn, nameTextStyle: { color: HEAT_DARK.muted, fontSize: 11 }, nameLocation: "middle", nameGap: 50, nameRotate: 90 }
      : {};
    return {
      backgroundColor: HEAT_DARK.plot,
      textStyle: { color: HEAT_DARK.text },
      title: {
        text: spec.title || "",
        subtext: spec.subtext || "",
        left: 0,
        top: 0,
        textStyle: {
          color: HEAT_DARK.text,
          fontSize: 15,
          fontWeight: 600,
          fontFamily: "Bricolage Grotesque, system-ui, sans-serif",
        },
        subtextStyle: { color: HEAT_DARK.muted, fontSize: 11, fontFamily: "Newsreader, Georgia, serif" },
      },
      animationDuration: 280,
      /* Count only in-cell via emphasis label; no floating box (keeps the grid clean). */
      tooltip: { show: false },
      grid: { left: 8, right: 84, top: 56, bottom: 28, containLabel: true },
      xAxis: {
        type: "category",
        data: xCats.map(String),
        ...xNameOpt,
        splitArea: { show: true, areaStyle: { color: [HEAT_DARK.plot, "rgba(255,255,255,0.02)"] } },
        axisLine: { lineStyle: { color: HEAT_DARK.border } },
        axisTick: { show: false },
        axisLabel: { color: HEAT_DARK.muted, fontSize: 10, rotate: xCats.length > 20 ? 50 : 45, interval: 0, hideOverlap: true, margin: 8 },
        splitLine: { show: false },
        boundaryGap: true,
      },
      yAxis: {
        type: "category",
        data: yCats.map(String),
        ...yNameOpt,
        inverse: true,
        splitArea: { show: true, areaStyle: { color: [HEAT_DARK.plot, "rgba(255,255,255,0.02)"] } },
        axisLine: { lineStyle: { color: HEAT_DARK.border } },
        axisTick: { show: false },
        axisLabel: { color: HEAT_DARK.muted, fontSize: 11, width: 88, overflow: "truncate", lineHeight: 16 },
        splitLine: { show: false },
        boundaryGap: true,
      },
      visualMap: {
        id: "heatVm",
        min: 0,
        max: vmax,
        calculable: true,
        orient: "vertical",
        right: 2,
        top: 60,
        bottom: "10%",
        itemWidth: 12,
        itemHeight: 10,
        inRange: { color: HEAT_PLASMA },
        outOfRange: { color: "#1a0a1a" },
        text: [String(vmax), "0"],
        textStyle: { color: HEAT_DARK.muted, fontSize: 10 },
        textGap: 6,
      },
      series: [
        {
          name: "Alerts",
          type: "heatmap",
          data: trip,
          itemStyle: {
            borderColor: HEAT_DARK.cellLine,
            borderWidth: 0.5,
            opacity: 1,
          },
          label: { show: false },
          emphasis: {
            focus: "self",
            label: {
              show: true,
              color: "#ffffff",
              fontSize: 13,
              fontWeight: 700,
              textShadowColor: "rgba(0,0,0,0.9)",
              textShadowBlur: 8,
              formatter: (p) => (p && p.data && p.data[2] != null ? String(p.data[2]) : ""),
            },
            itemStyle: {
              borderColor: "rgba(255,255,255,0.9)",
              borderWidth: 1.5,
              shadowBlur: 20,
              shadowColor: "rgba(240, 249, 33, 0.45)",
            },
          },
          blur: {
            itemStyle: { opacity: 0.85 },
            label: { show: false },
          },
        },
      ],
      media: [
        {
          query: { maxWidth: 560 },
          option: {
            backgroundColor: HEAT_DARK.plot,
            title: { textStyle: { fontSize: 13 } },
            grid: { left: 0, right: 12, top: 52, bottom: 108, containLabel: true },
            xAxis: { axisLabel: { fontSize: 9, rotate: xCats.length > 12 ? 55 : 40 } },
            yAxis: { axisLabel: { fontSize: 10, width: 80 } },
            visualMap: {
              id: "heatVm",
              orient: "horizontal",
              left: "center",
              right: 12,
              top: "auto",
              bottom: 4,
              itemWidth: 10,
              itemHeight: 8,
            },
          },
        },
        {
          query: { minWidth: 560 },
          option: {
            backgroundColor: HEAT_DARK.plot,
            visualMap: { id: "heatVm", orient: "vertical", right: 2, top: 52, bottom: "10%", left: "auto" },
          },
        },
      ],
    };
  }

  /** magic_model today strip — matches matplotlib `_draw_heatmap_row` + metric footer */
  function lerpByte(a, b, t) {
    return Math.round(a + (b - a) * t);
  }

  function foodStripColor(s) {
    const R0 = 240;
    const G0 = 68;
    const B0 = 56;
    const R1 = 255;
    const G1 = 212;
    const B1 = 0;
    const R2 = 23;
    const G2 = 178;
    const B2 = 106;
    const t = Math.max(0, Math.min(1, Number(s) || 0));
    if (t <= 0.5) {
      const k = t * 2;
      return "rgb(" + lerpByte(R0, R1, k) + "," + lerpByte(G0, G1, k) + "," + lerpByte(B0, B1, k) + ")";
    }
    const k = (t - 0.5) * 2;
    return "rgb(" + lerpByte(R1, R2, k) + "," + lerpByte(G1, G2, k) + "," + lerpByte(B1, B2, k) + ")";
  }

  function buildMagicStripOption(spec) {
    const BG = "#1D1D20";
    const PRIMARY = "#fbfbff";
    const SEC = "#909094";
    const GOLD = "#ffd400";
    const DIM = "#2b2b2f";
    const EDGE = "#1D1D20";
    const ch = spec.currentHour != null ? Number(spec.currentHour) : 0;
    const scores = spec.scores || [];
    const bh = spec.bestNextHour != null && spec.bestNextHour !== "" ? Number(spec.bestNextHour) : null;
    const bestCol = spec.bestNextLabelColor || (bh != null && scores[bh] >= 0.65 ? "#17b26a" : GOLD);

    const xCats = [];
    for (let h = 0; h < 24; h++) {
      xCats.push(("0" + h).slice(-2) + ":00");
    }
    const mono = "IBM Plex Mono, ui-monospace, monospace";

    /* Gapless bars (uniform height) — cartesian heatmap was rendering blank in ECharts 5 without visualMap. */
    const barData = [];
    for (let h = 0; h < 24; h++) {
      const s = scores[h] != null ? Number(scores[h]) : 0;
      let fill;
      let borderColor = EDGE;
      let borderWidth = 0.6;
      if (h < ch) {
        fill = DIM;
      } else {
        fill = foodStripColor(s);
        if (h === ch) {
          borderColor = GOLD;
          borderWidth = 2.8;
        }
      }
      const hh = ("0" + h).slice(-2);
      let labStr;
      let labColor;
      if (h < ch) {
        labStr = hh;
        labColor = "#555";
      } else {
        labStr = hh + ":00\n" + Math.round(s * 100) + "%";
        labColor = s > 0.6 ? "#0f0f0f" : "#fbfbff";
      }
      barData.push({
        value: 1,
        itemStyle: {
          color: fill,
          borderColor: borderColor,
          borderWidth: borderWidth,
        },
        label: {
          show: true,
          position: "inside",
          formatter: labStr,
          color: labColor,
          fontSize: 7,
          fontWeight: 700,
          fontFamily: mono,
          lineHeight: 10,
        },
      });
    }

    const badge = spec.semesterBadge || {};
    const badgeText = badge.text || "";
    const badgeBorder = badge.borderColor || GOLD;
    const metrics = spec.metrics || [];

    const metricGraphics = metrics.map(function (m, i) {
      const pctW = Math.round((m.weight != null ? Number(m.weight) : 0) * 100);
      return {
        type: "group",
        left: 2 + i * 19.6 + "%",
        top: "78%",
        children: [
          {
            type: "text",
            x: 0,
            y: 0,
            style: {
              text: String(m.name || ""),
              fill: SEC,
              font: "10px " + mono,
              textAlign: "left",
            },
          },
          {
            type: "text",
            x: 0,
            y: 18,
            style: {
              text: "×" + pctW + "%",
              fill: m.accentColor || SEC,
              font: "bold 11px " + mono,
              textAlign: "left",
            },
          },
          {
            type: "text",
            x: 0,
            y: 38,
            style: {
              text: String(m.scoreText || "") + "  " + String(m.tag || ""),
              fill: PRIMARY,
              font: "10px " + mono,
              opacity: 0.72,
              textAlign: "left",
            },
          },
        ],
      };
    });

    const markData = [
      {
        coord: [xCats[ch], 1],
        symbol: "triangle",
        symbolSize: 10,
        symbolRotate: 180,
        symbolOffset: [0, -16],
        itemStyle: { color: GOLD },
        label: {
          show: true,
          formatter: "NOW",
          color: GOLD,
          fontWeight: "bold",
          fontSize: 10,
          position: "top",
          distance: 2,
        },
      },
    ];
    if (bh != null && !isNaN(bh) && bh >= 0 && bh < 24) {
      const bs = scores[bh] != null ? Number(scores[bh]) : 0;
      markData.push({
        coord: [xCats[bh], 1],
        symbol: "circle",
        symbolSize: 1,
        itemStyle: { opacity: 0 },
        label: {
          show: true,
          formatter:
            "best next: " +
            ("0" + bh).slice(-2) +
            ":00 (" +
            Math.round(bs * 100) +
            "%)",
          color: bestCol,
          fontWeight: "bold",
          fontSize: 10,
          position: "bottom",
          distance: 4,
        },
      });
    }

    return {
      backgroundColor: BG,
      animationDuration: 220,
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(37,37,40,0.96)",
        borderColor: "#444",
        textStyle: { color: PRIMARY, fontSize: 12 },
        formatter: function (p) {
          const h = p.dataIndex;
          const v = scores[h] != null ? Number(scores[h]) : 0;
          const lab = xCats[h];
          const role = h < ch ? "past" : h === ch ? "now" : "ahead";
          return lab + " · " + Math.round(v * 100) + "%<br/>" + role;
        },
      },
      title: {
        text: spec.title || "",
        subtext: spec.subtitle || "",
        left: 8,
        top: 4,
        textStyle: { color: PRIMARY, fontSize: 15, fontWeight: 700, fontFamily: "Bricolage Grotesque, system-ui, sans-serif" },
        subtextStyle: { color: SEC, fontSize: 11, fontFamily: "Newsreader, Georgia, serif" },
      },
      graphic: metricGraphics.concat([
        {
          type: "group",
          right: 10,
          top: 6,
          children: [
            {
              type: "rect",
              shape: { width: 132, height: 26, r: 4 },
              style: { fill: "#252528", stroke: badgeBorder, lineWidth: 1.5 },
            },
            {
              type: "text",
              x: 66,
              y: 13,
              style: {
                text: badgeText,
                fill: badgeBorder,
                font: "bold 11px Bricolage Grotesque, system-ui, sans-serif",
                textAlign: "center",
                textVerticalAlign: "middle",
              },
            },
          ],
        },
        {
          type: "text",
          right: 10,
          bottom: 4,
          style: {
            text: "magic_model · buffet clearers",
            fill: "#444",
            font: "9px " + mono,
            textAlign: "right",
          },
        },
      ]),
      grid: { left: 36, right: 12, top: 72, bottom: 118, containLabel: false },
      xAxis: {
        type: "category",
        data: xCats,
        position: "bottom",
        axisLine: { lineStyle: { color: "#333" } },
        axisTick: { show: false },
        axisLabel: { show: false },
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 1,
        show: false,
        splitLine: { show: false },
      },
      series: [
        {
          name: "likelihood",
          type: "bar",
          data: barData,
          barCategoryGap: "0%",
          barGap: "0%",
          barMaxWidth: 9999,
          emphasis: {
            focus: "self",
            itemStyle: {
              shadowBlur: 14,
              shadowColor: "rgba(255, 212, 0, 0.35)",
            },
          },
          markPoint: {
            data: markData,
          },
        },
      ],
      media: [
        {
          query: { maxWidth: 520 },
          option: {
            grid: { left: 28, right: 8, top: 68, bottom: 132 },
            title: { textStyle: { fontSize: 13 } },
          },
        },
      ],
    };
  }

  function mountMagicStrip(el, spec) {
    el.style.width = "100%";
    el.style.minWidth = "0";
    el.style.minHeight = "320px";
    el.style.boxSizing = "border-box";
    const opt = buildMagicStripOption(spec);
    if (!opt) return function () {};
    const inst = echarts.init(el, null, { renderer: "canvas" });
    inst.setOption(opt, true);
    requestAnimationFrame(function () {
      inst.resize();
    });
    return bindChart(el, inst);
  }

  const subTextOf = (spec) =>
    spec.subtext != null && spec.subtext !== "" ? spec.subtext : spec.subtitle || "";

  const baseTitle = (spec) => ({
    text: spec.title || "",
    subtext: subTextOf(spec),
    left: 0,
    textStyle: { color: T.text, fontSize: 14, fontWeight: 600, fontFamily: "Bricolage Grotesque, system-ui, sans-serif" },
    subtextStyle: { color: T.sub, fontSize: 11, fontFamily: "Newsreader, Georgia, serif" },
  });

  const tooltipAxis = { trigger: "axis", backgroundColor: "rgba(255,252,248,0.95)", borderColor: T.border, textStyle: { color: T.text } };
  const tooltipItem = { trigger: "item", backgroundColor: "rgba(255,252,248,0.95)", borderColor: T.border, textStyle: { color: T.text } };

  function buildOption(spec) {
    if (!spec || !spec.chart) return null;
    switch (spec.chart) {
      case "bar":
        return {
          color: [T.accent],
          title: baseTitle(spec),
          tooltip: tooltipAxis,
          grid: { left: 48, right: 24, top: spec.subtitle ? 64 : 48, bottom: 52 },
          xAxis: {
            type: "category",
            data: spec.categories,
            axisLabel: { color: T.sub, rotate: 24 },
            axisLine: { lineStyle: { color: T.border } },
          },
          yAxis: {
            type: "value",
            splitLine: { lineStyle: { color: T.grid, type: "dashed" } },
            axisLabel: { color: T.sub },
          },
          series: [{ name: "Count", type: "bar", data: spec.values, barMaxWidth: 36 }],
        };
      case "barh": {
        const n = (spec.values && spec.values.length) || 0;
        const pal = [T.accent, T.blue, T.green, "#8b5a6a", "#4a5a6e"];
        const hi = spec.highlight;
        const colors = spec.categories.map((_, i) => {
          if (hi === "first" && i === 0) return T.gold;
          if (hi === "last" && i === n - 1) return T.gold;
          return pal[i % pal.length];
        });
        return {
          color: [T.accent],
          title: baseTitle(spec),
          tooltip: tooltipAxis,
          grid: { left: Math.min(220, 40 + n * 3), right: 28, top: spec.subtitle ? 58 : 44, bottom: 28, containLabel: true },
          xAxis: {
            type: "value",
            splitLine: { lineStyle: { color: T.grid, type: "dashed" } },
            axisLabel: { color: T.sub },
          },
          yAxis: {
            type: "category",
            data: spec.categories,
            inverse: spec.reverseY === true,
            axisLabel: { color: T.sub, width: 200, overflow: "truncate" },
            axisLine: { lineStyle: { color: T.border } },
          },
          series: [
            {
              name: "Value",
              type: "bar",
              data: spec.values.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
            },
          ],
        };
      }
      case "heatmap":
        return buildHeatmapOption(spec);
      case "line": {
        const ser = (spec.series || []).map((s) => ({
          name: s.name,
          type: "line",
          data: s.data,
          connectNulls: Boolean(s.name && s.name.toLowerCase().includes("avg")),
          smooth: 0.2,
          showSymbol: s.name && s.name.includes("avg") ? false : true,
          lineStyle: s.name && s.name.includes("avg") ? { type: "dashed", width: 2, color: T.gold } : { width: 2.2 },
        }));
        return {
          color: [T.accent, T.gold],
          title: baseTitle(spec),
          tooltip: tooltipAxis,
          legend: { bottom: 0, textStyle: { color: T.sub } },
          grid: { left: 48, right: 24, top: 52, bottom: 72 },
          xAxis: { type: "category", data: spec.categories, axisLabel: { color: T.sub, rotate: 32, fontSize: 9 } },
          yAxis: { type: "value", splitLine: { lineStyle: { color: T.grid, type: "dashed" } }, axisLabel: { color: T.sub } },
          series: ser,
        };
      }
      case "barColored": {
        const n = spec.values && spec.values.length;
        return {
          title: baseTitle(spec),
          tooltip: tooltipAxis,
          dataZoom: [
            { type: "inside", xAxisIndex: 0, filterMode: "filter" },
            { type: "slider", xAxisIndex: 0, height: 20, bottom: 8, borderColor: T.border, textStyle: { color: T.sub, fontSize: 10 } },
          ],
          grid: { left: 44, right: 20, top: 50, bottom: 88 },
          xAxis: { type: "category", data: spec.labels, axisLabel: { color: T.sub, rotate: 50, fontSize: 7 } },
          yAxis: { type: "value", splitLine: { lineStyle: { color: T.grid, type: "dashed" } } },
          series: [
            {
              name: "Alerts",
              type: "bar",
              data: spec.values.map((v, i) => ({
                value: v,
                itemStyle: { color: (spec.barColors && spec.barColors[i]) || T.accent },
              })),
            },
          ],
        };
      }
      case "confusion": {
        const m = spec.matrix;
        const rows = spec.rowLabels;
        const cols = spec.colLabels;
        const trip = [];
        for (let i = 0; i < m.length; i++) for (let j = 0; j < m[i].length; j++) trip.push([j, i, m[i][j]]);
        const mx = Math.max(1, ...trip.map((d) => d[2]));
        return {
          title: baseTitle(spec),
          tooltip: tooltipItem,
          grid: { left: 100, right: 90, top: 56, bottom: 48 },
          xAxis: { type: "category", data: cols, name: "Predicted", nameLocation: "middle", nameGap: 28, nameTextStyle: { color: T.sub } },
          yAxis: { type: "category", data: rows, name: "Actual", nameLocation: "middle", nameGap: 56, nameTextStyle: { color: T.sub } },
          visualMap: { min: 0, max: mx, show: true, inRange: { color: ["#e8e2d6", T.blue] }, right: 6, top: "middle" },
          series: [
            { type: "heatmap", data: trip, label: { show: true, color: T.text, fontSize: 14, fontWeight: 700 } },
          ],
        };
      }
      case "scatter": {
        const pts = (spec.x || []).map((x, i) => [x, (spec.y || [])[i]]);
        return {
          color: [T.accent],
          title: baseTitle(spec),
          tooltip: { trigger: "item", formatter: (p) => (p && p.data ? `Actual: ${p.data[0]}<br/>Predicted: ${p.data[1]}` : "") },
          grid: { left: 48, right: 28, top: 52, bottom: 44 },
          xAxis: { type: "value", name: spec.xName, min: 0, max: 23, nameTextStyle: { color: T.sub }, splitLine: { lineStyle: { color: T.grid, type: "dashed" } } },
          yAxis: { type: "value", name: spec.yName, min: 0, max: 23, nameTextStyle: { color: T.sub }, splitLine: { lineStyle: { color: T.grid, type: "dashed" } } },
          series: [
            { name: "Predictions", type: "scatter", data: pts, symbolSize: 6, itemStyle: { opacity: 0.35, color: T.accent }, large: pts.length > 1500, largeThreshold: 1500 },
            { name: "Perfect fit", type: "line", data: [[0, 0], [23, 23]], lineStyle: { type: "dashed", color: T.gold, width: 1.4 }, showSymbol: false, emphasis: { disabled: true } },
          ],
        };
      }
      case "probBar": {
        const thr = spec.threshold != null ? spec.threshold : 0.5;
        return {
          title: baseTitle(spec),
          tooltip: tooltipAxis,
          grid: { left: 40, right: 16, top: 50, bottom: 56 },
          xAxis: { type: "category", data: spec.categories, axisLabel: { color: T.sub, rotate: 45, fontSize: 8 } },
          yAxis: { type: "value", min: 0, max: 1, splitLine: { lineStyle: { color: T.grid, type: "dashed" } } },
          series: [
            {
              name: "P(food)",
              type: "bar",
              data: (spec.values || []).map((p) => {
                if (p == null) return { value: 0, itemStyle: { opacity: 0 } };
                const v = Number(p);
                const c = v >= 0.6 ? T.green : v >= 0.4 ? T.gold : T.blue;
                return { value: v, itemStyle: { color: c } };
              }),
              markLine: {
                data: [{ yAxis: thr }],
                lineStyle: { type: "dashed", color: T.accent },
                label: { formatter: "threshold " + thr },
              },
            },
          ],
        };
      }
      case "empty":
        return { title: { text: spec.message || "No data", textStyle: { color: T.sub, fontSize: 14 } } };
      case "message":
        return { title: baseTitle({ title: spec.title, subtext: spec.message || spec.subtitle || "" }) };
      case "barGroup": {
        const series = (spec.series || []).map((s) => {
          const o = { name: s.name, type: "bar", data: s.values || s.data, barMaxWidth: 32 };
          if (s.color) o.itemStyle = { color: s.color };
          return o;
        });
        return {
          color: [T.accent, T.blue, T.green, T.gold, "#8b5a6a"],
          title: baseTitle(spec),
          tooltip: tooltipAxis,
          legend: { type: "scroll", top: 28, textStyle: { color: T.sub, fontSize: 10 } },
          grid: { left: 44, right: 16, top: (spec.series || []).length > 2 ? 72 : 56, bottom: 40 },
          xAxis: {
            type: "category",
            data: spec.categories,
            axisLabel: { color: T.sub, rotate: spec.rotateX == null ? 0 : spec.rotateX },
            axisLine: { lineStyle: { color: T.border } },
          },
          yAxis: { type: "value", splitLine: { lineStyle: { color: T.grid, type: "dashed" } }, axisLabel: { color: T.sub } },
          series,
        };
      }
      case "stackedArea": {
        const pal = [T.accent, T.gold, T.blue, T.green, "#8b5a6a", "#4a5a6e", "#8c564b", "#e377c2"];
        const ser = (spec.series || []).map((s, i) => ({
          name: s.name,
          type: "line",
          stack: "total",
          data: s.data,
          areaStyle: { opacity: 0.82 },
          lineStyle: { width: 0.6, color: pal[i % pal.length] },
          itemStyle: { color: pal[i % pal.length] },
        }));
        return {
          color: pal,
          title: baseTitle(spec),
          tooltip: tooltipAxis,
          legend: { type: "scroll", bottom: 0, textStyle: { color: T.sub, fontSize: 9 } },
          grid: { left: 48, right: 20, top: 48, bottom: spec.series && spec.series.length > 4 ? 96 : 72 },
          xAxis: { type: "category", data: spec.categories, axisLabel: { color: T.sub, rotate: 40, fontSize: 8 } },
          yAxis: { type: "value", splitLine: { lineStyle: { color: T.grid, type: "dashed" } } },
          series: ser,
        };
      }
      default:
        return null;
    }
  }

  function bindChart(el, inst) {
    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(el);
    return function () {
      ro.disconnect();
      inst.dispose();
    };
  }

  /**
   * Heatmaps get a minimum pixel grid so cells never shrink to illegible size on mobile;
   * parent `.card__echart-scroll` supplies horizontal scroll when needed.
   */
  function mountHeatmap(el, spec) {
    const nX = (spec.xCategories && spec.xCategories.length) || 0;
    const nY = (spec.yCategories && spec.yCategories.length) || 0;
    const cellW = 10;
    const cellH = 20;
    const padX = 112;
    const padY = 130;
    const minW = Math.max(320, nX * cellW + padX);
    const minH = Math.max(280, nY * cellH + padY);
    el.style.minWidth = minW + "px";
    el.style.minHeight = minH + "px";
    el.style.boxSizing = "border-box";

    const opt = buildHeatmapOption(spec);
    if (!opt) return function () {};
    const inst = echarts.init(el, null, { renderer: "canvas" });
    inst.setOption(opt, true);
    requestAnimationFrame(function () {
      inst.resize();
    });
    return bindChart(el, inst);
  }

  function mount(el, spec) {
    if (!el || !spec) return function () {};
    if (spec.chart === "empty") {
      const opt = buildOption(spec);
      if (opt) {
        const inst = echarts.init(el, null, { renderer: "canvas" });
        inst.setOption(opt, true);
        return bindChart(el, inst);
      }
      return function () {};
    }
    if (spec.chart === "composite") {
      return mountComposite(el, spec);
    }
    if (spec.chart === "heatmap") {
      return mountHeatmap(el, spec);
    }
    if (spec.chart === "magicStrip") {
      return mountMagicStrip(el, spec);
    }
    const opt = buildOption(spec);
    if (!opt) return function () {};
    const inst = echarts.init(el, null, { renderer: "canvas" });
    inst.setOption(opt, true);
    return bindChart(el, inst);
  }

  function mountComposite(wrap, spec) {
    const panels = spec.panels || [];
    const cleanup = [];
    wrap.innerHTML = "";
    if (spec.quote) {
      const q = document.createElement("p");
      q.className = "comp-quote";
      q.textContent = '"' + spec.quote + '"';
      wrap.appendChild(q);
    }

    const grid = document.createElement("div");
    grid.className = "comp-grid";
    wrap.appendChild(grid);

    panels.forEach((p, idx) => {
      const box = document.createElement("div");
      box.className = "comp-panel";
      if (p.chart === "barh") {
        box.style.minHeight = (p.values || []).length > 8 ? "380px" : "240px";
      } else if (p.chart === "message") {
        box.style.minHeight = "120px";
      } else if (p.chart === "heatmap") {
        box.style.minHeight = "300px";
      } else {
        box.style.minHeight = "240px";
      }
      box.setAttribute("data-panel", String(idx));
      grid.appendChild(box);
      if (p.chart === "message") {
        const inst = echarts.init(box, null, { renderer: "canvas" });
        inst.setOption(
          {
            title: {
              text: p.title,
              subtext: p.message,
              textStyle: { color: T.text, fontSize: 12 },
              subtextStyle: { color: T.sub, fontSize: 11 },
            },
          },
          true
        );
        cleanup.push(bindChart(box, inst));
        return;
      }
      const inst = echarts.init(box, null, { renderer: "canvas" });
      const o = p.chart === "stepLine" ? buildStepLineOption(p) : buildOption(p);
      if (o) inst.setOption(o, true);
      cleanup.push(bindChart(box, inst));
    });
    return function () {
      cleanup.forEach(function (fn) {
        fn();
      });
    };
  }

  function buildStepLineOption(p) {
    const x = (p.dates || []).map((d) => d);
    return {
      color: [T.accent],
      title: { text: p.title || "", left: 0, textStyle: { color: T.text, fontSize: 12, fontWeight: 600 } },
      tooltip: { trigger: "axis", valueFormatter: (v) => (v == null ? "" : String(v)) },
      grid: { left: 48, right: 20, top: 36, bottom: 36 },
      xAxis: { type: "time", splitLine: { show: false }, axisLabel: { color: T.sub, fontSize: 8 } },
      yAxis: { type: "value", min: 0, splitLine: { lineStyle: { color: T.grid, type: "dashed" } } },
      series: [
        { name: "Cumulative", type: "line", step: "end", data: x.map((t, i) => [t, p.values[i]]), showSymbol: true, lineStyle: { width: 2.2, color: T.accent }, areaStyle: { opacity: 0.12, color: T.accent } },
      ],
    };
  }

  global.BuffetCharts = { buildOption, mount, T };
})(window);
