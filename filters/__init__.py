from aiogram import Dispatcher

from .filters import IsAdmin, NotStateFilter, IsNotCommand


def setup_filters(dp: Dispatcher):
    dp.filters_factory.bind(IsAdmin)
    dp.filters_factory.bind(NotStateFilter)
    dp.filters_factory.bind(IsNotCommand)