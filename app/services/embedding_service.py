import httpx
from openai import OpenAI

from app.core.config import settings


http_client = httpx.Client(verify=False)
client = OpenAI(http_client=http_client, api_key=settings.OPENAI_API_KEY)


def create_embedding(text: str) -> list[float]:
    cleaned_text = text.replace("\n", " ").strip()

    if not cleaned_text:
        raise ValueError("Cannot create embedding for empty text")

    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=cleaned_text,
        encoding_format="float",
    )

    embedding = response.data[0].embedding

    if len(embedding) != settings.EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Embedding dimension mismatch. Expected {settings.EMBEDDING_DIMENSIONS}, got {len(embedding)}"
        )

    return embedding