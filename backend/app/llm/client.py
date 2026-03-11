from openai import AsyncOpenAI

from app.core.config import Settings


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model
        self._embedding_model = settings.openai_embedding_model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Batch-embed texts, chunking into groups of 2048 per API call."""
        all_embeddings: list[list[float]] = []
        batch_size = 2048
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = await self._client.embeddings.create(
                model=self._embedding_model,
                input=batch,
            )
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings

    async def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    async def chat_stream(self, messages: list[dict], temperature: float = 0.3):
        """Yield streamed token strings."""
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
