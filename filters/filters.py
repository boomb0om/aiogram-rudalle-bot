from contextvars import ContextVar
from aiogram import types
from aiogram.types import CallbackQuery, ChatType, InlineQuery, Message, Poll, ChatMemberUpdated
from aiogram.dispatcher.filters import Filter, BoundFilter

import config


class IsAdmin(Filter):
    key = 'is_admin'

    async def check(self, message: types.Message):
        return message.from_user.id in config.ADMIN_IDS
    
    
class IsNotCommand(Filter):
    key = 'not_command'

    async def check(self, message: types.Message):
        return not message.text.startswith('/')
    

class NotStateFilter(BoundFilter):
    """
    Not + StateFilter
    """
    key = 'not_state'

    ctx_state = ContextVar('user_state')

    def __init__(self, dispatcher, not_state):
        from aiogram.dispatcher.filters.state import State, StatesGroup
        
        state = not_state
        self.dispatcher = dispatcher
        states = []
        if not isinstance(state, (list, set, tuple, frozenset)) or state is None:
            state = [state, ]
        for item in state:
            if isinstance(item, State):
                states.append(item.state)
            elif inspect.isclass(item) and issubclass(item, StatesGroup):
                states.extend(item.all_states_names)
            else:
                states.append(item)
        self.states = states

    def get_target(self, obj):
        if isinstance(obj, CallbackQuery):
            return getattr(getattr(getattr(obj, 'message', None),'chat', None), 'id', None), getattr(getattr(obj, 'from_user', None), 'id', None)
        return getattr(getattr(obj, 'chat', None), 'id', None), getattr(getattr(obj, 'from_user', None), 'id', None)

    async def check(self, obj):
        if '*' in self.states:
            return False

        try:
            state = self.ctx_state.get()
        except LookupError:
            chat, user = self.get_target(obj)

            if chat or user:
                state = await self.dispatcher.storage.get_state(chat=chat, user=user)
                self.ctx_state.set(state)
                if state in self.states:
                    return False

        else:
            if state in self.states:
                return False

        return {'state': self.dispatcher.current_state(), 'raw_state': state}