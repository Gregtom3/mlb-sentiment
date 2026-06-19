/* Tiny dependency-free SVG charting toolkit.
 * Each renderer draws into a container element using a fixed viewBox so the
 * charts scale responsively. A single shared tooltip is reused across charts. */
(function (global) {
  "use strict";

  const SVGNS = "http://www.w3.org/2000/svg";
  const COL = {
    pos: "#2FBF71", // green
    posFill: "rgba(47,191,113,0.38)",
    neg: "#E4002B", // MLB red
    negFill: "rgba(228,0,43,0.30)",
    line: "#F5F2E9", // cream sentiment line
    accent: "#E4002B",
    grid: "rgba(245,242,233,0.09)",
    axis: "#3a567c", // muted navy zero-lines
    text: "#F5F2E9",
    gold: "#F2C14E", // selected-game marker
    blue: "#4A90E2",
  };

  function el(name, attrs, parent) {
    const node = document.createElementNS(SVGNS, name);
    if (attrs) for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }

  function svg(container, w, h) {
    container.innerHTML = "";
    const s = el("svg", {
      viewBox: `0 0 ${w} ${h}`,
      preserveAspectRatio: "xMidYMid meet",
      width: "100%",
      class: "chart-svg",
    });
    container.appendChild(s);
    return s;
  }

  // --- shared tooltip ---
  let tip;
  function tooltip() {
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "chart-tip";
      tip.style.display = "none";
      document.body.appendChild(tip);
    }
    return tip;
  }
  function showTip(html, x, y) {
    const t = tooltip();
    t.innerHTML = html;
    t.style.display = "block";
    // keep it on-screen (it can be pinned by a touch)
    const w = t.offsetWidth || 220;
    t.style.left = Math.min(x + 14, window.innerWidth - w - 8) + "px";
    t.style.top = y + 14 + "px";
  }
  function hideTip() {
    if (tip) tip.style.display = "none";
  }

  // Bind hover (desktop) + tap (mobile) tooltips to a node. Returns nothing.
  let _tapHideBound = false;
  function bindTip(node, html) {
    node.setAttribute(
      "class",
      ((node.getAttribute("class") || "") + " tipnode").trim()
    );
    node.addEventListener("mousemove", (e) => showTip(html, e.clientX, e.clientY));
    node.addEventListener("mouseleave", hideTip);
    node.addEventListener(
      "touchstart",
      (e) => {
        const t = e.touches && e.touches[0];
        if (t) showTip(html, t.clientX, t.clientY);
      },
      { passive: true }
    );
    if (!_tapHideBound) {
      _tapHideBound = true;
      document.addEventListener(
        "touchstart",
        (e) => {
          const tgt = e.target;
          if (!tgt || !tgt.closest || !tgt.closest(".tipnode")) hideTip();
        },
        { passive: true }
      );
    }
  }

  function niceTicks(min, max, count) {
    if (min === max) {
      min -= 1;
      max += 1;
    }
    const span = max - min;
    const step0 = span / count;
    const mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const norm = step0 / mag;
    const step =
      (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
    const start = Math.ceil(min / step) * step;
    const ticks = [];
    for (let v = start; v <= max + 1e-9; v += step) ticks.push(+v.toFixed(6));
    return ticks;
  }

  function axes(s, m, x0, x1, y0, y1, opts) {
    opts = opts || {};
    // y gridlines + labels
    (opts.yTicks || []).forEach((t) => {
      const y = opts.yScale(t);
      el("line", { x1: x0, x2: x1, y1: y, y2: y, stroke: COL.grid, "stroke-width": 1 }, s);
      el(
        "text",
        { x: x0 - 8, y: y + 4, "text-anchor": "end", class: "ax-lbl" },
        s
      ).textContent = opts.yFmt ? opts.yFmt(t) : t;
    });
    // x labels
    (opts.xTicks || []).forEach((t) => {
      const tx = el(
        "text",
        { x: t.x, y: y1 + 22, "text-anchor": "middle", class: "ax-lbl" },
        s
      );
      tx.textContent = t.label;
    });
    if (opts.yLabel) {
      el(
        "text",
        { x: 14, y: (y0 + y1) / 2, transform: `rotate(-90 14 ${(y0 + y1) / 2})`,
          "text-anchor": "middle", class: "ax-title" },
        s
      ).textContent = opts.yLabel;
    }
  }

  /* ---- 1. Sentiment-by-game line (clickable markers) ---- */
  function gameLine(container, games, selectedId, onSelect) {
    const W = 620, H = 340, m = { l: 54, r: 16, t: 16, b: 40 };
    const s = svg(container, W, H);
    const x0 = m.l, x1 = W - m.r, y0 = m.t, y1 = H - m.b;
    const pts = games.filter((g) => g.avg_sentiment !== null);
    if (!pts.length) return emptyState(container, "No sentiment data.");
    const maxAbs = Math.max(0.1, ...pts.map((p) => Math.abs(p.avg_sentiment))) * 1.15;
    const xScale = (i) => x0 + (pts.length === 1 ? (x1 - x0) / 2 : (i * (x1 - x0)) / (pts.length - 1));
    const yScale = (v) => y1 - ((v + maxAbs) / (2 * maxAbs)) * (y1 - y0);
    const yTicks = niceTicks(-maxAbs, maxAbs, 5);
    axes(s, m, x0, x1, y0, y1, {
      yScale, yTicks, yFmt: (v) => v.toFixed(2), yLabel: "Avg sentiment",
      xTicks: pts.map((p, i) => ({ x: xScale(i), label: p.game_date.slice(5) })),
    });
    el("line", { x1: x0, x2: x1, y1: yScale(0), y2: yScale(0), stroke: COL.axis, "stroke-width": 1.2 }, s);
    // connecting line
    let d = "";
    pts.forEach((p, i) => (d += (i ? "L" : "M") + xScale(i) + " " + yScale(p.avg_sentiment)));
    el("path", { d, fill: "none", stroke: "rgba(245,242,233,0.28)", "stroke-width": 2 }, s);
    // markers
    pts.forEach((p, i) => {
      const cx = xScale(i), cy = yScale(p.avg_sentiment);
      const sel = p.game_id === selectedId;
      const win = p.outcome === "Win";
      const g = el("g", { class: "marker", style: "cursor:pointer" }, s);
      if (sel) {
        star(g, cx, cy, 11, COL.gold);
      } else {
        el("path", {
          d: triangle(cx, cy, 8, win),
          fill: win ? COL.pos : COL.neg,
          stroke: "rgba(245,242,233,0.55)", "stroke-width": 1.2,
        }, g);
      }
      const hit = el("circle", { cx, cy, r: 14, fill: "transparent" }, g);
      const label = `${p.away_team} @ ${p.home_team}<br>${p.game_date} · <b>${p.outcome}</b> ${p.home_score}-${p.away_score}<br>Avg sentiment: <b>${p.avg_sentiment.toFixed(3)}</b>`;
      bindTip(hit, label); // hover on desktop, tap on mobile
      hit.addEventListener("click", () => onSelect(p.game_id));
    });
  }

  /* ---- 2. Sentiment-over-time area + run-diff line ---- */
  function gameDetail(container, ts, runDiff, teamAbbr) {
    const W = 620, H = 340, m = { l: 50, r: 50, t: 16, b: 40 };
    const s = svg(container, W, H);
    const x0 = m.l, x1 = W - m.r, y0 = m.t, y1 = H - m.b;
    if (!ts.length) return emptyState(container, "No comments for this game.");
    const times = ts.map((d) => new Date(d.t.replace(" ", "T")).getTime());
    const tMin = Math.min(...times), tMax = Math.max(...times);
    const xScale = (t) => x0 + ((t - tMin) / (tMax - tMin || 1)) * (x1 - x0);
    const yScale = (v) => y1 - ((v + 1) / 2) * (y1 - y0); // sentiment in [-1,1]
    axes(s, m, x0, x1, y0, y1, {
      yScale, yTicks: [-1, -0.5, 0, 0.5, 1], yFmt: (v) => v.toFixed(1),
      yLabel: "Sentiment",
      xTicks: ts.filter((_, i) => i % Math.ceil(ts.length / 5) === 0).map((d) => ({
        x: xScale(new Date(d.t.replace(" ", "T")).getTime()), label: d.t.slice(11, 16),
      })),
    });
    // area split at zero
    const baseY = yScale(0);
    el("line", { x1: x0, x2: x1, y1: baseY, y2: baseY, stroke: COL.axis, "stroke-width": 1 }, s);
    splitArea(s, ts, xScale, yScale, baseY);
    // sentiment line
    let d = "";
    ts.forEach((p, i) => {
      const t = new Date(p.t.replace(" ", "T")).getTime();
      d += (i ? "L" : "M") + xScale(t) + " " + yScale(p.score);
    });
    el("path", { d, fill: "none", stroke: COL.line, "stroke-width": 2 }, s);
    // run differential on secondary axis
    if (runDiff && runDiff.length) {
      const dmax = Math.max(1, ...runDiff.map((r) => Math.abs(r.diff)));
      const y2 = (v) => y1 - ((v + dmax) / (2 * dmax)) * (y1 - y0);
      let rd = "";
      runDiff.forEach((p, i) => {
        const t = new Date(p.t.replace(" ", "T")).getTime();
        // step line
        if (i) rd += "L" + xScale(t) + " " + y2(runDiff[i - 1].diff);
        rd += (i ? "L" : "M") + xScale(t) + " " + y2(p.diff);
      });
      el("path", { d: rd, fill: "none", stroke: "#7E97BD", "stroke-width": 2, "stroke-dasharray": "5 4" }, s);
      niceTicks(-dmax, dmax, 4).forEach((t) => {
        el("text", { x: x1 + 8, y: y2(t) + 4, "text-anchor": "start", class: "ax-lbl" }, s).textContent = t;
      });
      el("text", { x: W - 10, y: (y0 + y1) / 2, transform: `rotate(90 ${W - 10} ${(y0 + y1) / 2})`,
        "text-anchor": "middle", class: "ax-title" }, s).textContent = `${teamAbbr} lead`;
    }
  }

  function splitArea(s, ts, xScale, yScale, baseY) {
    // Build positive and negative filled regions clipped at zero.
    const xy = ts.map((p) => [xScale(new Date(p.t.replace(" ", "T")).getTime()), p.score]);
    function region(sign) {
      let d = "", open = false;
      for (let i = 0; i < xy.length; i++) {
        const [x, v] = xy[i];
        const val = sign > 0 ? Math.max(0, v) : Math.min(0, v);
        const y = yScale(val);
        if (!open) { d += `M${x} ${baseY} L${x} ${y}`; open = true; }
        else d += ` L${x} ${y}`;
      }
      if (open) d += ` L${xy[xy.length - 1][0]} ${baseY} Z`;
      return d;
    }
    el("path", { d: region(1), fill: COL.posFill, stroke: "none" }, s);
    el("path", { d: region(-1), fill: COL.negFill, stroke: "none" }, s);
  }

  /* ---- 3. Distribution histogram (overlay pos/neg) ---- */
  function histogram(container, dist) {
    const W = 620, H = 320, m = { l: 50, r: 16, t: 16, b: 40 };
    const s = svg(container, W, H);
    const x0 = m.l, x1 = W - m.r, y0 = m.t, y1 = H - m.b;
    const c = dist.centers;
    if (!c.length) return emptyState(container, "No distribution data.");
    const maxC = Math.max(1, ...dist.positive, ...dist.negative);
    const bw = (x1 - x0) / c.length;
    const xScale = (v) => x0 + ((v + 1) / 2) * (x1 - x0);
    const yScale = (v) => y1 - (v / maxC) * (y1 - y0);
    axes(s, m, x0, x1, y0, y1, {
      yScale, yTicks: niceTicks(0, maxC, 4), yLabel: "Comments",
      xTicks: [-1, -0.5, 0, 0.5, 1].map((v) => ({ x: xScale(v), label: v.toFixed(1) })),
    });
    function bars(counts, color) {
      counts.forEach((n, i) => {
        if (!n) return;
        const x = xScale(c[i]) - bw / 2;
        el("rect", { x, y: yScale(n), width: Math.max(1, bw - 1), height: y1 - yScale(n),
          fill: color, opacity: 0.7 }, s);
      });
    }
    bars(dist.negative, COL.neg);
    bars(dist.positive, COL.pos);
    el("text", { x: (x0 + x1) / 2, y: H - 6, "text-anchor": "middle", class: "ax-title" }, s)
      .textContent = "Sentiment score";
  }

  /* ---- 4. Scatter + regression ---- */
  function scatter(container, pts, reg) {
    const W = 620, H = 320, m = { l: 54, r: 16, t: 16, b: 42 };
    const s = svg(container, W, H);
    const x0 = m.l, x1 = W - m.r, y0 = m.t, y1 = H - m.b;
    if (!pts.length) return emptyState(container, "No games to plot.");
    const xs = pts.map((p) => p.run_diff), ys = pts.map((p) => p.avg_sentiment);
    const xmin = Math.min(...xs, -1), xmax = Math.max(...xs, 1);
    const yabs = Math.max(0.1, ...ys.map(Math.abs)) * 1.2;
    const xScale = (v) => x0 + ((v - xmin) / (xmax - xmin || 1)) * (x1 - x0);
    const yScale = (v) => y1 - ((v + yabs) / (2 * yabs)) * (y1 - y0);
    axes(s, m, x0, x1, y0, y1, {
      yScale, yTicks: niceTicks(-yabs, yabs, 5), yFmt: (v) => v.toFixed(2),
      yLabel: "Avg sentiment",
      xTicks: niceTicks(xmin, xmax, 5).map((v) => ({ x: xScale(v), label: v })),
    });
    el("line", { x1: x0, x2: x1, y1: yScale(0), y2: yScale(0), stroke: COL.axis, "stroke-width": 1 }, s);
    el("line", { x1: xScale(0), x2: xScale(0), y1: y0, y2: y1, stroke: COL.grid, "stroke-width": 1 }, s);
    if (reg && reg.slope !== null) {
      const lx0 = xmin, lx1 = xmax;
      el("line", {
        x1: xScale(lx0), y1: yScale(reg.slope * lx0 + reg.intercept),
        x2: xScale(lx1), y2: yScale(reg.slope * lx1 + reg.intercept),
        stroke: COL.line, "stroke-width": 2, "stroke-dasharray": "6 4",
      }, s);
    }
    pts.forEach((p) => {
      const cx = xScale(p.run_diff), cy = yScale(p.avg_sentiment);
      const dot = el("circle", { cx, cy, r: 6, fill: "rgba(74,144,226,0.85)",
        stroke: "#2b5a8c", "stroke-width": 1 }, s);
      const lbl = `${p.date}<br>Run diff: <b>${p.run_diff}</b><br>Avg sentiment: <b>${p.avg_sentiment.toFixed(3)}</b>`;
      bindTip(dot, lbl);
    });
    el("text", { x: (x0 + x1) / 2, y: H - 6, "text-anchor": "middle", class: "ax-title" }, s)
      .textContent = "Final run differential";
  }

  /* ---- 5. Inning bar chart ---- */
  function innings(container, data) {
    const W = 620, H = 300, m = { l: 50, r: 16, t: 16, b: 36 };
    const s = svg(container, W, H);
    const x0 = m.l, x1 = W - m.r, y0 = m.t, y1 = H - m.b;
    if (!data.length) return emptyState(container, "No inning data.");
    const yabs = Math.max(0.1, ...data.map((d) => Math.abs(d.avg_sentiment))) * 1.2;
    const bw = (x1 - x0) / data.length;
    const yScale = (v) => y1 - ((v + yabs) / (2 * yabs)) * (y1 - y0);
    axes(s, m, x0, x1, y0, y1, {
      yScale, yTicks: niceTicks(-yabs, yabs, 5), yFmt: (v) => v.toFixed(2),
      yLabel: "Avg sentiment",
    });
    const baseY = yScale(0);
    el("line", { x1: x0, x2: x1, y1: baseY, y2: baseY, stroke: COL.axis, "stroke-width": 1 }, s);
    data.forEach((d, i) => {
      const cx = x0 + i * bw + bw / 2;
      const y = yScale(d.avg_sentiment);
      const pos = d.avg_sentiment >= 0;
      el("rect", { x: cx - bw * 0.32, y: pos ? y : baseY, width: bw * 0.64,
        height: Math.abs(baseY - y), fill: pos ? COL.pos : COL.neg, opacity: 0.85 }, s);
      el("text", { x: cx, y: y1 + 20, "text-anchor": "middle", class: "ax-lbl" }, s).textContent = d.inning;
    });
    el("text", { x: (x0 + x1) / 2, y: H - 4, "text-anchor": "middle", class: "ax-title" }, s)
      .textContent = "Inning";
  }

  /* ---- 6. Donut (event distribution) ---- */
  function donut(container, items, palette) {
    const W = 280, H = 260, cx = 140, cy = 120, r = 92, ir = 50;
    const s = svg(container, W, H);
    if (!items.length) return emptyState(container, "No events.");
    const total = items.reduce((a, b) => a + b.count, 0);
    let ang = -Math.PI / 2;
    items.forEach((it, i) => {
      const frac = it.count / total;
      const a2 = ang + frac * 2 * Math.PI;
      const color = palette[i % palette.length];
      const path = arc(cx, cy, r, ir, ang, a2);
      const seg = el("path", { d: path, fill: color, stroke: "#0A1A33", "stroke-width": 1.5 }, s);
      const lbl = `${it.event}: <b>${it.count}</b> (${(frac * 100).toFixed(0)}%)`;
      bindTip(seg, lbl);
      ang = a2;
    });
    el("text", { x: cx, y: cy + 4, "text-anchor": "middle", class: "donut-total" }, s).textContent = total;
    // The colour legend is rendered alongside the SVG in app.js.
  }

  // --- small shape helpers ---
  function triangle(cx, cy, r, up) {
    return up
      ? `M${cx} ${cy - r} L${cx + r} ${cy + r} L${cx - r} ${cy + r} Z`
      : `M${cx} ${cy + r} L${cx + r} ${cy - r} L${cx - r} ${cy - r} Z`;
  }
  function star(parent, cx, cy, r, fill) {
    let d = "";
    for (let i = 0; i < 10; i++) {
      const rad = i % 2 ? r * 0.45 : r;
      const a = (Math.PI / 5) * i - Math.PI / 2;
      d += (i ? "L" : "M") + (cx + rad * Math.cos(a)) + " " + (cy + rad * Math.sin(a));
    }
    el("path", { d: d + "Z", fill, stroke: "rgba(245,242,233,0.55)", "stroke-width": 1 }, parent);
  }
  function arc(cx, cy, r, ir, a1, a2) {
    const large = a2 - a1 > Math.PI ? 1 : 0;
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
    const x2 = cx + r * Math.cos(a2), y2 = cy + r * Math.sin(a2);
    const x3 = cx + ir * Math.cos(a2), y3 = cy + ir * Math.sin(a2);
    const x4 = cx + ir * Math.cos(a1), y4 = cy + ir * Math.sin(a1);
    return `M${x1} ${y1} A${r} ${r} 0 ${large} 1 ${x2} ${y2} L${x3} ${y3} A${ir} ${ir} 0 ${large} 0 ${x4} ${y4} Z`;
  }
  function emptyState(container, msg) {
    container.innerHTML = `<div class="empty">${msg}</div>`;
  }

  global.Charts = { gameLine, gameDetail, histogram, scatter, innings, donut, COL };
})(window);
