import os
import pandas as pd
from datetime import datetime, timezone
import joblib
import numpy as np

def load_processed_urls(master_path):
    if os.path.exists(master_path):
        return set(pd.read_csv(master_path).url.tolist())
    return set()

def append_processed_urls(master_path, new_urls, history_dir=None):
    os.makedirs(os.path.dirname(master_path), exist_ok=True)
    # load existing if any
    existing = pd.DataFrame({"url": list(load_processed_urls(master_path))})
    new_df = pd.DataFrame({"url": list(new_urls)})
    combined = pd.concat([existing, new_df], ignore_index=True).drop_duplicates().reset_index(drop=True)
    combined.to_csv(master_path, index=False)
    # historico
    if history_dir:
        os.makedirs(history_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d")
        combined.to_csv(os.path.join(history_dir, f"processed_urls_{ts}.csv"), index=False)

def save_model_version(obj, models_dir, name_prefix):
    os.makedirs(models_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = os.path.join(models_dir, f"{name_prefix}_v{ts}.joblib")
    joblib.dump(obj, path)
    return path

def save_embeddings(arr, models_dir, name_prefix):
    os.makedirs(models_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = os.path.join(models_dir, f"{name_prefix}_v{ts}.npz")
    np.savez_compressed(path, embeddings=arr)
    return path
