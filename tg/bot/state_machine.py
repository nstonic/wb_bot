from typing import Type

from telegram import Update  # noqa
from telegram.ext import CallbackContext  # noqa

from tg.bot.state_classes import Locator, BaseState


class StateMachine(dict[str, BaseState]):
    commands = ['/start']

    def __init__(self, *, start_state_name: str):
        super().__init__()
        self.start_state_name = Locator(start_state_name)
        self.update = None
        self.context = None

    def register(self, state_name: str):
        def decorator(cls: Type[BaseState]):
            self[state_name] = cls(state_name)

        return decorator

    def process(self, update: Update, context: CallbackContext):
        self.update = update
        self.context = context

        if update.message and update.message.text in self.commands:
            self.react_on_commands()
            return

        locator = context.user_data.get('locator')

        if not locator:
            self.switch_state(self.start_state_name)
            return
        else:
            state = self.get(locator.state_name)
            next_state_locator = state.process(self.update, self.context, **locator.params)

        if not next_state_locator:
            return

        if locator != next_state_locator:
            state.exit_state(update, context)

        self.switch_state(next_state_locator)

    def react_on_commands(self):
        if self.update.message.text == '/start':
            self.switch_state(self.start_state_name)

    def switch_state(self, next_state_locator: Locator):
        next_state = self.get(next_state_locator.state_name)
        if locator := next_state.enter_state(self.update, self.context, **next_state_locator.params):
            next_state_locator = locator
        self.context.user_data['locator'] = next_state_locator

