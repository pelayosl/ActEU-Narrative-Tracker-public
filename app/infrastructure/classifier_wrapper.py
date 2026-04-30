class ClassifierWrapper:
    """Adapter over FastText for training and prediction."""

    def train(self, texts: list[str], labels: list[str]) -> None:
        raise NotImplementedError

    def predict(self, text: str) -> tuple[str, float]:
        raise NotImplementedError

    def save(self, path: str) -> None:
        raise NotImplementedError

    def load(self, path: str) -> None:
        raise NotImplementedError
