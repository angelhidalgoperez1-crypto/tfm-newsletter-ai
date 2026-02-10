import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


def compute_novelty_scores(embeddings, labels):
    """
    Mide cuán diferente es una noticia respecto a su cluster
    (1 - similitud media con el resto del cluster)
    """
    novelty_scores = np.zeros(len(embeddings))

    for cluster_id in np.unique(labels):
        idx = np.where(labels == cluster_id)[0]
        cluster_embeddings = embeddings[idx]

        sims = cosine_similarity(cluster_embeddings)
        avg_sim = sims.mean(axis=1)

        novelty_scores[idx] = 1 - avg_sim

    return novelty_scores

def compute_recency_score(df, date_col="scraping_date", decay_days=30):
    """
    Score exponencial: noticias recientes valen más
    """
    now = pd.Timestamp.now()
    delta_days = (now - pd.to_datetime(df[date_col])).dt.days

    recency_score = np.exp(-delta_days / decay_days)
    return recency_score

def compute_source_score(df, source_col="source"):
    """
    Peso manual por fuente (editable)
    """
    source_weights = {
        "TechCrunch": 1.0,
        "Hugging Face Blog": 0.9,
        "AWS ML Blog": 0.85,
        "Xataka": 0.7,
        "Wired ES": 0.6
    }

    return df[source_col].map(source_weights).fillna(0.5)

def compute_final_score(
    df,
    w_similarity=0.4,
    w_novelty=0.3,
    w_recency=0.2,
    w_source=0.1
):
    """
    Score final ponderado
    """
    df["final_score"] = (
        w_similarity * df["similarity_to_centroid"] +
        w_novelty * df["novelty_score"] +
        w_recency * df["recency_score"] +
        w_source * df["source_score"]
    )

    return df
