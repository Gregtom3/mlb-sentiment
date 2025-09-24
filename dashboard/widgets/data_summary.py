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


def data_summary(comments_df: Any, games_df: Any, events_df: Any) -> None:
    """Render three metrics (comments, games, game events) in a Streamlit row.

    Parameters
    - comments_df: DataFrame-like containing comment rows (or None)
    - games_df: DataFrame-like containing game rows (or None)
    - events_df: DataFrame-like containing game event rows (or None)

    The function is safe to call in regular Python tests; if Streamlit is not
    available it will simply return a dict of computed values instead of
    rendering UI. This allows for easier unit testing.
    """
    comments_count = _to_count(comments_df)
    games_count = _to_count(games_df)
    events_count = _to_count(events_df)

    # If Streamlit is available render UI, otherwise return values for tests
    if st is None:
        return {
            "comments": comments_count,
            "games": games_count,
            "events": events_count,
        }

    col1, col2, col3 = st.columns(3)
    col_css = """
.st-key-col1-container {
	background-color: #FFFFFF; /* White background */
}
.st-key-col2-container {
    background-color: #FFFFFF; /* White background */
}
.st-key-col3-container {
    background-color: #FFFFFF; /* White background */
}
	"""
    st.html(f"<style>{col_css}</style>")

    with col1.container(border=True, key="col1-container"):
        st.metric("Total comments", f"{comments_count:,}")

    with col2.container(border=True, key="col2-container"):
        st.metric("Total games", f"{games_count:,}")

    with col3.container(border=True, key="col3-container"):
        st.metric("Total game events", f"{events_count:,}")


if __name__ == "__main__":  # quick manual smoke run when executed directly
    # Avoid importing pandas at module import time to keep this lightweight.
    print("data_summary module loaded. Call data_summary(...) from a Streamlit app.")
