import datetime
from typing import Any, Dict

try:
    import streamlit as st
except Exception:  # pragma: no cover - streamlit may not be installed in test env
    st = None  # type: ignore

import pandas as pd
import plotly.graph_objects as go


def _ensure_datetime(df: pd.DataFrame, col: str = "est") -> pd.Series:
    """Return a datetime Series from df[col], parsed if necessary.

    Accepts already-datetime types or strings. Falls back to pd.to_datetime.
    """
    if col not in df.columns:
        raise KeyError(f"Missing expected column: {col}")
    series = df[col]
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_datetime(series)


def render_game_events_widget(events_df: Any) -> Dict[str, int] | None:
    """Render a line chart of score differential (home - away) over time.

    Parameters
    - events_df: DataFrame-like with columns ['est','home_score','away_score','event','description']

    Behavior
    - x axis: EST timestamp (uses `est` column)
    - y axis: home_score - away_score
    - points connected by a line; markers shown
    - hover text: event and description

    If Streamlit is not available the function returns a small summary dict for tests.
    """
    container_css2 = """
.st-key-game_events-container {
	background-color: #FFFFFF; /* White background */
    padding: 10px;
}
	"""
    st.html(f"<style>{container_css2}</style>")
    with st.container(border=True, key="game_events-container"):
        # Defensive checks
        if events_df is None:
            if st is None:
                return {"points": 0}
            st.info("No game events available to plot.")
            return

        # Try to coerce to DataFrame if possible
        try:
            df = pd.DataFrame(events_df)
        except Exception:
            df = events_df

        required_cols = {"est", "home_score", "away_score"}
        if not required_cols.issubset(set(df.columns)):
            msg = f"Events data missing required columns: {required_cols - set(df.columns)}"
            if st is None:
                raise KeyError(msg)
            st.warning(msg)
            return

        if df.empty:
            if st is None:
                return {"points": 0}
            st.info("No game events to display.")
            return

        # Ensure timestamps are datetime
        try:
            times = _ensure_datetime(df, "est")
        except Exception as e:
            if st is None:
                raise
            st.error(f"Could not parse event timestamps: {e}")
            return

        # Compute differential and hover text
        try:
            differential = (
                pd.to_numeric(df["home_score"], errors="coerce").fillna(0)
                - pd.to_numeric(df["away_score"], errors="coerce").fillna(0)
            ).astype(int)
        except Exception:
            differential = pd.Series([0] * len(df))

        event_col = (
            df["event"].astype(str)
            if "event" in df.columns
            else pd.Series([""] * len(df))
        )
        desc_col = (
            df["description"].astype(str)
            if "description" in df.columns
            else pd.Series([""] * len(df))
        )

        hover_text = (
            (event_col.fillna("") + ": " + desc_col.fillna("")).astype(str).tolist()
        )

        # Build figure
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=list(times),
                y=list(differential),
                mode="lines+markers",
                marker=dict(size=6),
                line=dict(width=2),
                text=hover_text,
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S} <br>Differential: %{y}<br>%{text}<extra></extra>",
                name="Score differential (home - away)",
            )
        )

        fig.update_layout(
            title="Game Score Differential Over Time",
            xaxis_title="EST time",
            yaxis_title="Home - Away",
            autosize=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        if st is None:
            # For tests, return a small summary
            return {
                "points": len(df),
                "start": str(times.iloc[0]),
                "end": str(times.iloc[-1]),
            }

        st.markdown(
            f"<div style='padding:6px;background:#F8F9FC;border-radius:6px'>Game events ({len(df)} points)</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(fig, use_container_width=True)

        return None


if __name__ == "__main__":
    print(
        "Run this widget from the Streamlit dashboard (import and call render_game_events_widget)."
    )
