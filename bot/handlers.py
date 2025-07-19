import io
import requests
import base64
import os

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.state import StateFilter
from aiogram import Router, types, F

from states import BotStates
from prompts import questionnaire_systemp_prompt

LM_API_URL = os.getenv("LM_API_URL")
if not LM_API_URL:
    raise ValueError("LM_API_URL не найден в .env")

router = Router()


@router.message(StateFilter(None))
async def start_command(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Оценить анкету")],
            [KeyboardButton(text="Оценить фотографию")],
            [KeyboardButton(text="Общий диалог")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await state.set_state(BotStates.choosing_menu_state)
    await message.answer("Привет! Я бот для оценки анкет, фотографий и ответов. Выберите, что вы хотите оценить:",
                         reply_markup=keyboard)


@router.message(F.text == "Оценить анкету", StateFilter(BotStates.choosing_menu_state))
async def rate_profile(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.questionnaire_marking_state)
    await message.answer("Пожалуйста, отправьте анкету в виде текста.")


@router.message(F.text == "Оценить фотографию", StateFilter(BotStates.choosing_menu_state))
async def rate_photo(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.photo_marking_state)
    await message.answer("Пожалуйста, отправьте фотографию с подписью.")


@router.message(F.text == "Общий диалог", StateFilter(BotStates.choosing_menu_state))
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


# Здесь в интерактивном режиме оцениванием сообщения
@router.message(StateFilter(BotStates.conversation_state))
async def handle_conversation_message(message: types.Message, state: FSMContext):
    if message.text:
        data = await state.get_data()
        history = data.get("history", [])
        history.append({"role": "user", "content": message.text})
        payload = {
            "model": "google/gemma-3-4b",
            "messages": [
                            {"role": "system", "content": "Ты — умный помощник, отвечай на запросы на русском языке."}
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
            history = history[0] + history[6:]
        await state.update_data(history=history)
        await message.answer(reply)
    else:
        await message.answer("Пожалуйста, отправляйте только текстовые сообщения в этом режиме.")


@router.message(F.photo, StateFilter(BotStates.photo_marking_state))
async def handle_photo(message: types.Message, state: FSMContext):
    caption = message.caption or ""
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    bio = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=bio)
    bio.seek(0)
    image_base64 = base64.b64encode(bio.read()).decode("utf-8")
    payload = {
        "model": "google/gemma-3-4b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты — умный помощник. "
                    "Пользователь прислал фотографию, на которой изображён человек. "
                    f"Текст под фото: «{caption}». "
                    "Дай осмысленный ответ на русском языке."
                )
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
    user_input = message.text
    payload = {
        "model": "google/gemma-3-4b",
        "messages": [
            {"role": "system", "content": questionnaire_systemp_prompt},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.4
    }
    try:
        resp = requests.post(LM_API_URL, json=payload)
        resp.raise_for_status()
        result = resp.json()
        reply = result["choices"][0]["message"]["content"]
    except Exception as e:
        reply = f"Ошибка при запросе к LLM: {e}"
    if reply != ("Привет! Я помогу сделать твою анкету для знакомств лучше — пришли её сюда, и я дам советы по "
                 "улучшению!"):
        await state.clear()
    await message.answer(reply)
