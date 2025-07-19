from aiogram.fsm.state import StatesGroup, State


class BotStates(StatesGroup):
    choosing_menu_state = State()
    questionnaire_marking_state = State()
    photo_marking_state = State()
    conversation_state = State()


class UserRegistrationStates(StatesGroup):
    name_state = State()
    age_state = State()
    sex_state = State()
    zodiac_sign_state = State()
    height_state = State()
    weight_state = State()
    edu_state = State()
    children_state = State()
    alcohol_state = State()
    tobacco_state = State()
