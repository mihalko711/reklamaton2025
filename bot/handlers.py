import io
import sqlite3

import requests
import base64
import os

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.state import StateFilter
from aiogram import Router, types, F

from states import BotStates, UserRegistrationStates
from prompts import questionnaire_systemp_prompt, photo_systemp_prompt, conversation_systemp_prompt

LM_API_URL = os.getenv("LM_API_URL")
if not LM_API_URL:
    raise ValueError("LM_API_URL не найден в .env")

router = Router()


@router.message(StateFilter(None))
async def start_command(message: types.Message, state: FSMContext, db: sqlite3.Connection):
    user_id = message.from_user.id
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()

    if result:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Оценить анкету")],
                [KeyboardButton(text="Оценить фотографию")],
                [KeyboardButton(text="Диалог")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await state.set_state(BotStates.choosing_menu_state)
        await state.update_data({
            "name": result[1],
            "age": result[2],
            "sex": result[3],
            "zodiac": result[4],
            "height": result[5],
            "weight": result[6],
            "kids": result[7],
            "alco": result[8],
            "tobacco": result[9]
        })
        await message.answer(
            f"Привет {result[1]}! Я бот для оценки анкет, фотографий и ответов. Выберите, что вы хотите оценить:",
            reply_markup=keyboard)
    else:
        await message.answer("Для начала просим тебя немного рассказать о себе. Напиши своё имя!")
        await state.set_state(UserRegistrationStates.name_state)


@router.message(F.text == "Оценить анкету", StateFilter(BotStates.choosing_menu_state))
async def rate_profile(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.questionnaire_marking_state)
    await message.answer("Пожалуйста, отправьте анкету в виде текста.")


@router.message(F.text == "Оценить фотографию", StateFilter(BotStates.choosing_menu_state))
async def rate_photo(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.photo_marking_state)
    await message.answer("Пожалуйста, отправьте фотографию (можно с подписью)")


@router.message(F.text == "Диалог", StateFilter(BotStates.choosing_menu_state))
async def start_conversation(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.conversation_state)
    await state.update_data(history=[])
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Завершить разговор")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Вы вошли в интерактивный режим диалога, можете задавать любые вопросы по дейтингу и я постараюсь Вам помочь!",
        reply_markup=keyboard)


@router.message(F.text == "Завершить разговор")
async def stop_conversation(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы вышли из режима оценки ответов.")


@router.message(StateFilter(BotStates.conversation_state))
async def handle_conversation_message(message: types.Message, state: FSMContext):
    if message.text:
        data = await state.get_data()
        history = data.get("history", [])
        history.append({"role": "user", "content": message.text})
        payload = {
            "model": "google/gemma-3-4b",
            "messages": [
                            {"role": "system", "content": conversation_systemp_prompt}
                        ] + history,
            "temperature": 0.4
        }
        try:
            resp = requests.post(LM_API_URL, json=payload)
            resp.raise_for_status()
            result = resp.json()
            reply = result["choices"][0]["message"]["content"]
        except Exception as e:
            reply = f"Ошибка при запросе к LLM: {e}"
        history.append({"role": "assistant", "content": reply})
        if len(history) > 20:
            history = [history[0]] + history[6:]
        await state.update_data(history=history)
        await message.answer(reply)
    else:
        await message.answer("Пожалуйста, отправляйте только текстовые сообщения в этом режиме.")


@router.message(F.photo, StateFilter(BotStates.photo_marking_state))
async def handle_photo(message: types.Message, state: FSMContext):
    caption = message.caption or "*Текст отсутствует*"
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    bio = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=bio)
    bio.seek(0)
    image_base64 = base64.b64encode(bio.read()).decode("utf-8")
    payload = payload = {
        "model": "google/gemma-3-4b",
        "messages": [
            {
                "role": "system",
                "content": f"{photo_systemp_prompt}\nТекст под фото: «{caption}»"
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": caption},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ],
        "temperature": 0.4
    }
    try:
        resp = requests.post(LM_API_URL, json=payload)
        resp.raise_for_status()
        result = resp.json()
        reply = result["choices"][0]["message"]["content"]
    except Exception as e:
        reply = f"Ошибка при запросе к LLM с фото: {e}\nОтвет сервера: {resp.text if 'resp' in locals() else 'Нет ответа сервера'}"
    await state.clear()
    await message.answer(reply)


@router.message(F.text, BotStates.questionnaire_marking_state)
async def handle_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data["alco"] == -1:
        alco = "Отрицательно"
    elif data["alco"] == 0:
        alco = "Нейтрально"
    else:
        alco = "Положительно"

    if data["tobacco"] == -1:
        tobacco = "Отрицательно"
    elif data["tobacco"] == 0:
        tobacco = "Нейтрально"
    else:
        tobacco = "Положительно"
    additional_info = f"""
    Вот возможная полезная информация о пользователе:
    Имя: {data["name"]},
    Возраст: {data["age"]},
    Пол: {data["sex"]},
    Знак зодиака: {data["zodiac"]},
    Рост: {data["height"]},
    Вес: {data["weight"]},
    Есть ли дети: {data["kids"]},
    Отношение к алкоголю: {alco},
    Отношение к алкоголю: {tobacco},
    """
    user_input = message.text
    payload = {
        "model": "google/gemma-3-4b",
        "messages": [
            {"role": "system", "content": questionnaire_systemp_prompt + "\n" + additional_info},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.4
    }
    try:
        resp = requests.post(LM_API_URL, json=payload)
        resp.raise_for_status()
        result = resp.json()
        reply = result["choices"][0]["message"]["content"]
        reply = reply.replace("анкёй", "анкетой")
    except Exception as e:
        reply = f"Ошибка при запросе к LLM: {e}"
    if reply != ("Привет! Я помогу сделать твою анкету для знакомств лучше — пришли её сюда, и я дам советы по "
                 "улучшению!"):
        await state.clear()
    await message.answer(reply)
