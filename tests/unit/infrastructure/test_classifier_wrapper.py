"""NLP-heavy tests for the FastText adapter.

Marked `slow`: they require `fasttext` (requirements-nlp.txt) and actually train a
model, so they are excluded from CI (`-m "not slow"`) and meant to run locally.
`importorskip` keeps CI collection green when the NLP deps are not installed.
"""
import pytest

from tests.conftest import fasttext_unavailable

if fasttext_unavailable():
    pytest.skip("FastText (requirements-nlp.txt) not installed", allow_module_level=True)

from app.infrastructure.classifier_wrapper import ClassifierWrapper

pytestmark = pytest.mark.slow


# Two strongly separated classes with distinct vocabulary, repeated enough times
# for FastText to learn a clear decision boundary.
SPORTS = [
    "the football team scored a goal in the match",
    "the player kicked the ball into the net",
    "our team won the championship game last night",
    "the striker scored twice during the second half",
    "fans cheered as the goalkeeper saved the penalty",
    "the league match ended in a draw between the teams",
]
COOKING = [
    "preheat the oven and bake the cake with flour and sugar",
    "mix the eggs butter and flour to make the dough",
    "add salt and pepper to season the soup recipe",
    "whisk the cream and sugar until the batter is smooth",
    "roast the vegetables in the oven for thirty minutes",
    "knead the dough then let it rise before baking bread",
]


def _training_data():
    texts = SPORTS * 5 + COOKING * 5
    labels = ["sports"] * len(SPORTS) * 5 + ["cooking"] * len(COOKING) * 5
    return texts, labels


class TestPredictGuards:
    def test_predict_without_model_raises(self):
        with pytest.raises(RuntimeError):
            ClassifierWrapper().predict("anything")

    def test_save_without_model_raises(self, tmp_path):
        with pytest.raises(RuntimeError):
            ClassifierWrapper().save(str(tmp_path / "model.bin"))


class TestTrainPredict:
    def test_predict_returns_label_and_confidence(self):
        wrapper = ClassifierWrapper()
        wrapper.train(*_training_data())

        label, confidence = wrapper.predict("the team scored a goal in the football match")

        assert label in {"sports", "cooking"}
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_learns_separable_classes(self):
        wrapper = ClassifierWrapper()
        wrapper.train(*_training_data())

        sports_label, _ = wrapper.predict("the goalkeeper saved the penalty and the team won")
        cooking_label, _ = wrapper.predict("bake the cake in the oven with flour and sugar")

        assert sports_label == "sports"
        assert cooking_label == "cooking"

    def test_label_prefix_is_stripped(self):
        wrapper = ClassifierWrapper()
        wrapper.train(*_training_data())

        label, _ = wrapper.predict("the football match ended in a draw")
        assert not label.startswith("__label__")


class TestSaveLoad:
    def test_round_trip_preserves_predictions(self, tmp_path):
        path = str(tmp_path / "clf.bin")
        wrapper = ClassifierWrapper()
        wrapper.train(*_training_data())
        wrapper.save(path)

        text = "the player kicked the ball into the net"
        expected = wrapper.predict(text)

        reloaded = ClassifierWrapper()
        reloaded.load(path)
        got = reloaded.predict(text)

        assert got[0] == expected[0]
        assert got[1] == pytest.approx(expected[1])

    def test_save_creates_file(self, tmp_path):
        # save() must create the target directory if it does not exist.
        path = str(tmp_path / "nested" / "clf.bin")
        wrapper = ClassifierWrapper()
        wrapper.train(*_training_data())

        wrapper.save(path)

        import os
        assert os.path.exists(path)
