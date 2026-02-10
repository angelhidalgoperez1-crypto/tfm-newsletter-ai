from sentence_transformers import SentenceTransformer

EMBEDDING_MODELS = {
    "miniLM_multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "distiluse_multilingual": "sentence-transformers/distiluse-base-multilingual-cased-v2",
    "mpnet_en": "sentence-transformers/all-mpnet-base-v2",
}

class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        if model_name not in EMBEDDING_MODELS:
            raise ValueError(f"Modelo no soportado: {model_name}")

        self.model_id = model_name
        self.model = SentenceTransformer(EMBEDDING_MODELS[model_name])

    def encode(self, texts):
        return self.model.encode(
            texts,
            show_progress_bar=True,
            normalize_embeddings=True
        )
