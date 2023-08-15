from contextlib import suppress
from typing import NamedTuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, TelegramError
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

    def __init__(self, state_name: str):
        self.state_data = {}
        self.msg_text: str | None = None
        self.keyboard: list[list[InlineKeyboardButton]] | None = None
        self.update: Update | None = None
        self.context: CallbackContext | None = None
        super().__init__(state_name)

    def enter_state(self, update: Update, context: CallbackContext, **params) -> Locator | None:
        self.state_data = params | self.get_state_data(**params)
        self.msg_text = self.get_msg_text()
        self.keyboard = self.get_keyboard()
        self.answer_to_user()
        return Locator(self.state_name, self.state_data)

    def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        pass

    def get_msg_text(self) -> str:
        pass

    def get_state_data(self, **params) -> dict:
        return params

    def process(self, update: Update, context: CallbackContext, **params) -> Locator | None:
        self.state_data = params
        self.update = update
        self.context = CallbackContext
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
            add_main_menu_button: bool = True,
            parse_mode: str = 'HTML',
            edit_current_message: bool = True
    ):
        text = self.msg_text or ' '
        keyboard = self.keyboard or []

        if add_main_menu_button:
            keyboard.append([InlineKeyboardButton('Основное меню', callback_data='start')])

        if edit_current_message:
            try:
                self.context.bot.edit_message_text(
                    chat_id=self.update.effective_chat.id,
                    message_id=self.update.effective_message.message_id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
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
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=parse_mode
        )
