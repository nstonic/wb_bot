from typing import Optional

from telegram import Update, InlineKeyboardButton
from telegram.ext import CallbackContext

from wb_api import WBApiClient
from .handlers import answer_to_user
from .state_machine import BaseState, StateMachine

state_machine = StateMachine(start_state_locator='MAIN_MENU')


@state_machine.register('MAIN_MENU')
class MainMenu(BaseState):
    def enter_state(self, update: Update, context: CallbackContext) -> None:
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

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext) -> Optional[str]:
        query = update.callback_query.data
        actions = {
            'show_supplies': 'SHOW_SUPPLIES',
            'new_orders': 'NEW_ORDERS',
            'check_orders': 'CHECK_ORDERS'
        }
        return actions.get(query)


@state_machine.register('NEW_ORDERS')
class NewOrders(BaseState):

    def enter_state(self, update: Update, context: CallbackContext) -> None:
        wb_client = WBApiClient()
        new_orders = wb_client.get_new_orders()

        if new_orders:
            sorted_orders = sorted(new_orders, key=lambda o: o.created_at)
            keyboard = [
                [InlineKeyboardButton(str(order), callback_data=order.id)]
                for order in sorted_orders
            ]
            text = 'Новые заказы'
        else:
            keyboard = None
            text = 'Нет новых заказов'

        answer_to_user(
            update,
            context,
            text,
            keyboard,
            edit_current_message=True
        )

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext) -> Optional[str]:
        query = update.callback_query.data
        context.user_data['order_id'] = int(query)
        return 'SHOW_NEW_ORDERS_DETAILS'
