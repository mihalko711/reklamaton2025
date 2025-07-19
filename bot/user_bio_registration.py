from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.state import StateFilter
from aiogram import Router, types, F

from states import UserRegistrationStates

user_route = Router()


@user_route_message(UserRegistrationStates.name_state)
async def ()
