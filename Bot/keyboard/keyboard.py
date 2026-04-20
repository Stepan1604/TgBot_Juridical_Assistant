from aiogram import types

def get_kb():
    kb = [
        [
            types.KeyboardButton(text="Тех. Поддержка",),
            types.KeyboardButton(text="Оценить бота")
        ],
        [
            types.KeyboardButton(text="Отправить документ")
        ]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb,
                                         resize_keyboard=True,
                                         input_field_placeholder="Введите ваш запрос",
                                         )
    return keyboard