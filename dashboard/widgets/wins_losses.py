import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render_wins_losses_histogram(games_df: pd.DataFrame, current_game_id: int) -> None:
    """
    Render faint blue (wins) and faint red (losses) histograms for each game_id.

    Parameters
    ----------
    games_df : pd.DataFrame
        Must contain ['game_id','game_date','wins','losses'].
    current_game_id : int
        The currently selected game_id (for highlighting).
    """

    # --- Styling
    container_css = """
.st-key-wins-losses-container {
    background-color: #FFFFFF;
    padding: 10px;
}
    """
    st.html(f"<style>{container_css}</style>")

    with st.container(border=True, key="wins-losses-container"):
        # Defensive checks
        if games_df is None or games_df.empty:
            st.info("No game data available for wins/losses histogram.")
            return
        required_cols = {"game_id", "game_date", "wins", "losses"}
        if not required_cols.issubset(games_df.columns):
            st.warning(f"games_df must contain {required_cols}.")
            return

        st.markdown(
            """
            <div style="
                background-color:#F8F9FC;
                padding:10px;
                border-radius:6px;
                border-color:#DADADA;
                margin:0px 0;
                font-size:1.2em;
                font-weight:400;
            ">
                Wins vs Losses Over Time
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- Prepare data
        games_df = games_df.copy()
        games_df["game_date"] = pd.to_datetime(games_df["game_date"])
        games_df = games_df.sort_values("game_date", ascending=True).reset_index(
            drop=True
        )

        # Positive wins (blue) and negative losses (red)
        wins = games_df["wins"]
        losses = -games_df["losses"]  # negative for downward plotting

        # --- Build figure
        fig = go.Figure()

        # Wins histogram
        fig.add_trace(
            go.Bar(
                x=games_df["game_date"],
                y=wins,
                name="Wins",
                marker_color="rgba(63,131,242,0.4)",  # faint blue
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Wins: %{y}<extra></extra>",
            )
        )

        # Losses histogram
        fig.add_trace(
            go.Bar(
                x=games_df["game_date"],
                y=losses,
                name="Losses",
                marker_color="rgba(255,0,0,0.4)",  # faint red
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Losses: %{y}<extra></extra>",
            )
        )

        # Highlight current game
        if current_game_id in games_df["game_id"].values:
            row = games_df.loc[games_df["game_id"] == current_game_id].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[row["game_date"]],
                    y=[row["wins"]],
                    mode="markers",
                    marker=dict(size=14, color="blue", symbol="star"),
                    name="Selected Game (Win)",
                )
                if row["wins"] > 0
                else go.Scatter(
                    x=[row["game_date"]],
                    y=[-row["losses"]],
                    mode="markers",
                    marker=dict(size=14, color="red", symbol="star"),
                    name="Selected Game (Loss)",
                )
            )

        fig.update_layout(
            autosize=True,
            barmode="overlay",  # overlap wins and losses
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(family="Montserrat, sans-serif", size=14, color="black"),
            xaxis=dict(
                title="Game Date",
                showgrid=True,
                zeroline=False,
            ),
            yaxis=dict(
                title="Wins (blue) / Losses (red)",
                zeroline=True,
                zerolinecolor="black",
            ),
            margin=dict(l=75, r=20, t=20, b=40),
            showlegend=True,
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
