# pipeline.py

import os
import pandas as pd
import joblib
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader
from sklearn.metrics.pairwise import cosine_similarity

from config.load_config import load_config
from scraping.normalization import normalize_article
from scraping.sources.scraper_xataka import XatakaScraper
from scraping.sources.scraper_huggingface import HuggingFaceScraper
from scraping.sources.scraper_techcrunch import TechCrunchScraper
from scraping.sources.scraper_aws import AWSScraper
from scraping.sources.scraper_wired import WiredScraper
from scraping.sources.scraper_microsoft import MicrosoftNewsScraper
from scraping.sources.scraper_aibusiness import AIBusinessScraper

from nlp.preprocessing import basic_preprocess
from nlp.embeddings import SentenceTransformerEmbedder
from nlp.scoring import (
    compute_source_score,
    compute_novelty_scores,
    compute_recency_score,
    compute_final_score
)

from scripts.utils_storage import load_processed_urls, append_processed_urls


def run_pipeline():

    cfg = load_config()
    models_dir = cfg["models"]["dir"]

    processed_urls = load_processed_urls(
        cfg["data"]["processed_urls"]
    )

    # ==========================================================
    # SCRAPERS
    # ==========================================================

    scrapers = [
        XatakaScraper(),
        HuggingFaceScraper(),
        TechCrunchScraper(max_pages=cfg["scraping"].get("max_pages_per_tag", 5)),
        AWSScraper(max_pages=cfg["scraping"].get("aws_max_pages", 5)),
        # WiredScraper(max_pages=cfg["scraping"].get("wired_max_pages", 5)),
        # MicrosoftNewsScraper(),
        # AIBusinessScraper()
    ]

    # ==========================================================
    # NEW LINKS
    # ==========================================================

    new_links = []
    for s in scrapers:
        links = s.get_article_links()
        for l in links:
            if l not in processed_urls:
                new_links.append(l)

    if not new_links:
        print("No new articles.")
        return


    new_articles = []
    for url in new_links:
        for s in scrapers:
            if s.can_handle(url):
                article = s.scrape_article(url)
                if article:
                    new_articles.append(article)
                break

    if not new_articles:
        print("No valid articles scraped.")
        return

    # ==========================================================
    # NORMALIZATION
    # ==========================================================

    normalized = [normalize_article(a) for a in new_articles]
    df_new = pd.DataFrame(normalized)
    df_new = df_new[df_new["is_valid"]].copy()

    if df_new.empty:
        print("No valid normalized articles.")
        return

    # ==========================================================
    # PREPROCESS
    # ==========================================================

    df_new["text_for_embedding"] = (
        df_new["title"] + ". " + df_new["content"]
    ).apply(basic_preprocess)

    # ==========================================================
    # EMBEDDINGS
    # ==========================================================

    model_name = cfg["embeddings"]["active_model"]
    embedder = SentenceTransformerEmbedder(model_name)

    embeddings = embedder.encode(
        df_new["text_for_embedding"].tolist()
    )

    df_new["embedding"] = embeddings.tolist()

    # ==========================================================
    # KMEANS
    # ==========================================================

    kmeans = joblib.load(
        os.path.join(models_dir, "kmeans.joblib")
    )

    labels = kmeans.predict(embeddings)
    df_new["cluster"] = labels

    # Similaridad a centroide
    centroids = kmeans.cluster_centers_
    sims = cosine_similarity(embeddings, centroids)
    sim_to_centroid = sims[
        range(len(labels)),
        labels
    ]

    df_new["similarity_to_centroid"] = sim_to_centroid

    # ==========================================================
    # SCORING
    # ==========================================================

    df_new["source_score"] = df_new["source"].apply(
        compute_source_score
    )

    df_new["novelty_score"] = 1 - df_new["similarity_to_centroid"]

    df_new["recency_score"] = compute_recency_score(
        df_new["published_date"]
    )

    df_new = compute_final_score(
        df_new
    )

    # ==========================================================
    # PERSISTENCE
    # ==========================================================

    processed_parquet = cfg["data"]["processed_parquet"]

    if os.path.exists(processed_parquet):
        existing = pd.read_parquet(processed_parquet)
        combined = pd.concat(
            [existing, df_new],
            ignore_index=True
        )
    else:
        combined = df_new

    combined.to_parquet(
        processed_parquet,
        index=False
    )

    append_processed_urls(
        cfg["data"]["processed_urls"],
        df_new["url"].tolist()
    )

    # ==========================================================
    # SELECCIÓN NEWSLETTER
    # ==========================================================

    top_n = cfg["newsletter"].get("top_n", 5)

    top_articles = (
        combined
        .sort_values("final_score", ascending=False)
        .groupby("cluster")
        .head(top_n)
    )

    return top_articles
