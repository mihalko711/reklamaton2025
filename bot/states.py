from aiogram.fsm.state import StatesGroup, State


class BotStates(StatesGroup):
    choosing_menu_state = State()
    questionnaire_marking_state = State()
    photo_marking_state = State()
    first_message_state = State()
    conversation_state = State()
    conversation_advice_state = State()
