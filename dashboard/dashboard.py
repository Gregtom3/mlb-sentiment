import streamlit as st
import pandas as pd
import pyodbc
from mlb_sentiment.config import load_synapse_connection

st.title("MLB Data Dashboard (via Synapse View)")

options = {
    "Game Events": "gameEvents",
    "Games": "games",
    "Posts": "posts",
    "Comments": "comments",
}
choice = st.sidebar.selectbox("Choose a dataset:", list(options.keys()))
viewName = options[choice]

nrows = st.sidebar.slider("Rows to preview", 10, 1000, 100)

query = f"SELECT TOP {nrows} * FROM dbo.{viewName};"
with load_synapse_connection() as conn:
    df = pd.read_sql(query, conn)

st.success(f"Loaded {len(df)} rows")
st.dataframe(df)

num_cols = df.select_dtypes(include="number").columns
if len(num_cols) > 0:
    st.line_chart(df[num_cols])
else:
    st.info("No numeric columns found to chart.")
