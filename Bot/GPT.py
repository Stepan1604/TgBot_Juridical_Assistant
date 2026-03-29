from sqlalchemy import select
from TgBot.Bot.models import Prompt
from huggingface_hub import InferenceClient
from TgBot.ENV import env

api_key = env.LLM_TOKEN
model = "openai/gpt-oss-120b"

client = InferenceClient(api_key=api_key)


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

    system_prompt = "\n\n".join(system_parts)

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
