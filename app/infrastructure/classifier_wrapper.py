import os
import tempfile

import fasttext


class ClassifierWrapper:
    """Adapter over FastText for training and prediction."""

    def __init__(self) -> None:
        self._model: fasttext.FastText._FastText | None = None

    def train(self, texts: list[str], labels: list[str]) -> None:
        """Train a supervised FastText model. labels[i] is the topic_id for texts[i]."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            for text, label in zip(texts, labels):
                # FastText supervised format: __label__<label> <text>
                clean = text.replace("\n", " ").strip()
                f.write(f"__label__{label} {clean}\n")
            tmp_path = f.name
        try:
            self._model = fasttext.train_supervised(
                input=tmp_path,
                epoch=25,
                lr=0.5,
                wordNgrams=2,
                verbose=0,
            )
        finally:
            os.unlink(tmp_path)

    def predict(self, text: str) -> tuple[str, float]:
        """Return (topic_id, confidence) for the given text."""
        if self._model is None:
            raise RuntimeError("Model not trained or loaded")
        clean = text.replace("\n", " ").strip()
        labels, probs = self._model.predict(clean, k=1)
        # Strip the __label__ prefix FastText adds to returned labels
        label = labels[0].replace("__label__", "")
        return label, float(probs[0])

    def save(self, path: str) -> None:
        if self._model is None:
            raise RuntimeError("No model to save")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._model.save_model(path)

    def load(self, path: str) -> None:
        self._model = fasttext.load_model(path)
