/* Dashboard controller: load JSON payloads and render the scoreboard. */
(function () {
  "use strict";

  const state = { team: null, data: null, selectedGameId: null, tab: "top" };
  const $ = (id) => document.getElementById(id);

  async function loadJSON(path) {
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
    if (!manifest.teams || !manifest.teams.length) {
      $("app").innerHTML =
        `<div class="empty">No data yet — the daily refresh will fill the ` +
        `scoreboard shortly. Check back after the next build.</div>`;
      $("footer-generated").textContent = "Data built " + manifest.generated_at;
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

    // Tab wiring (static DOM — attach once).
    document.querySelectorAll("#comment-tabs .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.tab = btn.dataset.tab;
        document
          .querySelectorAll("#comment-tabs .tab")
          .forEach((b) => b.classList.toggle("is-active", b === btn));
        renderComments();
      });
    });

    await selectTeam(manifest.teams[0].team);
  }

  async function selectTeam(team) {
    state.team = team;
    state.data = await loadJSON(`data/${team}.json`);
    const games = state.data.games;
    state.selectedGameId = games.length ? games[games.length - 1].game_id : null;
    render();
  }

  function selectGame(id) {
    state.selectedGameId = id;
    render();
  }

  const fmt = (n) =>
    n === null || n === undefined ? "—" : Number(n).toLocaleString();
  const inn = (i) => (i === null || i === undefined ? "—" : "IN " + i);

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch])
    );
  }
  const scoreClass = (s) => (s > 0 ? "pos" : s < 0 ? "neg" : "");
  const signed = (s) => (s > 0 ? "+" : "") + s.toFixed(2);

  function render() {
    const d = state.data;
    $("team-title").textContent = d.team_name;
    $("generated").textContent = d.generated_at;

    const wins = d.games.filter((g) => g.outcome === "Win").length;
    const losses = d.games.filter((g) => g.outcome === "Loss").length;
    $("record-digits").textContent = `${wins}-${losses}`;

    // mood badges
    const sm = d.summary;
    $("summary-badges").innerHTML = [
      ["Mood when winning", sm.win_avg_sentiment, "pos"],
      ["Mood when losing", sm.loss_avg_sentiment, "neg"],
      ["Mood vs. run-diff R²", sm.r2, ""],
    ]
      .map(
        ([lbl, val, cls]) =>
          `<div class="badge ${cls}"><span>${lbl}</span><b>${
            val === null ? "—" : val.toFixed(3)
          }</b></div>`
      )
      .join("");

    // stat tiles
    const played = wins + losses;
    const pct = played ? ((wins / played) * 100).toFixed(0) : "0";
    $("stat-tiles").innerHTML = [
      [fmt(d.totals.total_comments), "Comments scored"],
      [fmt(d.totals.total_games), "Games tracked"],
      [fmt(d.totals.total_events), "Game events"],
      [`${pct}%`, "Win rate"],
    ]
      .map(
        ([v, l]) =>
          `<div class="tile"><div class="tile-val">${v}</div>` +
          `<div class="tile-lbl">${l}</div></div>`
      )
      .join("");

    // charts
    Charts.gameLine($("chart-gameline"), d.games, state.selectedGameId, selectGame);

    const g =
      d.games.find((x) => x.game_id === state.selectedGameId) || d.games[0];
    const pg = (g && d.per_game[String(g.game_id)]) || {};
    if (g) {
      $("detail-title").innerHTML =
        `${g.away_team} @ ${g.home_team} · ${g.game_date} · ` +
        `<span class="${g.outcome === "Win" ? "win" : "loss"}">${g.outcome} ` +
        `${g.home_score}-${g.away_score}</span>`;
    }
    Charts.gameDetail($("chart-detail"), pg.sentiment_ts || [], pg.run_diff_ts || [], d.team);
    Charts.histogram($("chart-hist"), d.distribution);
    Charts.scatter($("chart-scatter"), d.scatter, d.regression);
    Charts.innings($("chart-innings"), d.inning_sentiment);

    $("pie-team-title").textContent = d.team;
    renderPie("pie-team", "legend-team", d.event_pie.team);
    renderPie("pie-opp", "legend-opp", d.event_pie.opponent);

    renderComments();
    renderSeason(d.season);
    renderCommenters(d.commenters);
  }

  function renderComments() {
    const d = state.data;
    const g =
      d.games.find((x) => x.game_id === state.selectedGameId) || d.games[0];
    const pg = (g && d.per_game[String(g.game_id)]) || {};
    const panel = (pg.comments && pg.comments[state.tab]) || [];
    if (!panel.length) {
      $("comments-list").innerHTML = `<div class="empty">No comments.</div>`;
      return;
    }
    $("comments-list").innerHTML = panel
      .map((c) => {
        const cls = scoreClass(c.score);
        return (
          `<div class="crow ${cls}">` +
          `<div class="score">${signed(c.score)}</div>` +
          `<div class="inn">${inn(c.inning)}</div>` +
          `<div class="body"><div class="who">u/${escapeHtml(c.author)}</div>` +
          `<div class="said">${escapeHtml(c.text)}</div></div>` +
          `<div class="when">${c.t || ""}</div>` +
          `</div>`
        );
      })
      .join("");
  }

  function renderSeason(season) {
    if (!season) return;
    const quote = (c) =>
      `<div class="quote"><div class="said">“${escapeHtml(c.text)}”</div>` +
      `<div class="meta"><span class="sc">${signed(c.score)}</span>` +
      ` · u/${escapeHtml(c.author)}` +
      (c.game_date ? ` · ${c.game_date}` : "") +
      (c.inning ? ` · ${inn(c.inning)}` : "") +
      `</div></div>`;
    $("season-cheers").innerHTML =
      (season.positive || []).map(quote).join("") ||
      `<div class="empty">No comments.</div>`;
    $("season-boos").innerHTML =
      (season.negative || []).map(quote).join("") ||
      `<div class="empty">No comments.</div>`;
  }

  const PIE_COLORS = [
    "#FFB627", "#46C46A", "#5BC0EB", "#E2543B", "#C77DFF",
    "#9AA697", "#F08C3A", "#3DBE9E",
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
    if (!c) return;
    const list = (arr) =>
      arr.length
        ? arr.map((a) => `<li>u/${escapeHtml(a.author)} <b>${a.count}</b></li>`).join("")
        : "<li class='empty'>—</li>";
    const ex = (arr, cls) =>
      arr
        .slice(0, 4)
        .map(
          (e) =>
            `<div class="ex ${cls}"><div class="ex-meta">${e.date} · ${signed(
              e.score
            )}</div><div>${escapeHtml(e.text)}</div></div>`
        )
        .join("");
    $("commenters").innerHTML =
      `<div class="cm-col"><h4>Most Active</h4><ul>${list(c.active)}</ul></div>` +
      `<div class="cm-col"><h4>Sunniest Fans</h4>${ex(c.positive_examples, "win")}</div>` +
      `<div class="cm-col"><h4>Grumpiest Fans</h4>${ex(c.negative_examples, "loss")}</div>`;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
