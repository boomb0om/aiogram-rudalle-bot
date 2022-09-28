from aiogram import Dispatcher
from aiogram import types
from aiogram.dispatcher import FSMContext
from utils.states import UserStates

async def get_id_message(message):
    uid = message.from_user.id
    await message.answer(str(uid))
    

async def get_state_message(message: types.Message, state: FSMContext):
    uid = message.chat.id
    state = await state.get_state()
    await message.answer(str(state))


async def restart_user_state_message(message):
    user_id = message.text.replace('/restart_user_state', '').strip()
    if user_id == '':
        await message.answer("Введите id пользователя!") 
        return
    
    user_id = int(user_id)
    state = Dispatcher.get_current().current_state(chat=user_id, user=user_id)
    last_state = await state.get_state()
    await state.set_state(UserStates.start)
    new_state = await Dispatcher.get_current().current_state(chat=user_id, user=user_id).get_state()
    await message.answer(f"State пользователя {user_id} изменено с {last_state} на {new_state}")