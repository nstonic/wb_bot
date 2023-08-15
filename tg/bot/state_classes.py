from contextlib import suppress
from typing import NamedTuple

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    TelegramError,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import CallbackContext


class Locator(NamedTuple):
    state_name: str
    params: dict = dict()


class BaseState:

    def __init__(self, state_name: str):
        self.state_name = state_name

    def enter_state(self, update: Update, context: CallbackContext, **params) -> Locator | None:
        pass

    def exit_state(self, update: Update, context: CallbackContext, **params) -> None:
        pass

    def process(self, update: Update, context: CallbackContext, **params) -> Locator | None:
        pass


class TelegramBaseState(BaseState):
    msg_text: str | None = None
    inline_keyboard: list[list[InlineKeyboardButton]] | None = None
    keyboard: list[list[KeyboardButton]] | None = None

    def __init__(self, state_name: str):
        self.state_data = {}
        self.update: Update | None = None
        self.context: CallbackContext | None = None
        super().__init__(state_name)

    def enter_state(self, update: Update, context: CallbackContext, **params) -> Locator | None:
        self.update = update
        self.context = context
        self.state_data = params | self.get_state_data(**params)
        self.msg_text = self.get_msg_text()
        self.inline_keyboard = self.get_inline_keyboard()
        self.keyboard = self.get_keyboard()
        self.answer_to_user()
        return Locator(self.state_name, self.state_data)

    def get_inline_keyboard(self) -> list[list[InlineKeyboardButton]]:
        return self.inline_keyboard

    def get_keyboard(self) -> list[list[KeyboardButton]]:
        return self.keyboard

    def get_msg_text(self) -> str:
        return self.msg_text

    def get_state_data(self, **params) -> dict:
        return params

    def process(self, update: Update, context: CallbackContext, **params) -> Locator | None:
        self.state_data = params
        self.update = update
        self.context = context
        if update.message:
            return self.react_on_message()
        elif update.callback_query:
            return self.react_on_inline_keyboard()

    def react_on_inline_keyboard(self) -> Locator | None:
        pass

    def react_on_message(self) -> Locator | None:
        pass

    def answer_to_user(
            self,
            parse_mode: str = 'HTML',
            edit_current_message: bool = True
    ):
        parse_mode = self.state_data.get('parse_mode', parse_mode)
        edit_current_message = self.state_data.get('edit_current_message', edit_current_message)

        text = self.msg_text or ' '
        keyboard = self.inline_keyboard or self.keyboard or []

        if not keyboard:
            reply_markup = None
        else:
            if isinstance(keyboard[0][0], InlineKeyboardButton):
                reply_markup = InlineKeyboardMarkup(keyboard)
            elif isinstance(keyboard[0][0], KeyboardButton):
                reply_markup = ReplyKeyboardMarkup(keyboard)
            else:
                reply_markup = None

        if edit_current_message:
            try:
                self.context.bot.edit_message_text(
                    chat_id=self.update.effective_chat.id,
                    message_id=self.update.effective_message.message_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except TelegramError as ex:
                if 'Message is not modified' in str(ex):
                    return
            else:
                return

        with suppress(TelegramError):
            self.context.bot.delete_message(
                chat_id=self.update.effective_chat.id,
                message_id=self.update.effective_message.message_id
            )
        self.context.bot.send_message(
            chat_id=self.update.effective_chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
