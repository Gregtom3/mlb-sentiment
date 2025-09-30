import streamlit as st
import pandas as pd
import plotly.express as px


def render_event_pie_chart(
    events_df: pd.DataFrame,
    title: str = "",
    top_n: int = 10,
    team_acronym: str = "",
    do_opponent: bool = False,
) -> None:
    """
    Render a pie chart of the most common game events.

    Parameters
    ----------
    events_df : pd.DataFrame
        Must contain a column 'event' or similar describing the event type.
    title : str
        Title for the pie chart.
    top_n : int
        Number of top events to display (default 10).
    team_acronym : str
        Team acronym to determine if home or away team.
    do_opponent : bool
        If True, show events for the opponent team.
    """
    st.html(
        f"""
        <style>
        .st-key-event-pie-{str(do_opponent)} {{
            background-color: #FFFFFF;
            padding: 10px;
        }}
        </style>
        """
    )

    # Defensive check
    if events_df is None or events_df.empty or "event" not in events_df.columns:
        st.warning("No event data available to display pie chart.")
        return

    # Count most common events
    events_df = events_df.copy()
    if do_opponent == False:
        team_is_home = events_df.iloc[0]["home_team"] == team_acronym
        if team_is_home:
            events_df = events_df[events_df["home_team"] == team_acronym]
        else:
            events_df = events_df[events_df["away_team"] == team_acronym]
    else:
        team_is_home = events_df.iloc[0]["home_team"] != team_acronym
        if team_is_home:
            events_df = events_df[events_df["home_team"] == team_acronym]
        else:
            events_df = events_df[events_df["away_team"] == team_acronym]
    event_counts = events_df["event"].value_counts().head(top_n).reset_index()
    event_counts.columns = ["event", "count"]

    # Create pie chart
    fig = px.pie(
        event_counts,
        names="event",
        values="count",
        hole=0.3,  # donut style
    )
    fig.update_layout(paper_bgcolor="white", plot_bgcolor="white")

    # Render in Streamlit container
    with st.container(border=True, key=f"event-pie-{str(do_opponent)}", height=530):
        st.markdown(
            f"""
            <div style="
                background-color:#F8F9FC;
                padding:10px;
                border-radius:6px 6px 0px 0px;
                border-color:#DADADA;
                border-width:1px;
                border-style:solid;
                margin:-10px;
                font-size:1.2em;
                font-weight:400;
            ">
            {('📊 ' + title) if title else '📊 Event Distribution'}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            key=f"plotly-event-pie-{team_acronym}-{str(do_opponent)}",
        )
