from app.services.pagerank import top_entities


class TestTopEntities:
    def test_empty_input_returns_empty(self):
        assert top_entities([]) == []

    def test_docs_without_entities_return_empty(self):
        assert top_entities([[], []]) == []

    def test_single_entity_single_doc(self):
        result = top_entities([["Spain"]])
        assert [name for name, _ in result] == ["Spain"]

    def test_central_hub_ranks_first(self):
        """A entity co-occurs with everyone; it should rank top by centrality."""
        docs = [
            ["A", "B"],
            ["A", "C"],
            ["A", "D"],
            ["B", "C"],
        ]
        result = top_entities(docs)
        assert result[0][0] == "A"

    def test_limit_is_respected(self):
        docs = [["A", "B", "C", "D", "E", "F", "G"]]
        result = top_entities(docs, limit=5)
        assert len(result) == 5

    def test_fewer_than_limit_returns_all(self):
        result = top_entities([["A", "B"]], limit=5)
        assert len(result) == 2

    def test_scores_sorted_descending(self):
        docs = [["A", "B"], ["A", "C"], ["A", "D"], ["B", "C"]]
        scores = [score for _, score in top_entities(docs)]
        assert scores == sorted(scores, reverse=True)

    def test_duplicate_entity_in_doc_counted_once(self):
        """Repeating an entity within a document must not create a self-loop or inflate it."""
        result = top_entities([["A", "A", "B"]])
        names = {name for name, _ in result}
        assert names == {"A", "B"}

    def test_weight_reflects_cooccurrence_count(self):
        """A-B co-occur in 3 docs, C is peripheral; A and B outrank C."""
        docs = [
            ["A", "B"],
            ["A", "B"],
            ["A", "B"],
            ["C", "A"],
        ]
        result = top_entities(docs)
        ranked = [name for name, _ in result]
        assert ranked.index("A") < ranked.index("C")
        assert ranked.index("B") < ranked.index("C")

    def test_no_edges_still_ranks_nodes(self):
        """Entities that never co-occur (each alone in its doc) still get returned."""
        result = top_entities([["A"], ["B"], ["C"]], limit=2)
        assert len(result) == 2
        assert {name for name, _ in result} <= {"A", "B", "C"}

    def test_deterministic_tie_break_by_name(self):
        """Equal-score entities are ordered alphabetically for stable output."""
        result = top_entities([["B", "A"]])
        # symmetric graph -> equal scores -> alphabetical
        assert [name for name, _ in result] == ["A", "B"]
