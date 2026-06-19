/* Dashboard controller: load JSON payloads and render the views. */
(function () {
  "use strict";

  const state = {
    team: null,
    data: null,
    selectedGameId: null,
    tab: "top",
    view: "game",
    league: null,
    leagueMetric: "overall",
  };
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
        `scoreboard shortly.</div>`;
      $("footer-generated").textContent = "Data built " + manifest.generated_at;
      return;
    }
    const sel = $("team-select");
    manifest.teams
      .slice()
      .sort((a, b) => a.team_name.localeCompare(b.team_name))
      .forEach((t) => {
        const o = document.createElement("option");
        o.value = t.team;
        o.textContent = t.team_name; // full name only, no acronym
        sel.appendChild(o);
      });
    $("footer-generated").textContent = "Data built " + manifest.generated_at;
    sel.addEventListener("change", () => selectTeam(sel.value));

    // View switcher.
    document.querySelectorAll("#viewnav .vbtn").forEach((btn) => {
      btn.addEventListener("click", () => showView(btn.dataset.view));
    });
    // Comment tabs.
    document.querySelectorAll("#comment-tabs .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.tab = btn.dataset.tab;
        setActive("#comment-tabs .tab", btn);
        renderComments();
      });
    });
    // League metric toggle.
    document.querySelectorAll("#league-metric .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.leagueMetric = btn.dataset.metric;
        setActive("#league-metric .tab", btn);
        renderLeague();
      });
    });

    try {
      state.league = await loadJSON("data/league.json");
    } catch (e) {
      state.league = null;
    }
    renderLeague();

    await selectTeam(sel.value || manifest.teams[0].team);
  }

  function setActive(sel, btn) {
    document.querySelectorAll(sel).forEach((b) => b.classList.toggle("is-active", b === btn));
  }

  function showView(view) {
    state.view = view;
    document
      .querySelectorAll("#viewnav .vbtn")
      .forEach((b) => b.classList.toggle("is-active", b.dataset.view === view));
    document
      .querySelectorAll(".view")
      .forEach((v) => v.classList.toggle("is-active", v.id === "view-" + view));
    window.scrollTo({ top: 0, behavior: "auto" });
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
  const signed = (s) => (s > 0 ? "+" : "") + s.toFixed(2);
  const scoreClass = (s) => (s > 0 ? "pos" : s < 0 ? "neg" : "");
  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch])
    );
  }

  function render() {
    const d = state.data;
    $("team-title").textContent = d.team_name; // full name
    $("generated").textContent = d.generated_at;

    const wins = d.games.filter((g) => g.outcome === "Win").length;
    const losses = d.games.filter((g) => g.outcome === "Loss").length;
    $("record-digits").textContent = `${wins}-${losses}`;

    const sm = d.summary;
    $("summary-badges").innerHTML = [
      ["Mood when winning", sm.win_avg_sentiment, "pos"],
      ["Mood when losing", sm.loss_avg_sentiment, "neg"],
      ["Toxicity", sm.pct_negative, ""],
    ]
      .map(([lbl, val, cls]) => {
        const txt =
          val === null || val === undefined
            ? "—"
            : lbl === "Toxicity"
            ? val.toFixed(1) + "%"
            : val.toFixed(3);
        return `<div class="badge ${cls}"><span>${lbl}</span><b>${txt}</b></div>`;
      })
      .join("");

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

    // ---- The Game view ----
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
    renderMoments(pg);
    renderComments();

    // ---- Trends view ----
    Charts.histogram($("chart-hist"), d.distribution);
    Charts.scatter($("chart-scatter"), d.scatter, d.regression);
    Charts.innings($("chart-innings"), d.inning_sentiment);
    $("pie-team-title").textContent = d.team_name;
    renderPie("pie-team", "legend-team", d.event_pie.team);
    renderPie("pie-opp", "legend-opp", d.event_pie.opponent);

    // ---- Season + Fans views ----
    renderSeason(d.season);
    renderCommenters(d.commenters);
  }

  function renderMoments(pg) {
    const m = (pg && pg.moments) || [];
    $("moments-list").innerHTML = m.length
      ? m
          .map((x) => {
            const cls = x.swing >= 0 ? "surge" : "groan";
            const arrow = x.swing >= 0 ? "▲" : "▼";
            return (
              `<div class="moment ${cls}">` +
              `<div class="m-swing">${arrow} ${signed(x.swing)}</div>` +
              `<div class="m-body"><div class="m-play">${escapeHtml(x.description)}</div>` +
              `<div class="m-meta">${x.half} ${x.inning} · ${x.t} · ${x.score}</div></div>` +
              `</div>`
            );
          })
          .join("")
      : `<div class="empty">Not enough comment volume to pinpoint moments for this game.</div>`;
  }

  function renderComments() {
    const d = state.data;
    const g =
      d.games.find((x) => x.game_id === state.selectedGameId) || d.games[0];
    const pg = (g && d.per_game[String(g.game_id)]) || {};
    const panel = (pg.comments && pg.comments[state.tab]) || [];
    $("comments-list").innerHTML = panel.length
      ? panel
          .map(
            (c) =>
              `<div class="crow ${scoreClass(c.score)}">` +
              `<div class="score">${signed(c.score)}</div>` +
              `<div class="inn">${inn(c.inning)}</div>` +
              `<div class="body"><div class="who">u/${escapeHtml(c.author)}</div>` +
              `<div class="said">${escapeHtml(c.text)}</div></div>` +
              `<div class="when">${c.t || ""}</div></div>`
          )
          .join("")
      : `<div class="empty">No comments.</div>`;
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
      (season.positive || []).map(quote).join("") || `<div class="empty">No comments.</div>`;
    $("season-boos").innerHTML =
      (season.negative || []).map(quote).join("") || `<div class="empty">No comments.</div>`;
  }

  const PIE_COLORS = [
    "#E4002B", "#4A90E2", "#2FBF71", "#F2C14E", "#C77DFF",
    "#9DB1CE", "#F08C3A", "#3DBE9E",
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

  // ---- League Compare ----
  const LEAGUE_META = {
    overall: { note: "Average comment sentiment across all games (higher = happier fan base).", diverge: true },
    win: { note: "Average sentiment in games the team won.", diverge: true },
    loss: { note: "Average sentiment in games the team lost.", diverge: true },
    pct_negative: { note: "Share of comments scored negative — higher = more toxic.", diverge: false },
  };
  function renderLeague() {
    if (!state.league) {
      $("league-list").innerHTML = `<div class="empty">League data unavailable.</div>`;
      return;
    }
    const metric = state.leagueMetric;
    const meta = LEAGUE_META[metric];
    $("league-note").textContent = meta.note;

    const rows = state.league.teams
      .filter((t) => t[metric] !== null && t[metric] !== undefined)
      .sort((a, b) => b[metric] - a[metric]);
    if (!rows.length) {
      $("league-list").innerHTML = `<div class="empty">Not enough data yet.</div>`;
      return;
    }
    const maxAbs = Math.max(...rows.map((r) => Math.abs(r[metric]))) || 1;

    $("league-list").innerHTML = rows
      .map((r, i) => {
        const v = r[metric];
        let fill;
        if (meta.diverge) {
          const half = (Math.abs(v) / maxAbs) * 50;
          const color = v >= 0 ? "var(--pos)" : "var(--neg)";
          const left = v >= 0 ? 50 : 50 - half;
          fill = `left:${left}%;width:${half}%;background:${color}`;
        } else {
          fill = `left:0;width:${(v / 100) * 100}%;background:var(--neg)`;
        }
        const val = meta.diverge ? signed(v) : v.toFixed(1) + "%";
        const hi = r.team === state.team ? ' style="color:var(--accent)"' : "";
        return (
          `<div class="lrow">` +
          `<div class="rank">${i + 1}</div>` +
          `<div class="team"${hi}>${escapeHtml(r.team_name)}</div>` +
          `<div class="bar ${meta.diverge ? "diverge" : ""}"><div class="fill" style="${fill}"></div></div>` +
          `<div class="val">${val}</div>` +
          `</div>`
        );
      })
      .join("");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
