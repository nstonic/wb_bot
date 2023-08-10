from dataclasses import dataclass
from typing import Optional

from telegram import Update, Message, CallbackQuery
from telegram.ext import CallbackContext


@dataclass
class BaseState:
    state_class_locator: str

    def enter_state(self) -> Optional['BaseState']:
        pass

    def exit_state(self, state_class_transition: bool) -> None:
        pass

    def process(self, update: Update, context: CallbackContext) -> Optional['BaseState']:
        pass


class InteractiveState(BaseState):
    context: CallbackContext = None

    def react_on_message(self, message: Message) -> BaseState | None:
        pass

    def react_on_inline_keyboard(self, callback: CallbackQuery) -> BaseState | None:
        pass

    def process(self, update: Update, context: CallbackContext) -> BaseState | None:
        if not isinstance(update, Update):
            return

        self.context = context
        if update.message:
            return self.react_on_message(update.message)
        elif update.callback_query:
            return self.react_on_inline_keyboard(update.callback_query)