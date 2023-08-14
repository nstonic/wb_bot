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
        self.answer_to_user(
            update,
            context,
            text=self.get_msg_text(state_data),
            keyboard=self.get_keyboard(state_data),
            **state_data
        )
        return Locator(self.state_name, params)

    def answer_to_user(
            self,
            update: Update,
            context: CallbackContext,
            text: str,
            keyboard: list[list[InlineKeyboardButton]] = None,
            **kwargs
    ):

        add_main_menu_button = kwargs.get('add_main_menu_button', True)
        parse_mode = kwargs.get('parse_mode', 'HTML')
        edit_current_message = kwargs.get('edit_current_message', True)

        if not keyboard:
            keyboard = []

        if add_main_menu_button:
            keyboard.append([InlineKeyboardButton('Основное меню', callback_data='start')])

        if edit_current_message:
            try:
                context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=update.effective_message.message_id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=parse_mode
                )
            except TelegramError:
                pass
            else:
                return

        with suppress(TelegramError):
            context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id
            )
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=parse_mode
        )

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
