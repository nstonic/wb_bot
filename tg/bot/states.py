from contextlib import suppress
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, TelegramError
from telegram.ext import CallbackContext

from tg.bot.router import Router
from tg.bot.state_classes import InteractiveState, BaseState

router = Router()


def answer_to_user(
        update: Update,
        context: CallbackContext,
        text: str,
        keyboard: list[list[InlineKeyboardButton]] = None,
        add_main_menu_button: bool = True,
        parse_mode: str = 'HTML',
        edit_current_message: bool = True
):
    if not keyboard:
        keyboard = []

    if add_main_menu_button:
        keyboard.append([InlineKeyboardButton('Основное меню', callback_data='start')])

    if edit_current_message:
        try:
            message = context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=parse_mode
            )
        except TelegramError:
            pass
        else:
            return message

    with suppress(TelegramError):
        context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id
        )
    return context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=parse_mode
    )


@router.register('start')
class StartMenu(InteractiveState):

    def enter_state(self) -> Optional[BaseState]:
        text = 'Основное меню'
        keyboard = [
            [InlineKeyboardButton('Показать поставки', callback_data='show_supplies')],
            [InlineKeyboardButton('Новые заказы', callback_data='new_orders')],
            [InlineKeyboardButton('Заказы, ожидающие сортировки', callback_data='check_orders')]
        ]
        answer_to_user(
            update,
            context,
            text,
            keyboard,
            add_main_menu_button=False
        )
