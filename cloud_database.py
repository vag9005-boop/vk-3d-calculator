import streamlit as st
from sqlalchemy import create_engine
from urllib.parse import quote_plus

def get_cloud_engine():
    cloud = st.secrets["cloud"]
    url = (
        f"postgresql+psycopg2://"
        f"{cloud['user']}:{quote_plus(cloud['password'])}"
        f"@{cloud['host']}:{cloud['port']}/{cloud['dbname']}"
        f"?sslmode=require"
    )
    # Каждый раз создаем новое подключение, без кэша
    return create_engine(url, pool_pre_ping=True)