import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity


def fit_kmeans(embeddings, k, random_state=42):
    """
    Entrena KMeans y devuelve labels y centroides
    """
    kmeans = KMeans(
        n_clusters=k,
        random_state=random_state,
        n_init="auto"
    )
    labels = kmeans.fit_predict(embeddings)
    centroids = kmeans.cluster_centers_

    return kmeans, labels, centroids


def compute_similarity_to_centroid(embeddings, labels, centroids):
    """
    Calcula la similitud coseno de cada punto a su centroide
    """
    similarities = []

    for i, emb in enumerate(embeddings):
        cluster_id = labels[i]
        centroid = centroids[cluster_id].reshape(1, -1)
        sim = cosine_similarity(emb.reshape(1, -1), centroid)[0][0]
        similarities.append(sim)

    return np.array(similarities)


def find_optimal_k(embeddings, k_min=3, k_max=10):
    """
    Busca el K óptimo usando silhouette score
    """
    scores = {}

    for k in range(k_min, k_max + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(embeddings)

        score = silhouette_score(embeddings, labels, metric="cosine")
        scores[k] = score

    best_k = max(scores, key=scores.get)
    return best_k, scores
