import os
import sys
import logging
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timezone

from config.load_config import load_config
from scraping.normalization import normalize_article
from scraping.sources.scraper_xataka import XatakaScraper
from scraping.sources.scraper_techcrunch import TechCrunchScraper
from scraping.sources.scraper_aws import AWSScraper
from scraping.sources.scraper_wired import WiredScraper
from nlp.preprocessing import basic_preprocess
from nlp.embeddings import SentenceTransformerEmbedder
from nlp.clustering import find_optimal_k, fit_kmeans
from nlp.interpretation import top_terms_per_cluster_texts
from nlp.cleaning_tfidf import compute_tfidf

logger = logging.getLogger("full_retrain")
logging.basicConfig(level=logging.INFO)

# Get project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def full_scrape_and_build_corpus(scraping_cfg):
    """Scrape articles from all enabled sources"""
    scrapers = []
    
    if scraping_cfg["xataka"]["enabled"]:
        scrapers.append(XatakaScraper())
    if scraping_cfg["techcrunch"]["enabled"]:
        scrapers.append(TechCrunchScraper(max_pages=scraping_cfg["techcrunch"].get("max_pages", 50)))
    if scraping_cfg["aws"]["enabled"]:
        scrapers.append(AWSScraper(
            max_pages=scraping_cfg["aws"].get("max_pages", 50),
            blogs=scraping_cfg["aws"].get("blogs", [])
        ))
    if scraping_cfg["wired"]["enabled"]:
        scrapers.append(WiredScraper(max_pages=scraping_cfg["wired"].get("max_pages", 50)))
    
    articles = []
    for s in scrapers:
        try:
            logger.info(f"Scraping from {type(s).__name__}")
            links = s.get_article_links()
            for url in links:
                article = s.scrape_article(url)
                if article:
                    articles.append(article)
        except Exception as e:
            logger.exception(f"Error scraping {type(s).__name__}: {e}")
    
    normalized = [normalize_article(a) for a in articles]
    df = pd.DataFrame(normalized)
    df = df[df["is_valid"]].copy()
    return df

def main():
    cfg = load_config(os.path.join(PROJECT_ROOT, "config", "config.yaml"))
    
    models_dir = cfg["paths"]["models_dir"]
    os.makedirs(models_dir, exist_ok=True)

    # 1) Full scrape and build corpus
    logger.info("Starting full scrape...")
    df = full_scrape_and_build_corpus(cfg["scraping"])
    logger.info("Full corpus size: %d", len(df))

    # 2) Preprocess text for embeddings
    df["text_for_embedding"] = (df["title"] + ". " + df["content"]).apply(basic_preprocess)

    # 3) Compute embeddings
    embeddings_cfg = cfg["embeddings"]
    model_name = embeddings_cfg["active_model"]
    logger.info(f"Computing embeddings with {model_name}")
    embedder = SentenceTransformerEmbedder(model_name)
    embeddings = embedder.encode(df["text_for_embedding"].tolist())
    np.save(os.path.join(models_dir, "embeddings.npy"), embeddings)
    logger.info("Embeddings saved")

    # 4) Find optimal k and fit KMeans
    clustering_cfg = cfg["clustering"]
    k_min = clustering_cfg.get("k_min", 4)
    k_max = clustering_cfg.get("k_max", 12)
    logger.info(f"Finding optimal k (range: {k_min}-{k_max})")
    
    best_k, scores = find_optimal_k(embeddings, k_min=k_min, k_max=k_max)
    logger.info("Best k: %s", best_k)

    # Fit KMeans
    kmeans_model, labels, centroids = fit_kmeans(embeddings, k=best_k)
    df["cluster"] = labels

    # 5) TF-IDF for interpretation
    logger.info("Computing TF-IDF...")
    df["text_tfidf"] = df["content"].apply(basic_preprocess)
    X_tfidf, tfidf_vectorizer = compute_tfidf(df["text_tfidf"])
    cluster_terms = top_terms_per_cluster_texts(X_tfidf, df["cluster"], tfidf_vectorizer, top_n=12)

    # 6) Save models and artifacts
    logger.info("Saving models and artifacts to %s", models_dir)
    joblib.dump(kmeans_model, os.path.join(models_dir, "kmeans.joblib"))
    joblib.dump(tfidf_vectorizer, os.path.join(models_dir, "tfidf_vectorizer.joblib"))
    
    # Save corpus with cluster assignments
    corpus_path = os.path.join(models_dir, f"corpus_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%MZ')}.parquet")
    df.to_parquet(corpus_path, index=False)
    logger.info("Corpus saved to %s", corpus_path)

    # 7) Save metadata
    meta = {
        "best_k": int(best_k),
        "k_scores": [float(s) for s in scores],
        "embedding_model": model_name,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    }
    joblib.dump(meta, os.path.join(models_dir, "retrain_meta.joblib"))
    logger.info("Metadata saved")

    logger.info("✅ Retrain finished. Artifacts in %s", models_dir)

if __name__ == "__main__":
    main()

