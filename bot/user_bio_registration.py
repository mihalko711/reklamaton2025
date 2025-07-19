from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.state import StateFilter
from aiogram import Router, types, F

from states import UserRegistrationStates, BotStates

import sqlite3

user_route = Router()

DBInsert = '''
    INSERT OR REPLACE INTO users (
        id, name, age, gender, zodiac_sign, height, weight, 
        has_children, attitude_alcohol, attitude_tobacco
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
'''

Males = ["Парень", "Девушка"]
Zodiacs = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей",
           "Рыбы"]
YesNo = ["Да", "Нет"]
Rship = ["Положительно", "Нейтрально", "Отрицательно"]


@user_route.message(UserRegistrationStates.name_state)
async def set_name(message: types.Message, state: FSMContext, db: sqlite3.Connection):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(UserRegistrationStates.age_state)


@user_route.message(UserRegistrationStates.age_state)
async def set_age(message: types.Message, state: FSMContext, db: sqlite3.Connection):
    age_string = message.text

    try:
        age = int(age_string.strip())
    except ValueError:
        return

    await state.update_data(age=age)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Парень")],
            [KeyboardButton(text="Девушка")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await state.set_state(UserRegistrationStates.sex_state)
    await message.answer("Парень/Девушка", reply_markup=keyboard)


@user_route.message(UserRegistrationStates.sex_state)
async def set_sex(message: types.Message, state: FSMContext, db: sqlite3.Connection):
    sex = message.text

    if not (sex in Males):
        return

    await state.update_data(sex="f" if sex == "Девушка" else "m")

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Овен"), KeyboardButton(text="Телец"), KeyboardButton(text="Близнецы")],
            [KeyboardButton(text="Рак"), KeyboardButton(text="Скорпион"), KeyboardButton(text="Рыбы")],
            [KeyboardButton(text="Лев"), KeyboardButton(text="Дева"), KeyboardButton(text="Весы")],
            [KeyboardButton(text="Стрелец"), KeyboardButton(text="Козерог"), KeyboardButton(text="Водолей")]
        ]
    )

    await state.set_state(UserRegistrationStates.zodiac_sign_state)
    await message.answer("Твой знак зодиака", reply_markup=keyboard)


@user_route.message(UserRegistrationStates.zodiac_sign_state)
async def set_zz(message: types.Message, state: FSMContext, db: sqlite3.Connection):
    zz = message.text

    if not (zz in Zodiacs):
        return

    await state.update_data(zodiac=zz)

    await state.set_state(UserRegistrationStates.height_state)
    await message.answer("Напиши свой рост", reply_markup=types.ReplyKeyboardRemove())


@user_route.message(UserRegistrationStates.height_state)
async def set_height(message: types.Message, state: FSMContext, db: sqlite3.Connection):
    height_string = message.text

    try:
        height = int(height_string.strip())
    except ValueError:
        return

    await state.update_data(height=height)

    await state.set_state(UserRegistrationStates.weight_state)
    await message.answer("Напиши свой вес")


@user_route.message(UserRegistrationStates.weight_state)
async def set_weight(message: types.Message, state: FSMContext, db: sqlite3.Connection):
    weight_string = message.text

    try:
        weight = int(weight_string.strip())
    except ValueError:
        return

    await state.update_data(weight=weight)

    await state.set_state(UserRegistrationStates.children_state)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да")],
            [KeyboardButton(text="Нет")],
        ]
    )
    await message.answer("Есть ли у тебя дети", reply_markup=keyboard)


@user_route.message(UserRegistrationStates.children_state)
async def set_childer(message: types.Message, state: FSMContext, db: sqlite3.Connection):
    kids = message.text

    if not (kids in YesNo):
        return

    await state.update_data(kids=kids)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Положительно")],
            [KeyboardButton(text="Нейтрально")],
            [KeyboardButton(text="Отрицательно")],
        ]
    )
    await state.set_state(UserRegistrationStates.alcohol_state)
    await message.answer("Отношение к алкоголю", reply_markup=keyboard)


@user_route.message(UserRegistrationStates.alcohol_state)
async def set_alco(message: types.Message, state: FSMContext, db: sqlite3.Connection):
    rship = message.text

    if not (rship in Rship):
        return

    if rship == Rship[0]:
        value = 1
    elif rship == Rship[0]:
        value = 0
    else:
        value = -1
    await state.update_data(alco=value)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Положительно")],
            [KeyboardButton(text="Нейтрально")],
            [KeyboardButton(text="Отрицательно")],
        ]
    )

    await state.set_state(UserRegistrationStates.tobacco_state)
    await message.answer("Отношение к курению", reply_markup=keyboard)


@user_route.message(UserRegistrationStates.tobacco_state)
async def set_tabacco(message: types.Message, state: FSMContext, db: sqlite3.Connection):
    rship = message.text

    if not (rship in Rship):
        return

    if rship == Rship[0]:
        value = 1
    elif rship == Rship[0]:
        value = 0
    else:
        value = -1
    await state.update_data(tobacco=value)

    data = await state.get_data()
    cursor = db.cursor()
    cursor.execute(DBInsert, (
        str(message.from_user.id),
        data.get("name"),
        data.get("age"),
        data.get("sex"),
        data.get("zodiac"),
        data.get("height"),
        data.get("weight"),
        data.get("kids"),
        data.get("alco"),
        data.get("tobacco")
    ))
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Оценить анкету")],
            [KeyboardButton(text="Оценить фотографию")],
            [KeyboardButton(text="Общий диалог")]
        ],
        resize_keyboard=True
    )
    await message.answer("✅ Регистрация завершена. Спасибо!", reply_markup=keyboard)
    await state.set_state(BotStates.choosing_menu_state)
    await message.answer("Привет! Я бот для оценки анкет, фотографий и ответов. Выберите, что вы хотите оценить:")
