import io
import pytesseract
from PIL import Image
import requests
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.state import StateFilter
from aiogram import Router, types, F
from together import Together

from states import BotStates

client = Together(api_key = os.environ.get('TOGETHER_API_KEY'))
token_cloudinary = os.getenv('CLOUDINARY_API_SECRET')
router = Router()
answers_dict = {}
cloudinary.config( 
    cloud_name = os.getenv('CLOUDINARY_CLOUD'), 
    api_key = os.getenv('CLOUDINARY_API_KEY'), 
    api_secret = os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

sys_prompt_photo = '''
                        1. твоя работа только оценивать присланные фотографии и давать советы по их улучшению(фотографии для приложения знакомств)
                        2. оценка состоит в критическом комментарии фотографии на 1-2 предложения, можно с сарказмом
                        3. советов нужно 3-4 штуки отдельынми короткими пунктами, они должны быть уникальными, отражающими проблемы с фотографиями, а не общими
                        4. если входные данные не подходят по условиям из пунктов 5-7, то элегантно отправляй людей куда подальше, с коротеньким анекдотом и описанием проблемы
                        5. проблема небезопаасного контента, нельзя пропускать NSFW контент
                        6. принимаются только фотографии(именно ФОТОГРАФИИ, а не картинки) и может немного их ретушированные версии
                        7. на фотографии должен быть ЧЕЛОВЕК!
                        8. иногда добавляй в конце какой-ниубдь жутко комичный постскриптум можно даже с черным юмором и матюгнуться
                        9. не употребялй форматирование markdown, но употребляй форматирование текста для telegram 
                        '''
sys_prompt_advice = '''
                        Ты — аналитик переписки в приложении для знакомств.

                        Тебе приходит текст переписки, извлечённый из изображения с помощью OCR.

                        Твоя задача:

                        1. Распределить реплики по ролям (например, "Пользователь 1", "Пользователь 2").
                        2. Выделить и прокомментировать любые странные, подозрительные или необычные моменты в переписке.
                        3. Дать конкретный совет, как лучше продолжить диалог.
                        4. Добавить лёгкую и уместную шутку, связанную с ситуацией или содержанием переписки.

                        Отвечай кратко, по пунктам, понятно и с лёгким юмором.

                        ---

                        Пример входных данных:

                        <сюда вставляется распознанный текст переписки>

                        ---

                        Начинай анализ:
                        '''

sys_prompt_first_message = '''
                            1. Твоя задача — придумывать остроумное, зацепляющее и уместное первое сообщение, с которым можно начать диалог в приложении для знакомств.
                            2. На вход ты получаешь фотографию профиля и текст профиля (если есть). Используй оба источника: изображение и текст — чтобы придумать сообщение, которое выглядит максимально персонализированно.
                            3. Сообщение должно быть коротким (1-2 предложения), живым, желательно с юмором, сарказмом, или необычной формулировкой. Главное — чтобы это выглядело человечно, а не как спам.
                            4. Избегай клише типа "привет, как дела", "ты милашка", "красивое фото", "что ищешь?" — такое писать нельзя, иначе ты будешь звучать, как унылый бот.
                            5. Если фото или текст профиля вызывают подозрение (NSFW, нет лица, мем вместо человека, текст пустой или бессмысленный) — не пиши сообщение, а сгенерируй шуточный отказ или колкий комментарий с анекдотом.
                            6. Используй форматирование Telegram (жирный, курсив), но **не используй Markdown**.
                            7. Иногда можешь вставить лёгкий постскриптум, например, с дикой шуткой или неформальной ремаркой — но не чаще, чем в каждом пятом сообщении.

                            '''
                            
sys_prompt_anketa =         '''
                            Ты — эксперт по оценке анкет для знакомств, работаешь грубовато, с сарказмом, но по делу. На входе:
                            – фотография профиля
                            – текст анкеты (описание, цели, факты)
                            – возможный комментарий от пользователя

                            Твоя задача:

                                Коротко прокомментировать фото (1–2 язвительных предложения)

                                Дать 3–4 нестандартных совета по улучшению (по фото и описанию)

                                Отметить странности и недостатки анкеты: фальшь, общие фразы, кринж

                                Постскриптум — можешь с чёрным юмором или матом (по желанию)

                            Важно:
                            – Если это не фотография человека (арт, мем, скриншот), вежливо откажи с шуткой
                            – NSFW — сразу руби, не допуская
                            – Только живые, настоящие фото с лицом, без фильтров

                            Формат — обычный текст, без markdown, можно использовать капс и подчёркивания. Пиши так, будто ты уставший редактор анкет на Twinby, который всё уже видел.
                            '''

sys_prompt_just_converse =  '''1. Твоя задача — непринуждённо общаться на тему знакомств, отношений, свиданий и всяких романтических факапов.
                            2. Отвечай коротко, остроумно, с самоиронией, можно с лёгкой дерзостью и сарказмом.
                            3. Не будь банальным коучем. Никаких “будь собой” и “всё получится” — только живые, человеческие ответы.
                            4. Иногда можешь прикинуться другом на кухне с бокалом вина, слушающим чужие любовные страдания и раздающим советы.
                            5. Не стесняйся черного юмора, но не перегибай — собеседник всё же живой человек.
                            6. Не используй markdown, но оформляй текст для Telegram понятно и с акцентами, если нужно.
                            7. Если вопрос странный или токсичный — отвечай с иронией или пошли “на кофе подумать о жизни”.
                            '''
memory_len = 20
    
messages_from_bro = [{"role" : "system", "content" : sys_prompt_just_converse}]

def text_from_image(image_bytes: bytes):
    image = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image, lang='rus')
    return text.strip()

def converse_model_call(messages_now):
    if len(messages_now) > 20 :
        messages_now = messages_now[-20:]
    return client.chat.completions.create( model = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
                                     messages = messages_now, stream = True) 

def model_call(system_prompt, image_bio = None, text_in = None):
    messages = [
        {
            "role" : "system",
            "content" : system_prompt
        }
    ]
    if image_bio is None:
        messages.append({"role": "user", "content": text_in})
            
    elif text_in is None:
        image_url = cloudinary.uploader.upload(image_bio.read())['secure_url']
        messages.append({"role": "user", "content":[
                            {
                                "type" : "image_url",
                                "image_url" : {
                                    "url" : image_url
                                }
                            }
                        ]})
    else:
        image_url = cloudinary.uploader.upload(image_bio.read())['secure_url']
        messages.append({"role": "user", "content":[
                            {
                                "type" : "image_url",
                                "image_url" : {
                                    "url" : image_url
                                }
                            },
                            {
                                "type" : "text",
                                "text" : text_in
                            }
                        ]})


    return     client.chat.completions.create( model = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
                                     messages = messages, stream = True)    


@router.message(StateFilter(None))
async def start_command(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Дать совет по анкете")],
            [KeyboardButton(text="Получить отзыв о фотографии")],
            [KeyboardButton(text="Предложить первое сообщение")],
            [KeyboardButton(text="Дать совет по переписке")],
            [KeyboardButton(text="Поговорим")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await state.set_state(BotStates.choosing_menu_state)
    await message.answer("Привет! Я бот для оценки анкет, фотографий и ответов. Выберите, что вы хотите оценить:",
                         reply_markup=keyboard)


@router.message(F.text == "Дать совет по анкете", StateFilter(BotStates.choosing_menu_state))
async def rate_profile(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.questionnaire_marking_state)
    await message.answer("Пожалуйста, скинь анкету в виде текста или скрина, также можешь добавить свои вопросы.")


@router.message(F.text == "Дать совет по переписке", StateFilter(BotStates.choosing_menu_state))
async def conversation_advice(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.conversation_advice_state)
    await message.answer("Пожалуйста, отправьте скрин или текст переписки.")

@router.message(F.text == "Получить отзыв о фотографии", StateFilter(BotStates.choosing_menu_state))
async def rate_photo(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.photo_marking_state)
    await message.answer("Пожалуйста, отправьте фотографию.")



@router.message(F.text == "Предложить первое сообщение", StateFilter(BotStates.choosing_menu_state))
async def start_conversation(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.first_message_state)
    await message.answer("Можешь прислать фотку с твоими пожеланиями(можно даже только одно из двух)")

@router.message(F.text == "Поговорим", StateFilter(BotStates.choosing_menu_state))
async def start_converse_with_bot(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Завершим")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await state.set_state(BotStates.conversation_state)
    await message.answer("Ну поговорим)", reply_markup = keyboard )

@router.message(F.text == "Завершим", StateFilter(BotStates.conversation_state))
async def close_conversation(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Обращайся, бро!")



@router.message(StateFilter(BotStates.first_message_state))
async def create_first_message(message: types.Message, state: FSMContext):
    has_text = message.caption or message.text
    has_compressed_photo = bool(message.photo)
    
    # Проверка, что документ — это изображение
    is_uncompressed_image = (
        message.document is not None and
        message.document.mime_type and
        message.document.mime_type.startswith("image/")
    )
    if has_compressed_photo:
        photo_file = message.photo[-1]
    elif is_uncompressed_image:
        photo_file = message.document
    else:
        photo_file = None

    try:
        if photo_file and has_text:
            text = message.caption or message.text
            file = await message.bot.get_file(photo_file.file_id)
            bio = io.BytesIO()
            await message.bot.download_file(file.file_path, destination=bio)
            bio.seek(0)
            filename = file.file_path.split('/')[-1]
            answers_dict[filename] = ''
            response = model_call(sys_prompt_first_message, image_bio = bio, text_in = text)
        elif photo_file:
            file = await message.bot.get_file(photo_file.file_id)
            bio = io.BytesIO()
            await message.bot.download_file(file.file_path, destination=bio)
            bio.seek(0)
            filename = file.file_path.split('/')[-1]
            answers_dict[filename] = ''
            response = model_call(sys_prompt_first_message, image_bio = bio)
        elif has_text:
            text = message.caption or message.text
            filename = 'empty'
            answers_dict[filename] = ''
            response = model_call(sys_prompt_first_message, text_in = text)

        else:
            await message.answer("Нет ни текста, ни изображения.")

        for token in response:
            try:
                answers_dict[filename] += token.choices[0].delta.content
            except IndexError:
                continue

        reply = answers_dict[filename]
    except Exception as e:
        reply = f"Ошибка при запросе к LLM с фото: {e}"

    print(reply)
    await state.clear()
    await message.answer(reply)

@router.message(StateFilter(BotStates.questionnaire_marking_state))
async def advice_anketa(message: types.Message, state: FSMContext):
    has_text = message.caption or message.text
    has_compressed_photo = bool(message.photo)
    
    # Проверка, что документ — это изображение
    is_uncompressed_image = (
        message.document is not None and
        message.document.mime_type and
        message.document.mime_type.startswith("image/")
    )
    if has_compressed_photo:
        photo_file = message.photo[-1]
    elif is_uncompressed_image:
        photo_file = message.document
    else:
        photo_file = None

    try:
        if photo_file and has_text:
            text = message.caption or message.text
            file = await message.bot.get_file(photo_file.file_id)
            bio = io.BytesIO()
            await message.bot.download_file(file.file_path, destination=bio)
            bio.seek(0)
            filename = file.file_path.split('/')[-1]
            answers_dict[filename] = ''
            text_imag = text_from_image(bio.read())
            response = model_call(sys_prompt_anketa, text_in = text + text_imag)
        elif photo_file:
            file = await message.bot.get_file(photo_file.file_id)
            bio = io.BytesIO()
            await message.bot.download_file(file.file_path, destination=bio)
            bio.seek(0)
            filename = file.file_path.split('/')[-1]
            text_imag = text_from_image(bio.read())
            answers_dict[filename] = ''
            response = model_call(sys_prompt_anketa, text_in = text_imag)
        elif has_text:
            text = message.caption or message.text
            filename = 'empty'
            answers_dict[filename] = ''
            response = model_call(sys_prompt_anketa, text_in = text)

        else:
            await message.answer("Нет ни текста, ни изображения.")

        for token in response:
            try:
                answers_dict[filename] += token.choices[0].delta.content
            except IndexError:
                continue

        reply = answers_dict[filename]
    except Exception as e:
        reply = f"Ошибка при запросе к LLM с фото: {e}"

    print(reply)
    await state.clear()
    await message.answer(reply)



# Здесь в интерактивном режиме оцениванием сообщения
@router.message(StateFilter(BotStates.conversation_state))
async def handle_conversation_message(message: types.Message, state: FSMContext):
    if message.text:
        data = await state.get_data()
        history = data.get("messages_from_bro", [])
        history.append({"role": "user", "content": message.text})
        if len(history) >= 2:
            history[-1], history[-2] = history[-2], history[-1]
        try:
            filename = 'converse'
            answers_dict[filename] = ''
            response = converse_model_call(history)
            for token in response:
                try:
                    answers_dict[filename] += token.choices[0].delta.content
                except IndexError:
                    continue
            reply = answers_dict[filename]
        except Exception as e:
            reply = f"Ошибка при запросе к LLM: {e}"
        history.append({"role": "assistant", "content": reply})
        if len(history) >= 2:
            history[-1], history[-2] = history[-2], history[-1]
        await state.update_data(history=history)
        await message.answer(reply)
    else:
        await message.answer("Пожалуйста, отправляйте только текстовые сообщения в этом режиме.")


@router.message(F.photo, StateFilter(BotStates.photo_marking_state))
async def handle_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    bio = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=bio)
    bio.seek(0)
    try:
        filename = file.file_path.split('/')[-1]
        answers_dict[filename] = ''
        response = model_call(sys_prompt_photo, image_bio = bio)
        for token in response:
            try:
                answers_dict[filename] += token.choices[0].delta.content
            except IndexError:
                continue

        reply = answers_dict[filename]
        print(reply)
    except Exception as e:
        reply = f"Ошибка при запросе к LLM с фото: {e}"
    await state.clear()
    await message.answer(reply)

@router.message(
    lambda msg: msg.content_type == 'document' and msg.document.mime_type.startswith('image/'),
    StateFilter(BotStates.photo_marking_state)
)
async def handle_document(message: types.Message, state: FSMContext):
    document = message.document
    file = await message.bot.get_file(document.file_id)
    bio = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=bio)
    bio.seek(0)
    
    try:
        filename = file.file_path.split('/')[-1]
        answers_dict[filename] = ''
        response = model_call(sys_prompt_photo, image_bio = bio)
        for token in response:
            try:
                answers_dict[filename] += token.choices[0].delta.content
            except IndexError:
                continue

        reply = answers_dict[filename]
        print(reply)
    except Exception as e:
        reply = f"Ошибка при запросе к LLM с фото: {e}"
    await state.clear()
    await message.answer(reply)

@router.message(F.photo, StateFilter(BotStates.conversation_advice_state))
async def handle_conversation_advice_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    bio = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=bio)
    bio.seek(0)
    try:
        filename = file.file_path.split('/')[-1]
        conversation_text = text_from_image(bio.read())
        response = model_call(sys_prompt_advice, text_in = conversation_text)    
        answers_dict[filename] = ''
        print('\n' + '-' * 100 + '\n')
        for token in response:
            try:
                answers_dict[filename] += token.choices[0].delta.content
            except IndexError:
                continue

        reply = answers_dict[filename]
        print(reply)
    except Exception as e:
        reply = f"Ошибка при запросе к LLM с фото: {e}\nОтвет сервера: {response}"
    await state.clear()
    await message.answer(reply)

@router.message(
    lambda msg: msg.content_type == 'document' and msg.document.mime_type.startswith('image/'),
    StateFilter(BotStates.conversation_advice_state)
)
async def handle_conversation_advice_document(message: types.Message, state: FSMContext):
    document = message.document
    file = await message.bot.get_file(document.file_id)
    bio = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=bio)
    bio.seek(0)
    
    try:
        filename = file.file_path.split('/')[-1]
        conversation_text = text_from_image(bio.read())
        response = model_call(sys_prompt_advice, text_in = conversation_text)
        answers_dict[filename] = ''
        print('\n' + '-' * 100 + '\n')
        for token in response:
            try:
                answers_dict[filename] += token.choices[0].delta.content
            except IndexError:
                continue

        reply = answers_dict[filename]
        print(reply)
    except Exception as e:
        reply = f"Ошибка при запросе к LLM с фото: {e}\nОтвет сервера: {response}"
    await state.clear()
    await message.answer(reply)

@router.message(F.text, StateFilter(BotStates.conversation_advice_state))
async def handle_conversation_advice_text(message: types.Message, state: FSMContext):
    filename = message.text.split(' ')[0]
    try:
        response = model_call(sys_prompt_advice, text_in = message.text)    
        answers_dict[filename] = ''
        print('\n' + '-' * 100 + '\n')
        for token in response:
            try:
                answers_dict[filename] += token.choices[0].delta.content
            except IndexError:
                continue

        reply = answers_dict[filename]
        print(reply)
    except Exception as e:
        reply = f"Ошибка при запросе к LLM с фото: {e}\nОтвет сервера: {response}"
    await state.clear()
    await message.answer(reply)


@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    user_input = message.text
    payload = {
        "model": "google/gemma-3-4b",
        "messages": [
            {"role": "system", "content": "Ты — умный помощник, отвечай на запросы на русском языке."},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.6
    }
    try:
        resp = requests.post(LM_API_URL, json=payload)
        resp.raise_for_status()
        result = resp.json()
        reply = result["choices"][0]["message"]["content"]
    except Exception as e:
        reply = f"Ошибка при запросе к LLM: {e}"
    await state.clear()
    await message.answer(reply)
