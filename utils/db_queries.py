import pandas as pd
import streamlit as st


@st.cache_data(ttl=45, show_spinner=False)
def cached_read_sql(_conn, query, params=()):
    return pd.read_sql_query(query, _conn, params=tuple(params or ()))
