from bson import ObjectId
from bson.errors import InvalidId
from pymongo.asynchronous.database import AsyncDatabase

from app.config import settings
from app.schemas.search import SearchQuery


class DocumentRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._collection = db["documents"]

    def _build_filter(
        self, query: SearchQuery, proxy_doc_ids: list[str] | None = None
    ) -> dict:
        filters: list[dict] = []

        for keyword in query.keywords:
            if not keyword:
                continue
            regex = {"$regex": keyword, "$options": "i"}
            filters.append({"$or": [{"headline": regex}, {"plain_text": regex}]})

        if query.date_from or query.date_to:
            date_filter: dict = {}
            if query.date_from:
                date_filter["$gte"] = query.date_from
            if query.date_to:
                date_filter["$lte"] = query.date_to
            filters.append({"published_time": date_filter})

        if query.languages:
            filters.append({"language": {"$in": query.languages}})

        if query.platforms:
            filters.append({"platform": {"$in": query.platforms}})

        if query.topics:
            topic_filter: dict = {"acteu_topic.label": {"$in": query.topics}}
            if query.confidence_threshold is not None:
                topic_filter["acteu_topic.confidence"] = {"$gte": query.confidence_threshold}
            filters.append(topic_filter)

        # First filter: document-level subtopics
        # Second filter: directly add document proxies to the results, as they
        #                contain project-level subtopics.
        if query.subtopics:
            elem: dict = {"topic_id": {"$in": query.subtopics}}
            if query.confidence_threshold is not None:
                elem["confidence"] = {"$gte": query.confidence_threshold}
            subtopic_clauses: list[dict] = [{"subtopics": {"$elemMatch": elem}}]
            if proxy_doc_ids:
                object_ids = self._coerce_object_ids(proxy_doc_ids)
                if object_ids:
                    subtopic_clauses.append({"_id": {"$in": object_ids}})
            filters.append({"$or": subtopic_clauses})

        if not filters:
            return {}
        return {"$and": filters}

    def _coerce_object_ids(self, doc_ids: list[str]) -> list[ObjectId]:
        object_ids: list[ObjectId] = []
        for doc_id in doc_ids:
            try:
                object_ids.append(ObjectId(doc_id))
            except (InvalidId, TypeError):
                continue
        return object_ids

    async def find(
        self, query: SearchQuery, proxy_doc_ids: list[str] | None = None
    ) -> list[dict]:
        query_filter = self._build_filter(query, proxy_doc_ids)
        cursor = self._collection.find(query_filter).sort("published_time", -1).limit(
            settings.DOCUMENT_SEARCH_LIMIT
        )
        return [doc async for doc in cursor]

    async def find_by_ids(self, doc_ids: list[str]) -> list[dict]:
        object_ids = self._coerce_object_ids(doc_ids)
        if not object_ids:
            return []
        cursor = self._collection.find({"_id": {"$in": object_ids}})
        return [doc async for doc in cursor]

    async def distinct_languages(self) -> list[str]:
        """Every language value present in at least one document, sorted."""
        languages = await self._collection.distinct("language")
        return sorted(lang for lang in languages if lang)

    async def count(
        self, query: SearchQuery, proxy_doc_ids: list[str] | None = None
    ) -> int:
        query_filter = self._build_filter(query, proxy_doc_ids)
        return await self._collection.count_documents(query_filter)

    def _build_vis_match(
        self,
        topic: str,
        date_from,
        date_to,
        languages: list[str],
        platforms: list[str],
        proxy_doc_ids: list[str] | None = None,
    ) -> dict:
        """Match stage for a single visualisation topic.

        A document matches the topic when it carries it as a core topic
        (`acteu_topic.label` == slug), as a db subtopic (`subtopics.topic_id` == the
        subtopic UUID), or when its id is among the project proxy doc_ids resolved for
        that topic. The date/language/platform constraints apply uniformly to every
        source. Core topics arrive as their slug; subtopics as their topic_id.

        Essentially:
        {"$or": [{"acteu_topic.label": topic}, {"subtopics.topic_id": topic}, {"_id": {"$in": object_ids}}]}
        """
        topic_clauses: list[dict] = [
            {"acteu_topic.label": topic},
            {"subtopics.topic_id": topic},
        ]
        if proxy_doc_ids:
            object_ids = self._coerce_object_ids(proxy_doc_ids)
            if object_ids:
                topic_clauses.append({"_id": {"$in": object_ids}})

        match: dict = {"$or": topic_clauses}

        if date_from or date_to:
            date_filter: dict = {}
            if date_from:
                date_filter["$gte"] = date_from
            if date_to:
                date_filter["$lte"] = date_to
            match["published_time"] = date_filter

        if languages:
            match["language"] = {"$in": languages}

        if platforms:
            match["platform"] = {"$in": platforms}

        return match

    async def topic_presence_over_time(
        self,
        topic: str,
        date_from,
        date_to,
        languages: list[str],
        platforms: list[str],
        proxy_doc_ids: list[str] | None = None,
    ) -> list[dict]:
        """Daily document counts for a topic. Returns [{"date": "YYYY-MM-DD", "count": int}]
        sorted ascending by date."""
        match = self._build_vis_match(
            topic, date_from, date_to, languages, platforms, proxy_doc_ids
        )
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$published_time"}
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        cursor = await self._collection.aggregate(pipeline)
        return [{"date": doc["_id"], "count": doc["count"]} async for doc in cursor]

    async def topic_presence_by_language(
        self,
        topic: str,
        date_from,
        date_to,
        languages: list[str],
        platforms: list[str],
        proxy_doc_ids: list[str] | None = None,
    ) -> list[dict]:
        """Document counts per language for a topic. Returns
        [{"language": str, "count": int}] sorted by count descending."""
        match = self._build_vis_match(
            topic, date_from, date_to, languages, platforms, proxy_doc_ids
        )
        pipeline = [
            {"$match": match},
            {"$group": {"_id": "$language", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}},
        ]
        cursor = await self._collection.aggregate(pipeline)
        return [
            {"language": doc["_id"], "count": doc["count"]} async for doc in cursor
        ]

    async def topic_presence_by_platform(
        self,
        topic: str,
        date_from,
        date_to,
        languages: list[str],
        platforms: list[str],
        proxy_doc_ids: list[str] | None = None,
    ) -> list[dict]:
        """Document counts per platform for a topic. Returns
        [{"platform": str, "count": int}] sorted by count descending."""
        match = self._build_vis_match(
            topic, date_from, date_to, languages, platforms, proxy_doc_ids
        )
        pipeline = [
            {"$match": match},
            {"$group": {"_id": "$platform", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}},
        ]
        cursor = await self._collection.aggregate(pipeline)
        return [
            {"platform": doc["_id"], "count": doc["count"]} async for doc in cursor
        ]

    async def entities_for_topic(
        self,
        topic: str,
        date_from,
        date_to,
        languages: list[str],
        platforms: list[str],
        proxy_doc_ids: list[str] | None = None,
    ) -> list[list[str]]:
        """Per-document entity name lists for a topic. 
        Returns one inner list per matching document, e.g.
        [["Spain", "Lampedusa"], ["EU"], ...]. Documents with no entities are omitted."""
        match = self._build_vis_match(
            topic, date_from, date_to, languages, platforms, proxy_doc_ids
        )
        pipeline = [
            {"$match": match},
            {"$project": {"_id": 0, "entities": "$named_entities.text"}},
        ]
        cursor = await self._collection.aggregate(pipeline)
        result: list[list[str]] = []
        async for doc in cursor:
            entities = doc.get("entities") or []
            if entities:
                result.append(entities)
        return result

    @staticmethod
    def _relevance_stage(
        topic: str, proxy_confidence: dict[str, float] | None = None
    ) -> dict:
        '''
        Builds a MongoDB aggregation stage to compute a document-level
        relevance score for a given topic. Adds a _relevance field.

        Precedence: ActEU core topic (acteu_topic.label == slug) -> acteu_topic.confidence;
        otherwise the matching subtopics[].confidence (matched by subtopics.topic_id);
        otherwise, when the document matched via a project proxy for this topic, the proxy
        confidence (passed in `proxy_confidence` as a {doc_id: confidence} map); else None.
        '''
        doc_relevance = {
            "$cond": [
                {"$eq": ["$acteu_topic.label", topic]},
                "$acteu_topic.confidence",
                {
                    "$let": {
                        "vars": {
                            "matched": {
                                "$filter": {
                                    "input": {"$ifNull": ["$subtopics", []]},
                                    "as": "s",
                                    "cond": {"$eq": ["$$s.topic_id", topic]},
                                }
                            }
                        },
                        "in": {
                            "$cond": [
                                {"$gt": [{"$size": "$$matched"}, 0]},
                                {"$max": "$$matched.confidence"},
                                None,
                            ]
                        },
                    }
                },
            ]
        }

        if not proxy_confidence:
            relevance: dict = doc_relevance
        else:
            # Fall back to the proxy confidence: look the document up in the
            # {doc_id: confidence} map by its stringified _id, using two parallel
            # literal arrays (index in ids -> confidence at the same index).
            #
            # MongoDB aggregation expressions do not support direct key-based lookup, 
            # hence the separation into arrays to simulate the dictionary.
            ids = list(proxy_confidence.keys())
            confidences = [proxy_confidence[doc_id] for doc_id in ids]
            proxy_lookup = {
                "$let": {
                    "vars": {
                        "idx": {
                            "$indexOfArray": [
                                {"$literal": ids},
                                {"$toString": "$_id"}, # Current doc id, converted to str
                            ]
                        }
                    },
                    "in": {
                        "$cond": [
                            {"$gte": ["$$idx", 0]},
                            # Return confidence value at index idx in the confidences array
                            {"$arrayElemAt": [{"$literal": confidences}, "$$idx"]},
                            None,
                        ]
                    },
                }
            }
            relevance = {"$ifNull": [doc_relevance, proxy_lookup]}

        return {"$addFields": {"_relevance": relevance}}

    async def mean_topic_confidence(
        self,
        topic: str,
        date_from,
        date_to,
        languages: list[str],
        platforms: list[str],
        proxy_confidence: dict[str, float] | None = None,
    ) -> float | None:
        """Mean classifier confidence for a topic across all matching documents.

        Averages the per-document confidence for the matched topic (core, db-subtopic
        or project-proxy confidence). Returns `None` when no document has a confidence
        for the topic."""
        match = self._build_vis_match(
            topic, date_from, date_to, languages, platforms,
            list(proxy_confidence) if proxy_confidence else None,
        )
        pipeline = [
            {"$match": match}, # Filter, selects documents matching constraints
            self._relevance_stage(topic, proxy_confidence), # Compute topic relevance for each selected document
            {"$match": {"_relevance": {"$ne": None}}}, # Remove docs with None relevance
            {"$group": {"_id": None, "mean": {"$avg": "$_relevance"}}}, # Compute average relevance
        ]
        cursor = await self._collection.aggregate(pipeline)
        async for doc in cursor:
            return doc.get("mean")
        return None

    async def count_topic_documents(
        self,
        topic: str,
        date_from,
        date_to,
        languages: list[str],
        platforms: list[str],
        proxy_doc_ids: list[str] | None = None,
    ) -> int:
        """Number of documents matching a topic under the visualisation constraints.

        Counts every document that carries the topic (core, db-subtopic or project
        proxy), regardless of confidence. Returns 0 when nothing matches."""
        match = self._build_vis_match(
            topic, date_from, date_to, languages, platforms, proxy_doc_ids
        )
        return await self._collection.count_documents(match)

    async def relevant_documents(
        self,
        topic: str,
        date_from,
        date_to,
        languages: list[str],
        platforms: list[str],
        proxy_confidence: dict[str, float] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Top documents for a topic ranked by their confidence for that topic, taking
        up to `limit` documents *per platform* so every platform present among the
        matches is represented (callers can then interleave/trim across platforms).

        Relevance is the document's confidence for the matched topic: the core
        `acteu_topic.confidence` when matched as a core topic, the matching
        `subtopics[].confidence` when matched as a db subtopic, or the project proxy
        confidence (from `proxy_confidence`) when matched via a project proxy.
        Documents with no confidence rank below any confident match.

        Returns dicts with keys: doc_id, platform, language, published_time,
        plain_text, relevance (float | None). Documents are relevance-ordered within
        each platform; ordering across platforms is unspecified."""
        match = self._build_vis_match(
            topic, date_from, date_to, languages, platforms,
            list(proxy_confidence) if proxy_confidence else None,
        )
        pipeline = [
            {"$match": match},
            self._relevance_stage(topic, proxy_confidence),
            # Keep only the top `limit` documents of each platform, ranked by
            # relevance (confident matches first; no-confidence docs rank last).
            # $topN is memory-bounded to `limit` docs per platform, to avoid memory overflows.
            {
                "$group": {
                    "_id": "$platform",
                    "docs": {
                        "$topN": {
                            "n": limit,
                            "sortBy": {"_relevance": -1, "_id": 1},
                            "output": "$$ROOT",
                        }
                    },
                }
            },
            {"$unwind": "$docs"},
            {"$replaceRoot": {"newRoot": "$docs"}},
            {
                "$project": {
                    "_id": 1,
                    "platform": 1,
                    "language": 1,
                    "published_time": 1,
                    "plain_text": 1,
                    "relevance": "$_relevance",
                }
            },
        ]
        cursor = await self._collection.aggregate(pipeline)
        return [
            {
                "doc_id": str(doc["_id"]),
                "platform": doc.get("platform") or "",
                "language": doc.get("language") or "",
                "published_time": doc.get("published_time"),
                "plain_text": doc.get("plain_text") or "",
                "relevance": doc.get("relevance"),
            }
            async for doc in cursor
        ]

    async def get_excerpt(self, doc_id: str) -> str:
        try:
            object_id = ObjectId(doc_id)
        except (InvalidId, TypeError):
            return ""

        doc = await self._collection.find_one({"_id": object_id}, {"plain_text": 1})
        plain_text = (doc or {}).get("plain_text", "")
        plain_text = plain_text.strip()
        if len(plain_text) > 250:
            return f"{plain_text[:250].rstrip()}..."
        return plain_text
