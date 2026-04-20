from aiogram import types, Router
from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy import select
from aiogram.types import FSInputFile
from sqlalchemy.util import methods_equivalent

from database.init_db import AsyncSessionLocal
from keyboard.keyboard import get_kb
from models import User, Message, Rating
from services.chats.chat import get_active_chat
from services.users.users import get_or_create_user
from vars.dialog import *
from GPT import llm_request

from markitdown import MarkItDown

rt = Router()

data = {}


# - - - Состояния - - -
class BotStates(StatesGroup):
    waiting_age = State()
    waiting_grade = State()
    waiting_grade_text = State()
    waiting_request = State()
    waiting_document = State()


# - - - Хендлеры - - -
@rt.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    print(f"{message.from_user.id}: {message.text}")

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
        )

    await message.answer(START_TEXT(message.from_user.full_name))
    await state.set_state(BotStates.waiting_age)


@rt.message(BotStates.waiting_age)
async def cmd_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0:
            raise ValueError
    except ValueError:
        await message.answer(AGE_ERROR)
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one()
        user.age = age
        await session.commit()

    await message.answer(THANKS_TEXT, reply_markup=get_kb())
    await message.answer(HELP_TEXT)
    await state.set_state(BotStates.waiting_request)


@rt.message(F.text == "Тех. Поддержка", BotStates.waiting_request)
async def cmd_teh(message: types.Message):
    print(f"{message.from_user.id}: {message.html_text}")
    await message.answer(SYNC_TEXT)


@rt.message(F.text == "Оценить бота", BotStates.waiting_request)
async def cmd_grade(message, state: types.Message):
    builder = ReplyKeyboardBuilder()
    for button in range(1, 11):
        builder.add(types.KeyboardButton(text=str(button)))
    builder.adjust(5)
    print(f"{message.from_user.id} {message.from_user.full_name}: {message.html_text}")
    await message.answer(
        GRAPE_REQUEST1_TEXT,
        reply_markup=builder.as_markup(resize_keyboard=True, input_field_placeholder=GRAPE_REQUEST2_TEXT)
    )
    await state.set_state(BotStates.waiting_grade)


@rt.message(BotStates.waiting_grade)
async def cmd_grade(message: types.Message, state: FSMContext):
    score = int(message.text)

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one()

        rating = Rating(
            user_id=user.id,
            score=score,
        )
        session.add(rating)
        await session.commit()

    await message.answer(GRAPE_THANKS_TEXT, reply_markup=get_kb())
    await message.answer(GRADE_TEXT_REQUEST)
    await state.set_state(BotStates.waiting_grade_text)


@rt.message(BotStates.waiting_grade_text)
async def cmd_grade_text(message: types.Message, state: FSMContext):
    print(f"{message.from_user.id}: {message.text}")

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one()

        rating = (
            await session.execute(
                select(Rating)
                    .where(Rating.user_id == user.id)
                    .order_by(Rating.created_at.desc())
                    .limit(1)
            )
        ).scalar_one_or_none()

        if rating:
            rating.comment = message.text
            await session.commit()

    await message.answer("Спасибо за отзыв 🙌")
    await state.set_state(BotStates.waiting_request)


@rt.message(F.text == "Все оценки", BotStates.waiting_request)
async def all_grades(message: types.Message):

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                User.telegram_id,
                User.username,
                Rating.score,
                Rating.comment,
                Rating.created_at,
            )
                .join(Rating, Rating.user_id == User.id)
                .order_by(Rating.created_at.desc())
        )

        rows = result.all()

    if not rows:
        await message.answer("Оценок пока нет")
        return

    text = []
    for tg_id, username, score, comment, created_at in rows:
        text.append(
            f"👤 {str(tg_id) + ' - ' + username}\n"
            f"⭐ Оценка: {score}\n"
            f"💬 Комментарий: {comment or '—'}\n"
            f"🕒 {created_at:%d.%m.%Y %H:%M}"
        )

    await message.answer("\n\n".join(text))

@rt.message(F.text == "Отправить документ", BotStates.waiting_request)
async def document(message: types.Message, state: FSMContext):
    await message.answer("Отправьте свой документ")
    await state.set_state(BotStates.waiting_document)

@rt.message(F.document, BotStates.waiting_document)
async def document(message: types.Message, state: FSMContext):
    bot = message.bot

    name = message.from_user.id
    file_path = rf"C:\Users\ASUS\Pycharm\TgBot\Documents\{name}"

    user_document = message.document

    await bot.download(file=user_document, destination=file_path)

    await message.answer("Файл успешно принят")

    markitdown = MarkItDown()
    result = markitdown.convert(rf"C:\Users\ASUS\Pycharm\TgBot\Documents\{name}")

    if message.html_text == "":
        async with AsyncSessionLocal() as session:
            user = (
                await session.execute(
                    select(User).where(User.telegram_id == message.from_user.id)
                )
            ).scalar_one()

            content = f"Проанализируй текст, кратко перескажи и выяви все плюсы и недостатки данного документа:\n{result.text_content}"

            messages = [
                {"role": "user", "content": content}
            ]

            response = await llm_request(session, messages, user.age)
    else:
        async with AsyncSessionLocal() as session:
            user = (
                await session.execute(
                    select(User).where(User.telegram_id == message.from_user.id)
                )
            ).scalar_one()

            content = f"{message.html_text}:\n{result.text_content}"

            messages = [
                {"role": "user", "content": content}
            ]

            response = await llm_request(session, messages, user.age)

    await message.answer(response, parse_mode="HTML")
    await state.set_state(BotStates.waiting_request)


@rt.message(F.text, BotStates.waiting_request)
async def response_to_request(message: types.Message):
    print(f"{message.from_user.id}: {message.text}")

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one()

        chat = await get_active_chat(session, user.id)

        user_msg = Message(
            chat_id=chat.id,
            role="user",
            content=message.text,
        )
        session.add(user_msg)
        await session.commit()

        history = (
            await session.execute(
                select(Message)
                    .where(Message.chat_id == chat.id)
                    .order_by(Message.created_at)
            )
        ).scalars().all()

        messages = [
            {"role": m.role, "content": m.content}
            for m in history
        ]

        response = await llm_request(session, messages, user.age)

    async with AsyncSessionLocal() as session:
        assistant_msg = Message(
            chat_id=chat.id,
            role="assistant",
            content=response,
        )
        session.add(assistant_msg)
        await session.commit()

    await message.answer(response, parse_mode="HTML")
