import os
import tempfile

import fasttext


class ClassifierWrapper:
    """Adapter over FastText for training, prediction and model persistence.

    Wraps a single supervised FastText model. One wrapper trains and saves a model
    during training, and another loads and predicts with it during labelling.
    """

    def __init__(self) -> None:
        """Create an empty wrapper holding no model until trained or loaded."""
        self._model: fasttext.FastText._FastText | None = None

    def train(self, texts: list[str], labels: list[str]) -> None:
        """Train a supervised FastText model from labelled texts.

        Writes the texts in FastText's ``__label__<label> <text>`` format to a
        temporary file, trains, and removes the file afterward.

        :param texts: The training documents.
        :param labels: The label (topic_id) for each text, row-aligned with ``texts``.
        """
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
                lr=0.1,
                wordNgrams=2,
                verbose=0,
            )
        finally:
            os.unlink(tmp_path)

    def predict(self, text: str) -> tuple[str, float]:
        """Predict the most likely label for a single text.

        :param text: The document text to classify.
        :returns: A ``(topic_id, confidence)`` tuple for the top prediction.
        :raises RuntimeError: If no model has been trained or loaded.
        """
        if self._model is None:
            raise RuntimeError("Model not trained or loaded")
        clean = text.replace("\n", " ").strip()
        labels, probs = self._model.predict(clean, k=1)
        # Strip the __label__ prefix FastText adds to returned labels
        label = labels[0].replace("__label__", "")
        return label, float(probs[0])

    def save(self, path: str) -> None:
        """Persist the trained model to disk, creating parent directories as needed.

        :param path: Destination file path for the ``.bin`` model.
        :raises RuntimeError: If there is no trained model to save.
        """
        if self._model is None:
            raise RuntimeError("No model to save")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._model.save_model(path)

    def load(self, path: str) -> None:
        """Load a previously saved FastText model from disk.

        :param path: Path to the saved ``.bin`` model file.
        """
        self._model = fasttext.load_model(path)
