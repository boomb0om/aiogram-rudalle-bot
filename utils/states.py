from aiogram import Dispatcher
from aiogram.dispatcher.filters.state import State, StatesGroup

class UserStates(StatesGroup):
    start = State()
    choosing_aspect_ratio = State()
    choosing_images_num = State()
    processing = State()
    choosing_image_to_upscale = State()

not_processing_state = [None, UserStates.start, UserStates.choosing_aspect_ratio, 
                        UserStates.choosing_images_num, UserStates.choosing_image_to_upscale]