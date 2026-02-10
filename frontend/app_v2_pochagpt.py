import streamlit as st
import pandas as pd
import ast

st.set_page_config(page_title="AI Newsletter Engine", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("data/processed/articles_scored.csv", sep=";")
    df["embedding"] = df["embedding"].apply(ast.literal_eval)
    return df

df = load_data()

st.title("📰 AI-powered Newsletter Generator")

# ---- filtros
sources = st.multiselect(
    "Fuente",
    options=sorted(df["source"].unique()),
    default=sorted(df["source"].unique())
)

clusters = st.multiselect(
    "Área / Cluster",
    options=sorted(df["cluster_name"].unique()),
    default=sorted(df["cluster_name"].unique())
)

top_n = st.slider("Número de noticias", 3, 20, 8)

filtered = df[
    (df["source"].isin(sources)) &
    (df["cluster_name"].isin(clusters))
]

filtered = filtered.sort_values("final_score", ascending=False).head(top_n)

# ---- render
for _, row in filtered.iterrows():
    st.markdown(f"""
### {row['title']}
**Fuente:** {row['source']}  
**Área:** {row['cluster_name']}  
[Leer artículo]({row['url']})
---
""")
