import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from config import get_settings


class SemanticMatcher:
    def __init__(self) -> None:
        settings = get_settings()
        self._model_name: str = settings.SENTENCE_TRANSFORMER_MODEL
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def encode(self, text: str) -> np.ndarray:
        if not text.strip():
            raise ValueError("Cannot encode empty text.")
        model = self._load_model()
        embedding: np.ndarray = model.encode(text, convert_to_numpy=True)
        return embedding

    def similarity(self, text_a: str, text_b: str) -> float:
        vec_a = self.encode(text_a).reshape(1, -1)
        vec_b = self.encode(text_b).reshape(1, -1)
        score: float = float(cosine_similarity(vec_a, vec_b)[0][0])
        return max(0.0, min(1.0, score))
