import streamlit as st
import pandas as pd
import pyodbc
from mlb_sentiment.config import load_synapse_client

synapse_config = load_synapse_client()
SERVER = synapse_config["server"]
DATABASE = synapse_config["database"]
USERNAME = synapse_config["username"]
PASSWORD = synapse_config["password"]

def get_connection():
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={SERVER};DATABASE={DATABASE};"
        f"UID={USERNAME};PWD={PASSWORD};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(conn_str)

st.title("MLB Data Dashboard (via Synapse View)")

nrows = st.sidebar.slider("Rows to preview", 10, 1000, 100)

query = f"SELECT TOP {nrows} * FROM dbo.mlb_data;"
with get_connection() as conn:
    df = pd.read_sql(query, conn)

st.success(f"Loaded {len(df)} rows")
st.dataframe(df)

num_cols = df.select_dtypes(include="number").columns
if len(num_cols) > 0:
    st.line_chart(df[num_cols])
else:
    st.info("No numeric columns found to chart.")
