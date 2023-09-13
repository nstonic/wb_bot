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


class ClassicState(BaseState):
    msg_text: str | None = None
    inline_keyboard: list[list[InlineKeyboardButton]] | None = None
    keyboard: list[list[KeyboardButton]] | None = None

    def __init__(self, state_name: str):
        super().__init__(state_name)
        self.state_data = {}
        self.update: Update | None = None
        self.context: CallbackContext | None = None
        self.message_sending_params = {}

    def enter_state(self, update: Update, context: CallbackContext, **params) -> Locator | None:
        self.update = update
        self.context = context
        self.state_data = params | self.get_state_data(**params)
        self.msg_text = self.get_msg_text()
        self.inline_keyboard = self.get_inline_keyboard()
        self.keyboard = self.get_keyboard()
        self.answer_user()
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

    def get_markup(self):
        keyboard = self.inline_keyboard or self.keyboard or []

        match keyboard:
            case keyboard if isinstance(keyboard[0][0], InlineKeyboardButton):
                reply_markup = InlineKeyboardMarkup(keyboard)
            case keyboard if isinstance(keyboard[0][0], KeyboardButton):
                reply_markup = ReplyKeyboardMarkup(keyboard)
            case _:
                reply_markup = None

        return reply_markup

    def answer_user(self):
        self.context.bot.send_message(
            chat_id=self.update.effective_chat.id,
            text=self.msg_text or ' ',
            reply_markup=self.get_markup(),
            **self.message_sending_params,
        )


class TelegramBaseState(ClassicState):

    def answer_user(self, edit_current_message: bool = True):
        text = self.msg_text or ' '
        reply_markup = self.get_markup()

        if edit_current_message:
            try:
                self.context.bot.edit_message_text(
                    chat_id=self.update.effective_chat.id,
                    message_id=self.update.effective_message.message_id,
                    text=text,
                    reply_markup=reply_markup,
                    **self.message_sending_params
                )
            except TelegramError as ex:
                if 'Message is not modified' in str(ex):
                    if self.update.callback_query:
                        with suppress(TelegramError):
                            self.context.bot.answer_callback_query(
                                self.update.callback_query.id,
                                ''
                            )
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
            **self.message_sending_params,
        )
