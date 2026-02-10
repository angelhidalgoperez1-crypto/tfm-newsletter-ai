import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


def top_terms_per_cluster(
    X_tfidf,
    clusters,
    vectorizer,
    top_n=10
):
    """
    Extrae los términos más representativos de cada cluster
    a partir de una matriz TF-IDF ya entrenada.
    """

    terms = np.array(vectorizer.get_feature_names_out())
    cluster_terms = {}

    for cluster_id in np.unique(clusters):
        cluster_mask = clusters == cluster_id
        cluster_tfidf = X_tfidf[cluster_mask]

        # media TF-IDF por término dentro del cluster
        mean_tfidf = cluster_tfidf.mean(axis=0).A1

        top_indices = mean_tfidf.argsort()[::-1][:top_n]
        cluster_terms[cluster_id] = terms[top_indices].tolist()

    return cluster_terms


def name_clusters(cluster_keywords):
    """
    Generate human-readable cluster names from extracted keywords.
    
    Creates concise cluster names by joining the top 3 keywords with a forward slash
    separator and converting to title case.
    
    Args:
        cluster_keywords (dict): Dictionary mapping cluster IDs to lists of keywords
            (typically from `top_terms_per_cluster` using TF-IDF scores).
        
    Returns:
        dict: Cluster IDs mapped to human-readable names in format "Keyword1 / Keyword2 / Keyword3".
        
    Example:
        >>> cluster_keywords = {0: ['machine', 'learning', 'algorithm']}
        >>> name_clusters(cluster_keywords)
        {0: 'Machine / Learning / Algorithm'}
    """
    cluster_names = {}

    for cluster_id, keywords in cluster_keywords.items():
        name = " / ".join(keywords[:3])
        cluster_names[cluster_id] = name.title()

    return cluster_names
