from typing import Callable, Type

from telegram import Update
from telegram.ext import CallbackContext

from tg.bot.state_classes import BaseState

StateDecoratorType = Callable[[Type['BaseState']], Type['BaseState']]


def process(update: Update, context: CallbackContext):
    current_state = context.user_data.get('state') or router.get('start')
    next_state = current_state.process(update, context) or router.get('start')

    if not isinstance(next_state, BaseState):
        raise ValueError(f'Expect BaseState subclass as next_state value, got {next_state!r}')

    context.user_data['state'] = next_state


class UnknownStateClassLocatorError(Exception):
    pass
