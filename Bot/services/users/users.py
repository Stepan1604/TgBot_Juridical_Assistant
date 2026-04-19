from sqlalchemy import select
from models import User


async def get_or_create_user(
        session,
        telegram_id: int,
        full_name: str | None,
        username: str | None,
):
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if user:
        return user

    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        username=username,
    )
    session.add(user)
    await session.commit()
    return user
