from .default import get_id_message, get_state_message, restart_user_state_message
from filters import IsAdmin

def init_default_handlers(dp):
    dp.register_message_handler(get_id_message, state='*', commands=['get_id'])
    dp.register_message_handler(get_state_message, state='*', commands=['get_state'])
    dp.register_message_handler(restart_user_state_message, IsAdmin(), state='*', commands=['restart_user_state'])