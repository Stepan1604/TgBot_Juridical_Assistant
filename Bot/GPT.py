from sqlalchemy import select
from models import Prompt
from huggingface_hub import InferenceClient
from ENV import env

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

api_key = env.LLM_TOKEN
model = "openai/gpt-oss-120b:novita"
client = InferenceClient(api_key=api_key)

model_token = SentenceTransformer('C:/Users/ASUS/Desktop/Projects/models/multilingual-e5-large')
client_token = QdrantClient(host="localhost", port=6333)


async def llm_request(
        session,
        messages: list[dict],
        age: int | None,
) -> str:
    result = await session.execute(
        select(Prompt)
            .where(Prompt.is_active == True)
            .order_by(Prompt.id)
    )
    prompts = result.scalars().all()

    system_parts: list[str] = []

    for prompt in prompts:
        system_parts.append(prompt.content)

    if age:
        system_parts.append(
            f"Отвечай так, чтобы было понятно человеку, возрастом {age} лет."
        )
        vector = model_token.encode(f"{messages[-1]["content"]}").tolist()
        result = client_token.query_points(
            collection_name="constituction",
            query=vector,
            limit=3,
            search_params=models.SearchParams(hnsw_ef=128, exact=False),
        ).points
        system_parts.append(f"Для ответа на вопрос ИСПОЛЬЗУЙ ЭТО: {", ".join([point.payload.get("target") for point in result])}")

    system_prompt = "\n\n".join(system_parts)
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        *messages,
    ]

    chat_response = client.chat.completions.create(
        model=model,
        temperature=0.9,
        top_p=0.8,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            *messages,
        ],
    )

    return chat_response.choices[0].message.content
