import pandas as pd
import ast
import sys
import os

from config.load_config import load_config
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

# Load config
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

cfg = load_config(os.path.join(PROJECT_ROOT, "config", "config.yaml"))

# ---- Loading data
raw_path = cfg["data"]["raw_path"]
df = pd.read_csv(raw_path, sep=";")

# ---- preprocessing
df["text_for_embedding"] = (
    df["title"] + ". " + df["content"]
).apply(basic_preprocess)

# ---- embeddings
embedder = MultilingualEmbedder()
embeddings = embedder.encode(df["text_for_embedding"].tolist())

# ---- clustering (use n_clusters from config)
K = cfg["clustering"]["n_clusters"]
labels, centroids = fit_kmeans(embeddings, K)
df["cluster"] = labels

df["similarity_to_centroid"] = compute_similarity_to_centroid(
    embeddings, labels, centroids
)

# ---- Interpretation
keywords = top_terms_per_cluster(df)
cluster_names = name_clusters(keywords)
df["cluster_name"] = df["cluster"].map(cluster_names)

# ---- scoring (use weights from config)
df["novelty_score"] = compute_novelty_scores(embeddings, labels)
df["recency_score"] = compute_recency_score(df)
df["source_score"] = compute_source_score(df)

scoring_cfg = cfg["scoring"]
df = compute_final_score(
    df,
    w_similarity=scoring_cfg["w_similarity"],
    w_novelty=scoring_cfg["w_novelty"],
    w_recency=scoring_cfg["w_recency"],
    w_source=scoring_cfg["w_source"]
)

# ---- Persistence
processed_path = cfg["data"]["processed_path"]
os.makedirs(os.path.dirname(processed_path), exist_ok=True)
df["embedding"] = embeddings.tolist()
df.to_csv(f"{processed_path.replace('.parquet', '')}.csv", sep=";", index=False)
df.to_parquet(processed_path, index=False)

print("✅ Pipeline completado")
