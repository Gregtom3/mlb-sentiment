import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render_inning_sentiment_widget(
    comments_df: pd.DataFrame,
    events_df: pd.DataFrame,
    games_df: pd.DataFrame,
) -> None:
    """
    Render average sentiment per inning across all games.

    Parameters
    ----------
    comments_df : pd.DataFrame
        Must contain ['created_est','sentiment_score','game_id'].
    events_df : pd.DataFrame
        Must contain ['est','halfInning','game_id'].
    games_df : pd.DataFrame
        Must contain ['game_id','game_date','home_team','away_team'].
    """

    # --- Styling
    container_css = """
.st-key-inning-sentiment-container {
    background-color: #FFFFFF;
    padding: 10px;
}
    """
    st.html(f"<style>{container_css}</style>")

    with st.container(border=True, key="inning-sentiment-container", height=530):

        # Defensive checks
        if comments_df is None or comments_df.empty:
            st.info("No comments available for inning sentiment.")
            return
        if events_df is None or events_df.empty:
            st.info("No game events available to segment by inning.")
            return

        st.markdown(
            """
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
                Average Inning Sentiment (All Games)
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- Prep data
        events_df = events_df.copy()
        events_df["est"] = pd.to_datetime(events_df["est"])
        comments_df = comments_df.copy()
        comments_df["created_est"] = pd.to_datetime(comments_df["created_est"])

        all_results = []

        # Loop over games
        for gid in events_df["game_id"].unique():
            ev_game = events_df[events_df["game_id"] == gid].sort_values("est")
            cm_game = comments_df[comments_df["game_id"] == gid].sort_values(
                "created_est"
            )

            if ev_game.empty or cm_game.empty:
                continue

            # inning boundaries (last event in each inning)
            inning_bounds = (
                ev_game.groupby("inning")["est"]
                .max()
                .reset_index()
                .sort_values("est")
                .reset_index(drop=True)
            )

            prev_time = ev_game["est"].min()
            for _, row in inning_bounds.iterrows():
                inning = row["inning"]
                end_time = row["est"]

                mask = (cm_game["created_est"] >= prev_time) & (
                    cm_game["created_est"] < end_time
                )
                if mask.any():
                    avg_sent = cm_game.loc[mask, "sentiment_score"].mean()
                    all_results.append({"Inning": inning, "avg_sentiment": avg_sent})
                prev_time = end_time

        results_df = pd.DataFrame(all_results)

        if results_df.empty:
            st.info("No inning sentiment could be computed across games.")
            return

        # Aggregate across games → average sentiment per inning label
        agg_df = results_df.groupby("Inning")["avg_sentiment"].mean().reset_index()

        # --- Plot
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=agg_df["Inning"],
                y=agg_df["avg_sentiment"],
                marker_color=[
                    "rgba(52,194,48,0.8)" if v > 0 else "rgba(255,0,0,0.8)"
                    for v in agg_df["avg_sentiment"]
                ],
                text=[f"{v:.2f}" for v in agg_df["avg_sentiment"]],
                textposition="outside",
            )
        )
        fig.update_layout(
            paper_bgcolor="white",
            plot_bgcolor="white",
            yaxis=dict(title="Average Sentiment"),
            xaxis=dict(
                title="Inning",
                tickmode="array",
                tickvals=list(agg_df["Inning"]),
                ticktext=list(agg_df["Inning"]),
            ),
            margin=dict(l=40, r=20, t=40, b=40),
        )

        st.plotly_chart(fig, use_container_width=True)
