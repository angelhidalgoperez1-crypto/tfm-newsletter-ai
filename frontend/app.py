import streamlit as st
import pandas as pd
from IPython.display import HTML

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="AI Newsletter – AMC",
    layout="wide"
)

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data
def load_data():
    return pd.read_pickle("data/processed/even_more_articles.pkl")

df = load_data()

# -----------------------------
# SIDEBAR FILTERS
# -----------------------------
st.sidebar.title("Filtros")

sources = ["Todas"] + sorted(df["source"].dropna().unique().tolist())
selected_source = st.sidebar.selectbox(
    "Fuente / Revista",
    sources
)

areas = ["Todas"] + sorted(df["area"].dropna().unique().tolist())
selected_area = st.sidebar.selectbox(
    "Área AMC",
    areas
)

top_k = st.sidebar.slider(
    "Número de noticias",
    min_value=5,
    max_value=30,
    value=10
)

# -----------------------------
# FILTER DATA
# -----------------------------
filtered_df = df.copy()

if selected_source != "Todas":
    filtered_df = filtered_df[filtered_df["source"] == selected_source]

if selected_area != "Todas":
    filtered_df = filtered_df[filtered_df["area"] == selected_area]

filtered_df = filtered_df.sort_values(
    "final_score", ascending=False
).head(top_k)

# -----------------------------
# MAIN VIEW
# -----------------------------
st.title("🧠 Newsletter Inteligente – AMC Global")

st.markdown(
    f"""
    **Fuente:** {selected_source}  
    **Área:** {selected_area}  
    **Noticias mostradas:** {len(filtered_df)}
    """
)

st.divider()

# -----------------------------
# RENDER ARTICLES
# -----------------------------
for _, row in filtered_df.iterrows():
    st.markdown(
        f"""
        <div style="
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #3498DB;
            background-color: #F9F9F9;
        ">
            <h4>{row['title']}</h4>
            <i>{row['source']} · {row.get('language','')}</i><br><br>
            <a href="{row['url']}" target="_blank">Leer más</a>
        </div>
        """,
        unsafe_allow_html=True
    )
