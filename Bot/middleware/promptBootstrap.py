from aiogram import BaseMiddleware
from sqlalchemy import select, func
from typing import Callable, Awaitable, Any

from TgBot.Bot.models import Prompt
from TgBot.Bot.database.init_db import AsyncSessionLocal

from TgBot.Bot.vars.prompt import AGE_POLICY_PROMPT, LEGAL_SYSTEM_PROMPT


class PromptBootstrapMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Any, dict], Awaitable[Any]],
            event: Any,
            data: dict,
    ) -> Any:
        async with AsyncSessionLocal() as session:
            # Проверяем, есть ли вообще промпты
            result = await session.execute(
                select(func.count(Prompt.id))
            )
            count = result.scalar_one()

            if count == 0:
                session.add_all(
                    [
                        Prompt(
                            name="age_policy",
                            description="Возрастная цензура и стиль общения",
                            content=AGE_POLICY_PROMPT,
                            is_active=True,
                        ),
                        Prompt(
                            name="legal_system",
                            description="Системный юридический промпт",
                            content=LEGAL_SYSTEM_PROMPT,
                            is_active=True,
                        ),
                    ]
                )
                await session.commit()

        return await handler(event, data)
