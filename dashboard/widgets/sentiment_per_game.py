import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render_win_loss_sentiment_widget(
    comments_df: pd.DataFrame,
    games_df: pd.DataFrame,
    team_acronym: str,
    rolling_window: int = 5,
    ci_factor: float = 1.0,  # 1=std band, ~2≈95% CI
) -> None:
    """
    Plot rolling average of average sentiment per game,
    split by victories and losses, with error bands.

    Parameters
    ----------
    comments_df : pd.DataFrame
        Must contain ['game_id','sentiment_score'].
    games_df : pd.DataFrame
        Must contain ['game_id','game_date','home_team','away_team','home_score','away_score'].
    team_acronym : str
        Team acronym to determine wins/losses.
    rolling_window : int
        Rolling average window size (default 5 games).
    ci_factor : float
        Scale of std for bands (default 1.0 for ±1σ).
    """

    # --- Styling
    container_css = """
.st-key-winloss-sentiment-container {
    background-color: #FFFFFF;
    padding: 10px;
}
    """
    st.html(f"<style>{container_css}</style>")

    with st.container(border=True, key="winloss-sentiment-container", height=530):

        if comments_df is None or comments_df.empty:
            st.info("No comments available for win/loss sentiment chart.")
            return
        if games_df is None or games_df.empty:
            st.info("No games available for win/loss sentiment chart.")
            return

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
                Rolling Sentiment by Game Outcome ({team_acronym})
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- Prep data
        comments_df = comments_df.copy()
        games_df = games_df.copy()

        # Average sentiment per game
        game_sent = (
            comments_df.groupby("game_id")["sentiment_score"]
            .mean()
            .reset_index()
            .rename(columns={"sentiment_score": "avg_sentiment"})
        )

        merged = pd.merge(
            games_df,
            game_sent,
            on="game_id",
            how="inner",
        )

        merged["game_date"] = pd.to_datetime(merged["game_date"])

        # Determine win/loss
        def outcome(row):
            if pd.isna(row["home_score"]) or pd.isna(row["away_score"]):
                return "Unknown"
            if row["home_team"] == team_acronym:
                return "Win" if row["home_score"] > row["away_score"] else "Loss"
            elif row["away_team"] == team_acronym:
                return "Win" if row["away_score"] > row["home_score"] else "Loss"
            return "Other"

        merged["Outcome"] = merged.apply(outcome, axis=1)
        merged = merged[merged["Outcome"].isin(["Win", "Loss"])].sort_values(
            "game_date"
        )

        if merged.empty:
            st.info("No games found with wins/losses for this team.")
            return

        # Compute rolling stats separately for Wins and Losses
        win_df = merged[merged["Outcome"] == "Win"].copy()
        loss_df = merged[merged["Outcome"] == "Loss"].copy()

        for df in [win_df, loss_df]:
            df["rolling_mean"] = (
                df["avg_sentiment"].rolling(rolling_window, min_periods=1).mean()
            )
            df["rolling_std"] = (
                df["avg_sentiment"].rolling(rolling_window, min_periods=1).std()
            )
            df["upper"] = df["rolling_mean"] + ci_factor * df["rolling_std"]
            df["lower"] = df["rolling_mean"] - ci_factor * df["rolling_std"]

        abs_max_sentiment = (
            max(
                merged["avg_sentiment"].abs().max(),
                win_df["upper"].abs().max() if not win_df.empty else 0,
                loss_df["upper"].abs().max() if not loss_df.empty else 0,
            )
            + 0.1
        )

        # --- Plot
        fig = go.Figure()

        # Wins scatter
        fig.add_trace(
            go.Scatter(
                x=win_df["game_date"],
                y=win_df["avg_sentiment"],
                mode="markers",
                marker=dict(color="green", size=10, symbol="triangle-up"),
                name="Win (avg sentiment)",
            )
        )
        # Losses scatter
        fig.add_trace(
            go.Scatter(
                x=loss_df["game_date"],
                y=loss_df["avg_sentiment"],
                mode="markers",
                marker=dict(color="red", size=10, symbol="triangle-down"),
                name="Loss (avg sentiment)",
            )
        )

        # Win rolling line + error band
        fig.add_trace(
            go.Scatter(
                x=win_df["game_date"],
                y=win_df["rolling_mean"],
                mode="lines",
                line=dict(color="darkgreen", width=2),
                name=f"Win Rolling Avg ({rolling_window})",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=pd.concat([win_df["game_date"], win_df["game_date"][::-1]]),
                y=pd.concat([win_df["upper"], win_df["lower"][::-1]]),
                fill="toself",
                fillcolor="rgba(0,128,0,0.2)",
                line=dict(color="rgba(0,0,0,0)"),
                hoverinfo="skip",
                name="Win ±1σ",
                showlegend=True,
            )
        )

        # Loss rolling line + error band
        fig.add_trace(
            go.Scatter(
                x=loss_df["game_date"],
                y=loss_df["rolling_mean"],
                mode="lines",
                line=dict(color="darkred", width=2),
                name=f"Loss Rolling Avg ({rolling_window})",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=pd.concat([loss_df["game_date"], loss_df["game_date"][::-1]]),
                y=pd.concat([loss_df["upper"], loss_df["lower"][::-1]]),
                fill="toself",
                fillcolor="rgba(255,0,0,0.2)",
                line=dict(color="rgba(0,0,0,0)"),
                hoverinfo="skip",
                name="Loss ±1σ",
                showlegend=True,
            )
        )

        fig.update_layout(
            paper_bgcolor="white",
            plot_bgcolor="white",
            yaxis=dict(
                title="Average Sentiment",
                range=[-abs_max_sentiment, abs_max_sentiment],
            ),
            xaxis=dict(title="Game Date (EST)"),
            margin=dict(l=40, r=20, t=40, b=40),
        )

        st.plotly_chart(fig, use_container_width=True)
