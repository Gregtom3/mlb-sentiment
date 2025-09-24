import pandas as pd
import streamlit as st


@st.cache_data
def compute_sentiment_ts(
    comments_df: pd.DataFrame, window_minutes: int = 2
) -> pd.DataFrame:
    if comments_df.empty:
        return pd.DataFrame()
    sentiment_ts = (
        comments_df.set_index("created_est")
        .resample(f"{window_minutes}Min")["sentiment_score"]
        .mean()
        .reset_index()
    )
    sentiment_ts["sentiment_smooth"] = (
        sentiment_ts["sentiment_score"]
        .rolling(window=3, min_periods=1, center=True)
        .mean()
    )
    return sentiment_ts
