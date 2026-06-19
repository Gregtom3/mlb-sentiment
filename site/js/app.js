/* Dashboard controller: load JSON payloads and render the page. */
(function () {
  "use strict";

  const state = { team: null, data: null, selectedGameId: null };
  const $ = (id) => document.getElementById(id);

  async function loadJSON(path) {
    // Allow a self-contained build (and offline preview) to inline payloads.
    if (window.__MLB_EMBED__ && window.__MLB_EMBED__[path]) {
      return window.__MLB_EMBED__[path];
    }
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) throw new Error(`${path}: ${res.status}`);
    return res.json();
  }

  async function init() {
    let manifest;
    try {
      manifest = await loadJSON("data/manifest.json");
    } catch (e) {
      $("app").innerHTML =
        `<div class="empty">Could not load <code>data/manifest.json</code>. ` +
        `Run <code>python pipeline/build_site_data.py</code> first.</div>`;
      return;
    }
    const sel = $("team-select");
    manifest.teams.forEach((t) => {
      const o = document.createElement("option");
      o.value = t.team;
      o.textContent = `${t.team_name} (${t.team})`;
      sel.appendChild(o);
    });
    $("footer-generated").textContent = "Data built " + manifest.generated_at;
    sel.addEventListener("change", () => selectTeam(sel.value));
    await selectTeam(manifest.teams[0].team);
  }

  async function selectTeam(team) {
    state.team = team;
    state.data = await loadJSON(`data/${team}.json`);
    // default to the most recent game
    const games = state.data.games;
    state.selectedGameId = games.length ? games[games.length - 1].game_id : null;
    render();
  }

  function selectGame(id) {
    state.selectedGameId = id;
    render();
  }

  function fmt(n) {
    return n === null || n === undefined ? "—" : Number(n).toLocaleString();
  }

  function render() {
    const d = state.data;
    $("team-title").textContent = `${d.team_name} · Fan Sentiment`;
    $("generated").textContent = d.generated_at;

    // --- stat cards ---
    const wins = d.games.filter((g) => g.outcome === "Win").length;
    const losses = d.games.filter((g) => g.outcome === "Loss").length;
    const played = wins + losses;
    const pct = played ? ((wins / played) * 100).toFixed(1) : "0.0";
    const cards = [
      ["💬", "Comments", fmt(d.totals.total_comments)],
      ["⚾", "Games", fmt(d.totals.total_games)],
      ["📋", "Game events", fmt(d.totals.total_events)],
      ["🏆", "Record", `${wins}-${losses} (${pct}%)`],
    ];
    $("stat-cards").innerHTML = cards
      .map(
        ([ic, lbl, val]) =>
          `<div class="card stat"><div class="stat-ic">${ic}</div>` +
          `<div><div class="stat-val">${val}</div><div class="stat-lbl">${lbl}</div></div></div>`
      )
      .join("");

    // --- summary badges ---
    const sm = d.summary;
    $("summary-badges").innerHTML = [
      ["Avg sentiment · Wins", sm.win_avg_sentiment, "pos"],
      ["Avg sentiment · Losses", sm.loss_avg_sentiment, "neg"],
      ["Sentiment vs run-diff R²", sm.r2, "neutral"],
    ]
      .map(
        ([lbl, val, cls]) =>
          `<div class="badge ${cls}"><span>${lbl}</span><b>${
            val === null ? "—" : val.toFixed(3)
          }</b></div>`
      )
      .join("");

    // --- charts ---
    Charts.gameLine($("chart-gameline"), d.games, state.selectedGameId, selectGame);

    const g = d.games.find((x) => x.game_id === state.selectedGameId) || d.games[0];
    const pg = d.per_game[String(g.game_id)] || {};
    $("detail-title").innerHTML =
      `${g.away_team} @ ${g.home_team} · ${g.game_date} · ` +
      `<span class="${g.outcome === "Win" ? "win" : "loss"}">${g.outcome} ` +
      `${g.home_score}-${g.away_score}</span>`;
    Charts.gameDetail($("chart-detail"), pg.sentiment_ts || [], pg.run_diff_ts || [], d.team);

    Charts.histogram($("chart-hist"), d.distribution);
    Charts.scatter($("chart-scatter"), d.scatter, d.regression);
    Charts.innings($("chart-innings"), d.inning_sentiment);

    // event pies + legends
    renderPie("pie-team", "legend-team", d.event_pie.team);
    renderPie("pie-opp", "legend-opp", d.event_pie.opponent);

    // comments table for the selected game
    const rows = (pg.comments || [])
      .map(
        (c) =>
          `<tr><td class="t">${c.t}</td><td class="${
            c.score > 0 ? "win" : c.score < 0 ? "loss" : ""
          }">${c.score.toFixed(2)}</td><td>${escapeHtml(c.author)}</td>` +
          `<td>${escapeHtml(c.text)}</td></tr>`
      )
      .join("");
    $("comments-body").innerHTML =
      rows || `<tr><td colspan="4" class="empty">No comments.</td></tr>`;

    // commenters panel
    renderCommenters(d.commenters);
  }

  const PIE_COLORS = [
    "#5b8def", "#2EA56B", "#f2b705", "#D7494B", "#8e6fd6",
    "#22b8cf", "#f08c3a", "#7a7f87",
  ];
  function renderPie(svgId, legendId, items) {
    Charts.donut($(svgId), items, PIE_COLORS);
    $(legendId).innerHTML = items
      .map(
        (it, i) =>
          `<div class="lg"><span class="sw" style="background:${
            PIE_COLORS[i % PIE_COLORS.length]
          }"></span>${escapeHtml(it.event)} <b>${it.count}</b></div>`
      )
      .join("");
  }

  function renderCommenters(c) {
    const list = (arr) =>
      arr.length
        ? arr.map((a) => `<li>${escapeHtml(a.author)} <b>${a.count}</b></li>`).join("")
        : "<li class='empty'>—</li>";
    const ex = (arr, cls) =>
      arr
        .slice(0, 4)
        .map(
          (e) =>
            `<div class="ex ${cls}"><div class="ex-meta">${e.date} · score ${e.score}</div>` +
            `<div>${escapeHtml(e.text)}</div></div>`
        )
        .join("");
    $("commenters").innerHTML =
      `<div class="cm-col"><h4>🔥 Most active</h4><ul>${list(c.active)}</ul></div>` +
      `<div class="cm-col"><h4>🤩 Most positive</h4>${ex(c.positive_examples, "win")}</div>` +
      `<div class="cm-col"><h4>😡 Most negative</h4>${ex(c.negative_examples, "loss")}</div>`;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch])
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
