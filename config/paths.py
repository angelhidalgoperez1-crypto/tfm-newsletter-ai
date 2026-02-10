import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
DIAGNOSTICS_DIR = os.path.join(PROJECT_ROOT, "output",
                               "diagnostics")
NEWSLETTER_DIR = os.path.join(PROJECT_ROOT, "output",
                             "newsletter")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")