import streamlit as st
import pandas as pd
import plotly.express as px


def render_event_pie_chart(events_df: pd.DataFrame, top_n: int = 10) -> None:
    """
    Render a pie chart of the most common game events.

    Parameters
    ----------
    events_df : pd.DataFrame
        Must contain a column 'event' or similar describing the event type.
    top_n : int
        Number of top events to display (default 10).
    """

    # Defensive check
    if events_df is None or events_df.empty or "event" not in events_df.columns:
        st.warning("No event data available to display pie chart.")
        return

    # Count most common events
    event_counts = events_df["event"].value_counts().head(top_n).reset_index()
    event_counts.columns = ["event", "count"]

    # Create pie chart
    fig = px.pie(
        event_counts,
        names="event",
        values="count",
        title=f"Top {top_n} Most Common Game Events",
        hole=0.3,  # donut style
    )

    # Render in Streamlit container
    with st.container(border=True, key="event-pie-container", height=500):
        st.plotly_chart(fig, use_container_width=True)
