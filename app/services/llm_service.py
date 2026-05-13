import httpx
from openai import OpenAI

from app.core.config import settings


http_client = httpx.Client(verify=False)
client = OpenAI(http_client=http_client, api_key=settings.OPENAI_API_KEY, verify=False)



def generate_answer(prompt: str) -> str:
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful AI assistant for employee onboarding.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    return response.choices[0].message.content


def generate_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding