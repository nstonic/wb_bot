from contextlib import suppress
from typing import NamedTuple, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, TelegramError
from telegram.ext import CallbackContext


class Locator(NamedTuple):
    state_name: str
    params: dict = dict()


class BaseState:

    def __init__(self, state_name: str):
        self.state_name = state_name

    def enter_state(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        pass

    def exit_state(self, update: Update, context: CallbackContext, **params) -> None:
        pass

    def process(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        pass


class TelegramBaseState(BaseState):
    def enter_state(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        state_data = self.get_state_data(**params)
        state_data.update(params)
        keyboard = self.get_keyboard(state_data) or []
        text = self.get_msg_text(state_data)

        if state_data.get('add_main_menu_button', True):
            keyboard.append([InlineKeyboardButton('Основное меню', callback_data='start')])

        parse_mode = state_data.get('parse_mode', 'HTML')

        try:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                parse_mode=parse_mode
            )
        except TelegramError:
            with suppress(TelegramError):
                context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.effective_message.message_id
                )
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                parse_mode=parse_mode
            )

        return Locator(self.state_name, params)

    def get_keyboard(self, state_data: dict) -> list[list[InlineKeyboardButton]]:
        pass

    def get_msg_text(self, state_data: dict) -> str:
        pass

    def get_state_data(self, **params) -> dict:
        return params

    def process(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        if update.message:
            return self.react_on_message(update, context, **params)
        elif update.callback_query:
            return self.react_on_inline_keyboard(update, context, **params)

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        pass

    def react_on_message(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        pass
