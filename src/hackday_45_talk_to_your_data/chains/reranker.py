"""Cross-encoder reranker — trims multi-collection chunks to top-N."""

import functools

from sentence_transformers import CrossEncoder  # type: ignore[import-untyped]

from hackday_45_talk_to_your_data.api.models import SourceChunk

_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_TOP_N = 8


@functools.cache
def _encoder() -> CrossEncoder:
    return CrossEncoder(_MODEL)


def rerank(query: str, chunks: list[SourceChunk], top_n: int = _TOP_N) -> list[SourceChunk]:
    if len(chunks) <= top_n:
        return chunks
    pairs = [(query, chunk.content) for chunk in chunks]
    scores: list[float] = _encoder().predict(pairs).tolist()  # pyright: ignore[reportUnknownMemberType]
    ranked = sorted(zip(scores, chunks, strict=True), key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in ranked[:top_n]]
