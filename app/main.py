from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Load config
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config.load_config import load_config
from app.pipeline import run_weekly_pipeline

cfg = load_config(os.path.join(PROJECT_ROOT, "config", "config.yaml"))

app = FastAPI(
    title="AI Newsletter Service",
    description="API REST para gestionar y distribuir noticias tecnológicas curadas automáticamente",
    version="1.0.0"
)

# Models
class Article(BaseModel):
    title: str
    url: str
    source: str
    cluster: int
    final_score: float
    scraping_date: str
    
class Feedback(BaseModel):
    url: str
    rating: str  # thumb_up, thumb_down, etc.

# Helper functions
def get_processed_articles_df() -> pd.DataFrame:
    """Load processed articles from parquet"""
    processed_path = cfg["data"]["processed_path"]
    if not os.path.exists(processed_path):
        return pd.DataFrame()
    return pd.read_parquet(processed_path)

def validate_storage() -> dict:
    """Check storage connectivity"""
    try:
        processed_path = cfg["data"]["processed_path"]
        newsletters_dir = cfg["data"]["newsletters_dir"]
        os.makedirs(os.path.dirname(processed_path), exist_ok=True)
        os.makedirs(newsletters_dir, exist_ok=True)
        return {"status": "healthy", "storage": "accessible"}
    except Exception as e:
        return {"status": "unhealthy", "storage": f"error: {str(e)}"}

@app.get("/health")
def health():
    """Endpoint de verificación de estado del servicio"""
    storage_status = validate_storage()
    return {
        "service": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **storage_status
    }

@app.get("/articles", response_model=dict)
def get_articles(
    skip: int = Query(0, ge=0, description="Número de artículos a saltar"),
    limit: int = Query(10, ge=1, le=100, description="Número de artículos a devolver"),
    source: Optional[str] = Query(None, description="Filtrar por fuente"),
    start_date: Optional[str] = Query(None, description="Filtrar desde fecha (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filtrar hasta fecha (YYYY-MM-DD)"),
    cluster: Optional[int] = Query(None, ge=0, description="Filtrar por cluster")
):
    """
    Devuelve lista de artículos procesados con soporte para paginación y filtrado.
    
    Parámetros:
    - skip: número de artículos a saltar (default 0)
    - limit: número de artículos a devolver (default 10, máx 100)
    - source: filtrar por nombre de fuente (ej: "TechCrunch")
    - start_date: filtrar desde esta fecha (formato YYYY-MM-DD)
    - end_date: filtrar hasta esta fecha (formato YYYY-MM-DD)
    - cluster: filtrar por ID de cluster
    """
    try:
        df = get_processed_articles_df()
        if df.empty:
            return {"total": 0, "skip": skip, "limit": limit, "articles": []}
        
        # Apply filters
        if source:
            df = df[df["source"].str.contains(source, case=False, na=False)]
        
        if start_date:
            df = df[df["scraping_date"] >= start_date]
        
        if end_date:
            df = df[df["scraping_date"] <= end_date]
        
        if cluster is not None:
            df = df[df["cluster"] == cluster]
        
        total = len(df)
        
        # Pagination
        df_paginated = df.iloc[skip:skip+limit]
        
        articles = df_paginated[[
            "title", "url", "source", "cluster", "final_score", "scraping_date"
        ]].to_dict(orient="records")
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "returned": len(articles),
            "articles": articles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching articles: {str(e)}")

@app.get("/articles/top", response_model=dict)
def get_top_articles(
    limit: int = Query(10, ge=1, le=50, description="Número de artículos a devolver"),
    cluster: Optional[int] = Query(None, ge=0, description="Filtrar por cluster"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Puntuación mínima")
):
    """
    Devuelve los artículos más relevantes ordenados por final_score en orden descendente.
    Útil para dashboards y secciones destacadas.
    
    Parámetros:
    - limit: número de artículos a devolver (default 10, máx 50)
    - cluster: filtrar por ID de cluster (opcional)
    - min_score: puntuación mínima del artículo (0.0 a 1.0)
    """
    try:
        df = get_processed_articles_df()
        if df.empty:
            return {"total": 0, "articles": []}
        
        # Filter by score
        df = df[df["final_score"] >= min_score]
        
        # Filter by cluster if specified
        if cluster is not None:
            df = df[df["cluster"] == cluster]
        
        # Sort by score and get top
        df_top = df.nlargest(limit, "final_score")
        
        articles = df_top[[
            "title", "url", "source", "cluster", "final_score", "scraping_date"
        ]].to_dict(orient="records")
        
        return {
            "total": len(df),
            "returned": len(articles),
            "articles": articles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top articles: {str(e)}")

@app.post("/run-pipeline")
def run_pipeline(
    generate_only: bool = Query(False, description="Solo generar preview sin guardar")
):
    """
    Lanza el pipeline semanal bajo demanda.
    
    Parámetros:
    - generate_only: si es True, solo genera preview sin guardar resultados
    
    Devuelve un identificador de seguimiento para monitorizar el progreso.
    """
    try:
        # Generate timestamp for tracking
        task_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        
        result = run_weekly_pipeline(generate_only=generate_only)
        
        return {
            "task_id": task_id,
            "status": "completed",
            "message": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@app.get("/preview", response_class=HTMLResponse)
def preview():
    """Genera un preview HTML del newsletter sin guardar"""
    try:
        html = run_weekly_pipeline(generate_only=True)
        return html
    except Exception as e:
        return f"<h1>Error generating preview</h1><p>{str(e)}</p>"

@app.post("/feedback")
def submit_feedback(feedback: Feedback):
    """
    Registra feedback del usuario sobre un artículo.
    
    Parámetros:
    - url: URL del artículo
    - rating: valoración (thumb_up, thumb_down, etc.)
    """
    try:
        feedback_dir = cfg["data"].get("feedback_dir", "data/feedback")
        os.makedirs(feedback_dir, exist_ok=True)
        
        feedback_path = os.path.join(feedback_dir, "feedback.csv")
        
        row = {
            "url": feedback.url,
            "rating": feedback.rating,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        df = pd.DataFrame([row])
        
        if os.path.exists(feedback_path):
            df.to_csv(feedback_path, mode="a", header=False, index=False)
        else:
            df.to_csv(feedback_path, index=False)
        
        return {
            "message": "Feedback recorded successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving feedback: {str(e)}")

@app.get("/docs", include_in_schema=False)
def custom_docs():
    """Documentación interactiva de la API (OpenAPI)"""
    return {"message": "API documentation available at /docs"}

