import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render_wins_losses_histogram(games_df: pd.DataFrame, current_game_id: int) -> None:
    """
    Render cumulative win-loss differential as bars:
    - Blue if differential >= 0
    - Red if differential < 0

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
        if games_df is None or games_df.empty:
            st.info("No game data available for win-loss differential.")
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
                Win-Loss Differential
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

        # Compute cumulative differential
        games_df["differential"] = games_df["wins"] - games_df["losses"]

        # Split into positive/negative for coloring
        positive_mask = games_df["differential"] >= 0
        negative_mask = ~positive_mask

        fig = go.Figure()

        # Blue bars for positive differential
        fig.add_trace(
            go.Bar(
                x=list(games_df.loc[positive_mask, "game_date"]),
                y=list(games_df.loc[positive_mask, "differential"]),
                name="Above .500",
                marker_color="rgba(63,131,242,0.6)",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Differential: %{y}<extra></extra>",
            )
        )

        # Red bars for negative differential
        fig.add_trace(
            go.Bar(
                x=list(games_df.loc[negative_mask, "game_date"]),
                y=list(games_df.loc[negative_mask, "differential"]),
                name="Below .500",
                marker_color="rgba(255,0,0,0.6)",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Differential: %{y}<extra></extra>",
            )
        )

        # Highlight current game
        if current_game_id in games_df["game_id"].values:
            row = games_df.loc[games_df["game_id"] == current_game_id].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[row["game_date"]],
                    y=[row["differential"]],
                    mode="markers",
                    marker=dict(size=14, color="black", symbol="star"),
                    name="Selected Game",
                    showlegend=False,
                )
            )

        # Layout
        fig.update_layout(
            autosize=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(family="Montserrat, sans-serif", size=14, color="black"),
            xaxis=dict(showgrid=True, zeroline=False),
            yaxis=dict(zeroline=True, zerolinecolor="black"),
            margin=dict(l=75, r=20, t=20, b=40),
            showlegend=True,
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
