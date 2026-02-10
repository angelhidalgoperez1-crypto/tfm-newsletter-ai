import pandas as pd
import ast

from nlp.preprocessing import basic_preprocess
from nlp.embeddings import MultilingualEmbedder
from nlp.clustering import fit_kmeans, compute_similarity_to_centroid
from nlp.interpretation import top_terms_per_cluster, name_clusters
from nlp.scoring import (
    compute_novelty_scores,
    compute_recency_score,
    compute_source_score,
    compute_final_score
)

# ---- cargar datos
df = pd.read_csv("data/raw/even_more_articles_normalized.csv", sep=";")

# ---- preprocessing
df["text_for_embedding"] = (
    df["title"] + ". " + df["content"]
).apply(basic_preprocess)

# ---- embeddings
embedder = MultilingualEmbedder()
embeddings = embedder.encode(df["text_for_embedding"].tolist())

# ---- clustering
K = 8
labels, centroids = fit_kmeans(embeddings, K)
df["cluster"] = labels

df["similarity_to_centroid"] = compute_similarity_to_centroid(
    embeddings, labels, centroids
)

# ---- interpretación
keywords = top_terms_per_cluster(df)
cluster_names = name_clusters(keywords)
df["cluster_name"] = df["cluster"].map(cluster_names)

# ---- scoring
df["novelty_score"] = compute_novelty_scores(embeddings, labels)
df["recency_score"] = compute_recency_score(df)
df["source_score"] = compute_source_score(df)

df = compute_final_score(df)

# ---- persistencia
df["embedding"] = embeddings.tolist()
df.to_csv("data/processed/articles_scored.csv", sep=";", index=False)

print("✅ Pipeline completado")
