import os
import logging
import pandas as pd
import sys
import joblib
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader
import numpy as np
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
from nlp.scoring import compute_source_score, compute_novelty_scores, compute_recency_score, compute_final_score

from scripts.utils_storage import load_processed_urls, append_processed_urls

logger = logging.getLogger("weekly_pipeline")
logging.basicConfig(level=logging.INFO)

# Get project root for config
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


def save_newsletter_html(out_dir, html, prefix="weekly_news"):
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    path = os.path.join(out_dir, f"{prefix}_{ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

def main():
    cfg = load_config(os.path.join(PROJECT_ROOT, "config", "config.yaml"))
    
    # Get paths from config
    processed_urls_path = cfg["data"]["processed_urls_path"]
    models_dir = cfg["paths"]["models_dir"]
    newsletters_dir = cfg["data"]["newsletters_dir"]

    processed_urls = load_processed_urls(processed_urls_path)
    logger.info("Loaded %d processed URLs", len(processed_urls))

    # 1) Scrapers (configurable desde config.yaml)
    scraping_cfg = cfg["scraping"]
    scrapers = []
    
    if scraping_cfg["xataka"]["enabled"]:
        scrapers.append(XatakaScraper())
    if scraping_cfg["techcrunch"]["enabled"]:
        scrapers.append(TechCrunchScraper(max_pages=scraping_cfg["techcrunch"]["max_pages"]))
    if scraping_cfg["aws"]["enabled"]:
        scrapers.append(AWSScraper(
            max_pages=scraping_cfg["aws"]["max_pages"],
            blogs=scraping_cfg["aws"]["blogs"]
        ))
    if scraping_cfg["huggingface"]["enabled"]:
        scrapers.append(HuggingFaceScraper(
            max_pages=scraping_cfg["huggingface"]["max_pages"],
            sleep_time=scraping_cfg["huggingface"]["sleep_time"]
        ))
    if scraping_cfg["wired"]["enabled"]:
        scrapers.append(WiredScraper(max_pages=scraping_cfg["wired"]["max_pages"]))

    logger.info("Initialized %d scrapers", len(scrapers))

    # 2) Collect new links
    new_links = []
    for s in scrapers:
        try:
            links = s.get_article_links()
            for l in links:
                if l not in processed_urls:
                    new_links.append(l)
        except Exception as e:
            logger.exception("Error scraper %s: %s", type(s).__name__, e)

    logger.info("Found %d new candidate links", len(new_links))
    if not new_links:
        logger.info("No new links; exiting")
        return

    # 3) Scrape each new link
    new_articles = []
    for url in new_links:
        for s in scrapers:
            try:
                if hasattr(s, 'can_handle') and s.can_handle(url):
                    article = s.scrape_article(url)
                    if article:
                        new_articles.append(article)
                    break
            except Exception as e:
                logger.exception("Error scraping %s: %s", url, e)

    if not new_articles:
        logger.info("No articles scraped from new links")
        return

    # 4) Normalize
    normalized = [normalize_article(a) for a in new_articles]
    df_new = pd.DataFrame(normalized)
    df_new = df_new[df_new["is_valid"]].copy()
    logger.info("Normalized %d new articles", len(df_new))

    # 5) Preprocess text
    df_new["text_for_embedding"] = (df_new["title"] + ". " + df_new["content"]).apply(basic_preprocess)

    # 6) Load embedder and compute embeddings for new only
    model_name = cfg["embeddings"]["active_model"]
    embedder = SentenceTransformerEmbedder(model_name)
    embeddings = embedder.encode(df_new["text_for_embedding"].tolist())
    df_new["embedding"] = embeddings.tolist()

    # 7) Load KMeans model and predict clusters
    kmeans_path = os.path.join(models_dir, "kmeans.joblib")
    if not os.path.exists(kmeans_path):
        logger.error("KMeans model not found at %s", kmeans_path)
        return
    kmeans = joblib.load(kmeans_path)
    labels = kmeans.predict(embeddings)
    df_new["cluster"] = labels

    # 8) Scoring
    df_new["source_score"] = df_new["source"].apply(compute_source_score)
    
    # Compute similarity to centroid
    centroids = kmeans.cluster_centers_
    sims = cosine_similarity(embeddings, centroids)
    sim_to_centroid = sims[np.arange(len(labels)), labels]
    df_new["similarity_to_centroid"] = sim_to_centroid
    
    # Compute other scores
    df_new["novelty_score"] = compute_novelty_scores(embeddings, df_new["cluster"].values)
    df_new["recency_score"] = compute_recency_score(df_new)
    
    # Use scoring weights from config
    scoring_cfg = cfg["scoring"]
    df_new = compute_final_score(
        df_new,
        w_similarity=scoring_cfg["w_similarity"],
        w_novelty=scoring_cfg["w_novelty"],
        w_recency=scoring_cfg["w_recency"],
        w_source=scoring_cfg["w_source"]
    )

    # 9) Persist new processed articles
    processed_path = cfg["data"]["processed_path"]
    os.makedirs(os.path.dirname(processed_path), exist_ok=True)
    if os.path.exists(processed_path):
        existing = pd.read_parquet(processed_path)
        combined = pd.concat([existing, df_new], ignore_index=True)
    else:
        combined = df_new
    combined.to_parquet(processed_path, index=False)

    # 10) Update processed_urls
    processed_urls.update(df_new["url"].tolist())
    os.makedirs(os.path.dirname(processed_urls_path), exist_ok=True)
    append_processed_urls(processed_urls_path, df_new["url"].tolist())

    # 11) Build newsletter candidates: top N per cluster
    top_n = cfg["newsletter"]["top_n_per_cluster"]
    top_articles = combined.sort_values("final_score", ascending=False).groupby("cluster").head(top_n)

    # 12) Render HTML via Jinja2
    env = Environment(loader=FileSystemLoader(os.path.join(PROJECT_ROOT, "app", "templates")))
    template = env.get_template("newsletter.html")
    html = template.render(
        generated_at=datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ"),
        articles=top_articles.to_dict(orient="records"),
        title=cfg["newsletter"]["title"]
    )

    html_path = save_newsletter_html(newsletters_dir, html)
    logger.info("Saved newsletter HTML to %s", html_path)

    # 13) Optional: send via email if configured
    if cfg["newsletter"]["send"]:
        try:
            from utils.emailer import send_html_email
            send_html_email(
                subject=f"{cfg['newsletter']['title']} - {datetime.now(timezone.utc).date()}",
                html_path=html_path,
                recipients=cfg["newsletter"]["recipients"]
            )
            logger.info("Newsletter sent to %d recipients", len(cfg["newsletter"]["recipients"]))
        except Exception as e:
            logger.error("Failed to send email: %s", e)



    # 9) Persist new processed articles
    processed_path = cfg["data"]["processed_path"]
    os.makedirs(os.path.dirname(processed_path), exist_ok=True)
    if os.path.exists(processed_path):
        existing = pd.read_parquet(processed_path)
        combined = pd.concat([existing, df_new], ignore_index=True)
    else:
        combined = df_new
    combined.to_parquet(processed_path, index=False)

    # 10) Update processed_urls
    processed_urls.update(df_new["url"].tolist())
    os.makedirs(os.path.dirname(processed_urls_path), exist_ok=True)
    append_processed_urls(processed_urls_path, df_new["url"].tolist())

    # 11) Build newsletter candidates: top N per cluster or per department
    top_n = cfg["newsletter"].get("top_n", 5)
    top_articles = combined.sort_values("final_score", ascending=False).groupby("cluster").head(top_n)

    # 12) Render HTML via Jinja2 (prepare a simple template in templates/newsletter.html)
    env = Environment(loader=FileSystemLoader(os.path.join(PROJECT_ROOT, "frontend", "templates")))
    template = env.get_template("newsletter_weekly.html")
    html = template.render(
        generated_at=datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ"),
        articles=top_articles.to_dict(orient="records"),
        title=cfg["newsletter"].get("title", "AMC - Weekly AI & Tech Newsletter")
    )

    html_path = save_newsletter_html(newsletter_out, html)
    logger.info("Saved newsletter HTML to %s", html_path)

    # 13) Optional: send via SMTP/SendGrid if configured
    if cfg["newsletter"].get("send", False):
        send_html_email(
            subject=f"{cfg['newsletter'].get('title')} - {datetime.now(timezone.utc).date()}",
            html_path=html_path,
            recipients=cfg["newsletter"].get("recipients", [])
        )

if __name__ == "__main__":
    main()

