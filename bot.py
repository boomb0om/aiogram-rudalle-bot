from PIL import Image
from io import BytesIO
import json
import numpy as np
import os
import time
import sys
import logging
import re
import base64
from io import BytesIO
import string
import random

import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import exceptions
from aiogram.utils.exceptions import Throttled
from aiogram.types import ParseMode
from aiogram.utils.deep_linking import get_start_link, decode_payload

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import config
from utils.files import download_to_bytes
from utils.logger import setup_logger
from utils.messages import send_message_safe, send_media_safe, broadcast_message
from filters import setup_filters, IsAdmin, IsNotCommand
from handlers import init_default_handlers
from utils.states import UserStates, not_processing_state
from utils.keyboards import KEYBOARDS

from app.api import KFServingAPI

logger = setup_logger('bot.log')

# init storage and bot
storage = MemoryStorage()
API_KEY = config.api_key
bot = Bot(token=API_KEY)
dp = Dispatcher(bot, storage=storage)

# setup filters
setup_filters(dp)

# setup default handlers
init_default_handlers(dp)

#
@dp.errors_handler()
async def global_error_handler(update, exception):
    logger.error(f'Update: {update} \n{exception}', exc_info=True)
    
    
async def anti_flood(*args, **kwargs):
    message = args[0]
    await message.answer("Пожалуйста, не нужно отправлять боту слишком много сообщений сразу")

    
############################
############################ ADMIN COMMANDS
############################

@dp.message_handler(IsAdmin(), state='*', commands=['get_queue'])
@dp.throttled(anti_flood, rate=1)
async def get_queue_message(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    await message.answer(f'{rudalleAPI.queue}')
    
@dp.message_handler(IsAdmin(), state='*', commands=['get_stats'])
@dp.throttled(anti_flood, rate=1)
async def get_queue_message(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    await message.answer(f'{len(rudalleAPI.queue)}')
    
    
############################
############################
############################

@dp.message_handler(state='*', commands=['position'])
@dp.throttled(anti_flood, rate=1)
async def position_message(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    
    if uid not in rudalleAPI.queue:
        await message.answer(f"Вы сейчас не находитесь в очереди!")
        return
    
    if uid == rudalleAPI.queue[0]:
        await message.answer(f"Вы в очереди на 1м месте. Модель сейчас обрабатывает ваш запрос.")
    else:
        await message.answer(f"Вы в очереди на {rudalleAPI.queue.index(uid)+1} позиции")
    

@dp.message_handler(state=[UserStates.start, None], commands=['start'])
@dp.throttled(anti_flood, rate=2)
async def start_message(message: types.Message, state: FSMContext):
    await UserStates.start.set()
    
    await message.answer(
        "Привет, Я ruDALL-E Kandinsky bot! Я могу генерировать изображения по описанию.",
        reply_markup=KEYBOARDS['hide']
    )
    await message.answer("Чтобы начать, просто напиши мне то, что ты хочешь сгенерировать.")

    
@dp.message_handler(state='*', commands=['help'])
@dp.throttled(anti_flood, rate=2)
async def help_message(message: types.Message, state: FSMContext):
    text = "Просто отправь мне текстовое описание и я сгенерирую фото по этому описанию. "+\
           'Улучшение изображений с помощью диффузии возможно только для изображений формата 1:1. '+\
           'Для улучшения изображений с другим соотношением сторон будет использоваться RealESRGAN.\n'+\
           '/position - посмотреть позицию в очереди\n'+\
           '/finish - выйти из обработки изображений'
    await message.answer(text)
    
    
@dp.message_handler(IsNotCommand(), state=UserStates.processing)
@dp.throttled(anti_flood, rate=2)
async def processing_message(message):
    await message.answer("Сначала дождитесь, пока закончится обработка!")

    
@dp.message_handler(IsNotCommand(), state=[UserStates.start, None], content_types=['text'])
@dp.throttled(anti_flood, rate=1)
async def aspect_ration_message(message: types.Message, state: FSMContext):
    query = message.text.strip()
    await state.update_data(query=query)
    
    text = 'C каким соотношением сторон генерировать изображения? Можете выбрать один из предложенных вариантов, '+\
           'либо ввести соотношение в формате W:H'
    await message.answer(text, reply_markup=KEYBOARDS['aspect_ratio']['markup'])
    await UserStates.choosing_aspect_ratio.set()
    
    
@dp.message_handler(IsNotCommand(), state=UserStates.choosing_aspect_ratio, content_types=['text'])
@dp.throttled(anti_flood, rate=1)
async def images_num_message(message: types.Message, state: FSMContext):
    try:
        aspect_ratio_str = message.text.strip()
        assert re.fullmatch(r"\d+:\d+", aspect_ratio_str)
        
        a, b = aspect_ratio_str.split(':')
        a, b = int(a), int(b)
        assert a != 0 and b != 0
        
        aspect_ratio = a/b
        if a/b == 1:
            aspect_ratio = 1
        
        assert max(aspect_ratio, 1/aspect_ratio) <= 4
    except Exception as err:
        text = "Введите соотношение сторон в формате W:H. W и H должны быть не 0. "+\
               "max(W/H, H/W) должен быть <= 4" 
        return await message.answer(text)
    
    aspect_ratio_module = max(aspect_ratio, 1/aspect_ratio)
        
    if aspect_ratio_module == 1:
        imgs_to_gen_keyboard = KEYBOARDS['imgs_to_gen_full']
    elif 1 < aspect_ratio_module <= 2:
        imgs_to_gen_keyboard = KEYBOARDS['imgs_to_gen_medium']
    elif 2 < aspect_ratio_module:
        imgs_to_gen_keyboard = KEYBOARDS['imgs_to_gen_small']
        
    await state.update_data(aspect_ratio=aspect_ratio, imgs_to_gen_variants=imgs_to_gen_keyboard['variants'])
    
    text = 'Выберите количество изображений для генерации'
    await message.answer(text, reply_markup=imgs_to_gen_keyboard['markup'])
    await UserStates.choosing_images_num.set()
    
    
@dp.message_handler(IsNotCommand(), state=[UserStates.choosing_images_num], content_types=['text'])
@dp.throttled(anti_flood, rate=1)
async def generate_message(message: types.Message, state: FSMContext): 
    user_data = await state.get_data()
    query = user_data['query']
    aspect_ratio = user_data['aspect_ratio']
    imgs_to_gen_variants = user_data['imgs_to_gen_variants']
    
    try:
        images_to_gen = int(message.text.strip())
        assert str(images_to_gen) in imgs_to_gen_variants
    except Exception as err:
        return await message.answer(f"Пожалуйста, выберите количество изображений для генерации из предложенных вариантов")
    
    await state.update_data(num_imgs=images_to_gen)
    
    text = 'Я добавил вас в очередь на генерацию изображений.\n'+\
           '/position - посмотреть позицию в очереди\n'
    await message.answer(text, reply_markup=KEYBOARDS['hide'])
    await UserStates.processing.set()
    
    error = False
    try:
        data = await rudalleAPI.task_generate(message.from_user.id, query, images_to_gen, aspect_ratio)
    except Exception as err:
        logger.exception(f"task_generate error: {err}")
        error = True
        data = None
        
    if error or not data['ok']:
        if data is not None and 'error' in data:
            logger.error(f"Generate images error: {data['error']}")
        await message.answer(f"Произошла ошибка при работе модели:( Попробуйте, пожалуйста, еще раз")
        await UserStates.start.set()
        return
    
    sr_images = data["sr_images"]
    sr_images_data = [BytesIO(base64.b64decode(img_b64)) for img_b64 in sr_images]
    await state.update_data(sr_images_data=sr_images_data)
    
    grid_images_b64 = data["grid_images"]
    imgsdata = [BytesIO(base64.b64decode(img_b64)) for img_b64 in grid_images_b64]
    
    await send_media_safe(message.answer_photo, 2, imgsdata[0], logger=logger, 
                          caption=f'Результаты генерации по запросу "{query}"')
    if aspect_ratio == 1:
        await send_media_safe(message.answer_photo, 2, imgsdata[1], logger=logger, 
                              caption=f'Результаты генерации с порядковым номером картинки (слева сверху каждого фото)')
        
    text = "Введите номер изображения, которое хотите улучшить, или напишите /finish, чтобы перейти к следующей генерации. "+\
           "Нумерация изображений начинается с единицы и идет слева направо и сверху вниз."
    await message.answer(text)
    await UserStates.choosing_image_to_upscale.set()
    
    
@dp.message_handler(IsNotCommand(), state=[UserStates.choosing_image_to_upscale], content_types=['text'])
@dp.throttled(anti_flood, rate=1)
async def choose_image_to_upscale_message(message: types.Message, state: FSMContext): 
    user_data = await state.get_data()
    user_generated_images = user_data['num_imgs']
    aspect_ratio = user_data['aspect_ratio']
    
    try:
        image_num = int(message.text.strip())
        assert 1 <= image_num <= user_generated_images
    except Exception as err:
        return await message.answer(f"Номер изображения должен быть целом числом от 1 до {user_generated_images}")
    
    await state.update_data(image_num_to_upscale=image_num)
    
    user_sr_images_data = user_data['sr_images_data']
    sr_image_data = user_sr_images_data[image_num-1]

    await UserStates.choosing_image_to_upscale.set()
    await send_media_safe(message.answer_photo, 2, sr_image_data, logger=logger, 
                          caption=f'Изображение, улучшенное с помощью RealESRGAN')
    await message.answer("Можете опять ввести номер изображения для улучшения.\n/finish, чтобы перейти к следующей генерации")
    
    
@dp.message_handler(state=not_processing_state, commands=['finish'])
@dp.throttled(anti_flood, rate=2)
async def finish_message(message: types.Message, state: FSMContext):
    await UserStates.start.set()
    await message.answer("Можете вводить текст для новой генерации", reply_markup=KEYBOARDS['hide'])
    
    
@dp.message_handler(state='*', commands=['cancel'])
@dp.throttled(anti_flood, rate=2)
async def cancel_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state in [UserStates.start.state, None]:
        await message.answer('Кажется, вы на самом начальном этапе. Введите текст для генерации', 
                             reply_markup=KEYBOARDS['hide'])
    elif current_state in [UserStates.choosing_aspect_ratio.state]:
        await message.answer('Ввод успешно отменен. Можете ввести запрос еще раз', reply_markup=KEYBOARDS['hide'])
        await UserStates.start.set()
    elif current_state in [UserStates.choosing_images_num.state]:
        await message.answer('Ввод успешно отменен. Можете выбрать соотношение сторон еще раз', 
                             reply_markup=KEYBOARDS['aspect_ratio']['markup'])
        await UserStates.choosing_aspect_ratio.set()
    elif current_state in [UserStates.processing.state]:
        await message.answer('Запрос уже отправлен в обработку, его нельзя отменить :(', reply_markup=KEYBOARDS['hide'])
    else:
        await message.answer('Кажется, на этом этапе нельзя отменять предыдущее действие.')
    
    
############################
############################ INITIALISATION
############################
    
async def on_startup(dispatcher):
    print('on_startup')
    global rudalleAPI
    rudalleAPI = KFServingAPI(f"http://0.0.0.0:{config.kfserving_http_port}/v2/models/{config.kfserving_name}/infer")
    print(f'QueueAPI created. Server url: {rudalleAPI.url}')
    
async def on_shutdown(dispatcher):
    print('on_shutdown')
    

if __name__ == "__main__":
    # auth
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)