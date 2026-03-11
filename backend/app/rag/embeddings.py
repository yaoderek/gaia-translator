from app.llm.client import LLMClient


async def embed_chunks(llm_client: LLMClient, chunks: list[dict]) -> list[dict]:
    """Add an 'embedding' field to each chunk dict by batching calls to the LLM client."""
    batch_size = 100
    all_embeddings: list[list[float]] = []

    for start in range(0, len(chunks), batch_size):
        batch_texts = [c["text"] for c in chunks[start : start + batch_size]]
        embeddings = await llm_client.embed(batch_texts)
        all_embeddings.extend(embeddings)

    for chunk, embedding in zip(chunks, all_embeddings):
        chunk["embedding"] = embedding

    return chunks
