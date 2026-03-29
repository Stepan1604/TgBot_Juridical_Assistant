from sqlalchemy import select
from TgBot.Bot.models import Chat


async def get_active_chat(session, user_id: int) -> Chat:
    result = await session.execute(
        select(Chat)
            .where(Chat.user_id == user_id, Chat.is_active == True)
    )
    chat = result.scalar_one_or_none()

    if chat:
        return chat

    chat = Chat(user_id=user_id)
    session.add(chat)
    await session.commit()
    return chat
