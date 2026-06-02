"""Entity PageRank over a co-occurrence graph.

Pure computation (no I/O) so it is trivially unit-testable. Given the per-document
entity lists for a topic, build an undirected weighted graph where:
  - nodes are distinct entity names,
  - an edge connects two entities that co-occur in the same document,
  - edge weight is the number of documents in which both entities appear together.

PageRank (igraph, damping 0.85) then ranks entities by centrality, which surfaces
entities tied to other important entities rather than merely frequent ones.
"""

from itertools import combinations

import igraph as ig

DAMPING = 0.85


def top_entities(
    doc_entity_lists: list[list[str]],
    limit: int = 5,
) -> list[tuple[str, float]]:
    """Rank entities by weighted PageRank over their co-occurrence graph.

    Returns up to `limit` (entity, score) tuples sorted by score descending.
    Handles degenerate inputs gracefully:
      - no entities at all -> []
      - entities that never co-occur (no edges) -> ranked by isolated-node PageRank
        (uniform), still returning the most frequent up to `limit`.
    """
    # Accumulate undirected edge weights from per-document co-occurrence.
    edge_weights: dict[tuple[str, str], int] = {}
    node_index: dict[str, int] = {}

    def node_id(name: str) -> int:
        idx = node_index.get(name)
        if idx is None:
            idx = len(node_index)
            node_index[name] = idx
        return idx

    for entities in doc_entity_lists:
        unique = sorted(set(entities))  # deduplicated within a document
        for entity in unique:
            node_id(entity)  # ensure isolated entities are still nodes
        for a, b in combinations(unique, 2):
            key = (a, b)  # `unique` is sorted, so the pair is already ordered
            edge_weights[key] = edge_weights.get(key, 0) + 1

    if not node_index:
        return []

    graph = ig.Graph()
    graph.add_vertices(len(node_index))

    edges = [(node_index[a], node_index[b]) for (a, b) in edge_weights]
    weights = list(edge_weights.values())
    if edges:
        graph.add_edges(edges)

    scores = graph.pagerank(weights=weights if edges else None, damping=DAMPING)

    index_to_name = {idx: name for name, idx in node_index.items()}
    ranked = sorted(
        ((index_to_name[i], score) for i, score in enumerate(scores)),
        key=lambda pair: (-pair[1], pair[0]),
    )
    return ranked[:limit]
