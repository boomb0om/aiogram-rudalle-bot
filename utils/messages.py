from PIL import Image
from io import BytesIO
import io
import asyncio
from aiogram.utils import exceptions

import logging
import config


async def broadcast_message(bot, text, user_ids, *args, logger=None, timeout=0.05, **kwargs):
    # replace logger if none
    logger = logger or logging.getLogger('dummy')
    
    successfull = 0
    for uid in user_ids:
        await asyncio.sleep(timeout)
        try:
            await bot.send_message(uid, text)
            successfull += 1
        except exceptions.BotBlocked:
            continue
        except Exception as error:
            logger.exception(f"Broadcast error: {str(error)}")
            continue
    return successfull


async def send_message_safe(method, num_retries, *args, logger=None, **kwargs):
    """
    Send message safely
    """
    # replace logger if none
    logger = logger or logging.getLogger('dummy')
    
    if num_retries <= 0:
        logger.warning(f"Retries ended, sending failed")
        return

    try:
        return await method(*args, **kwargs)
    except exceptions.BotBlocked:
        logger.error(f"Blocked by user")
    except exceptions.ChatNotFound:
        logger.error(f"Chat not found")
    except exceptions.RetryAfter as e:
        logger.warning(f"Flood limit is exceeded. Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await self.send_message_rec(method, num_retries-1, *args, **kwargs)  # Recursive call
    except exceptions.UserDeactivated:
        logger.error(f"User is deactivated")
    except exceptions.TelegramAPIError:
        logger.exception(f"TelegramAPIError")
    except exceptions.NetworkError:
        logger.error(f"NetworkError")
        await asyncio.sleep(config.network_error_timeout)
        return await self.send_message_rec(method, num_retries-1, *args, **kwargs)  # Recursive call


async def send_media_safe(method, num_retries, buff, logger=None, **kwargs):
    """
    Send message with media safely
    """
    # replace logger if none
    logger = logger or logging.getLogger('dummy')
    
    if num_retries <= 0:
        logger.warning(f"Retries ended, sending failed")
        return

    try:
        buff.seek(0)
        return await method(buff, **kwargs)
    except exceptions.BotBlocked:
        logger.error(f"Blocked by user")
    except exceptions.ChatNotFound:
        logger.error(f"Chat not found")
    except exceptions.RetryAfter as e:
        logger.warning(f"Flood limit is exceeded. Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await self.send_document_rec(method, num_retries-1, buff, **kwargs)  # Recursive call
    except exceptions.UserDeactivated:
        logger.error(f"User is deactivated")
    except exceptions.TelegramAPIError:
        logger.exception(f"TelegramAPIError")
    except exceptions.NetworkError:
        logger.error(f"NetworkError (send_media_safe)")
        await asyncio.sleep(config.network_error_timeout)
        return await self.send_document_rec(method, num_retries-1, buff, **kwargs)  # Recursive call