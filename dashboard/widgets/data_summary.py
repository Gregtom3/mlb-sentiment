from typing import Any

try:
    import streamlit as st
except Exception:  # pragma: no cover - streamlit may not be installed in test env
    st = None  # type: ignore


def _to_count(df: Any) -> int:
    """Return a safe integer count for a pandas-like dataframe.

    If df is None return 0. If df has a `shape` attribute use shape[0]. If it is
    an integer, return it directly. Otherwise fall back to len(df).
    """
    if df is None:
        return 0
    # pandas DataFrame / Series
    try:
        if hasattr(df, "shape"):
            return int(df.shape[0])
    except Exception:
        pass
    # integer-like
    if isinstance(df, int):
        return int(df)
    try:
        return int(len(df))
    except Exception:
        return 0


def data_summary(
    comments_df: Any, games_df: Any, events_df: Any, team_acronym: str = ""
) -> None:
    """Render metrics (comments, games, game events, W/L record) in a Streamlit row.

    Parameters
    - comments_df: DataFrame-like containing comment rows (or None)
    - games_df: DataFrame-like containing game rows (or None)
    - events_df: DataFrame-like containing game event rows (or None)
    - team_acronym: team acronym to compute W/L record
    """
    comments_count = _to_count(comments_df)
    games_count = _to_count(games_df)
    events_count = _to_count(events_df)

    # --- compute wins/losses if possible ---
    wins = losses = 0
    if games_df is not None and hasattr(games_df, "iterrows"):
        try:
            for _, g in games_df.iterrows():
                if team_acronym and "home_team" in g and "away_team" in g:
                    if g["home_team"] == team_acronym:
                        if g["home_score"] > g["away_score"]:
                            wins += 1
                        elif g["home_score"] < g["away_score"]:
                            losses += 1
                    elif g["away_team"] == team_acronym:
                        if g["away_score"] > g["home_score"]:
                            wins += 1
                        elif g["away_score"] < g["home_score"]:
                            losses += 1
        except Exception:
            pass

    total_played = wins + losses
    win_pct = round((wins / total_played) * 100, 1) if total_played > 0 else 0.0

    # --- Streamlit UI ---
    col1, col2, col3, col4 = st.columns(4)
    col_css = """
    .st-key-col1-container, .st-key-col2-container, .st-key-col3-container, .st-key-col4-container {
        background-color: #FFFFFF;
    }
    """
    st.html(f"<style>{col_css}</style>")

    with col1.container(border=True, key="col1-container"):
        st.metric("Total Subreddit Comments", f"{comments_count:,}")

    with col2.container(border=True, key="col2-container"):
        st.metric("Total Games", f"{games_count:,}")

    with col3.container(border=True, key="col3-container"):
        st.metric("Total Game Events", f"{events_count:,}")

    with col4.container(border=True, key="col4-container"):
        st.metric(f"Win-Loss", f"{wins}-{losses} ({win_pct}%)")
