from collections import Counter
from contextlib import suppress
from typing import Optional

from django.conf import settings
from telegram import Update, InlineKeyboardButton
from telegram.ext import CallbackContext

from wb_api import WBApiClient
from .helpers import filter_supplies, SupplyFilter, send_supply_qr_code
from .state_machine import StateMachine
from .state_classes import Locator, TelegramBaseState
from .paginator import Paginator
from .stickers import get_orders_stickers

state_machine = StateMachine(start_state_name='MAIN_MENU')


@state_machine.register('MAIN_MENU')
class MainMenuState(TelegramBaseState):
    def get_state_data(self, **params) -> dict:
        return {'add_main_menu_button': False}

    def get_msg_text(self, state_data: dict) -> str:
        return 'Основное меню'

    def get_keyboard(self, state_data: dict) -> list[list[InlineKeyboardButton]]:
        return [
            [InlineKeyboardButton('Показать поставки', callback_data='show_supplies')],
            [InlineKeyboardButton('Новые заказы', callback_data='new_orders')],
            [InlineKeyboardButton('Заказы, ожидающие сортировки', callback_data='check_orders')]
        ]

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext, **params) -> Locator:
        query = update.callback_query.data
        match query:
            case 'show_supplies':
                return Locator('SUPPLIES')
            case 'new_orders':
                return Locator('NEW_ORDERS')
            case 'check_orders':
                return Locator('CHECK_WAITING_ORDERS')


@state_machine.register('NEW_ORDERS')
class NewOrdersState(TelegramBaseState):

    def get_state_data(self, **params) -> dict:
        wb_client = WBApiClient()
        new_orders = wb_client.get_new_orders()
        return {'new_orders': new_orders}

    def get_msg_text(self, state_data: dict) -> str:
        new_orders = state_data.get('new_orders')

        if new_orders:
            text = f'Новые заказы - {len(new_orders)} шт.'
        else:
            text = 'Нет новых заказов'

        return text

    def get_keyboard(self, state_data: dict) -> list[list[InlineKeyboardButton]]:
        new_orders = state_data.get('new_orders')

        if new_orders:
            sorted_orders = sorted(new_orders, key=lambda o: o.created_at)
            paginator = Paginator(
                sorted_orders,
                button_text_getter=lambda o: str(o),
                button_callback_data_getter=lambda o: str(o.id),
                page_size=settings.BOT_PAGINATOR_PAGE_SIZE
            )
            keyboard = paginator.get_keyboard(
                page_number=state_data.get('page_number', 1),
            )
            return keyboard

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        query = update.callback_query.data
        match query:
            case query if query.startswith('page'):
                params['page_number'] = int(query.split('#')[-1])
                return Locator(self.state_name, params)
            case 'start':
                return Locator('MAIN_MENU')
            case query if query.isdigit():
                order_params = {'order_id': int(query)}
                return Locator('ORDER_DETAILS', order_params)


@state_machine.register('SUPPLIES')
class SuppliesState(TelegramBaseState):

    def get_state_data(self, **params) -> dict:
        only_active = params.get('only_active', True)

        supplies = filter_supplies(SupplyFilter.ACTIVE if only_active else SupplyFilter.ALL)
        supplies.sort(key=lambda s: s.created_at, reverse=True)

        return {'supplies': supplies}

    def get_msg_text(self, state_data: dict) -> str:
        supplies = state_data['supplies']

        if supplies:
            text = 'Список поставок'
        else:
            text = 'У вас еще нет поставок. Создайте первую'

        return text

    def get_keyboard(self, state_data: dict) -> list[list[InlineKeyboardButton]]:
        supplies = state_data['supplies']
        only_active = state_data.get('only_active', True)
        page_number = state_data.get('page_number', 1)

        keyboard = [[InlineKeyboardButton('Создать новую поставку', callback_data='new_supply')]]

        if only_active:
            keyboard.insert(
                0,
                [InlineKeyboardButton('Показать закрытые поставки', callback_data='closed_supplies')]
            )

        if supplies:
            paginator = Paginator(
                supplies,
                button_text_getter=lambda s: str(s),
                button_callback_data_getter=lambda s: f'supply#{s.id}',
                page_size=settings.BOT_PAGINATOR_PAGE_SIZE,
            )
            paginator_keyboard = paginator.get_keyboard(page_number=page_number)
            keyboard = paginator_keyboard + keyboard

        return keyboard

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        query = update.callback_query.data
        match query:
            case 'closed_supplies':
                params['only_active'] = False
                return Locator(self.state_name, params)
            case query if query.startswith('page'):
                params['page_number'] = int(query.split('#')[-1])
                return Locator(self.state_name, params)
            case query if query.startswith('supply'):
                supply_params = {'supply_id': query.split('#')[-1]}
                return Locator('SUPPLY', supply_params)
            case 'new_supply':
                return Locator('NEW_SUPPLY')
            case 'start':
                return Locator('MAIN_MENU')


@state_machine.register('SUPPLY')
class SupplyState(TelegramBaseState):

    def get_state_data(self, **params) -> dict:
        supply_id = params.get('supply_id')

        if not supply_id:
            raise ValueError("Supply id is not defined")

        wb_client = WBApiClient()
        return {
            'supply': wb_client.get_supply(supply_id),
            'orders': wb_client.get_supply_orders(supply_id)
        }

    def get_msg_text(self, state_data: dict) -> str:
        if orders := state_data.get('orders'):
            articles = [order.article for order in orders]
            joined_orders = '\n'.join(
                [f'{article} - {count}шт.'
                 for article, count in Counter(sorted(articles)).items()]
            )
            supply = state_data.get('supply')
            text = f'Продукция в поставке {supply.name}:\n\n{joined_orders}'
        else:
            text = f'В поставке нет заказов'

        return text

    def get_keyboard(self, state_data: dict) -> list[list[InlineKeyboardButton]]:
        supply = state_data.get('supply')
        orders = state_data.get('orders')

        if not supply.is_done:
            if orders:
                keyboard = [
                    [InlineKeyboardButton('Создать стикеры', callback_data='stickers')],
                    [InlineKeyboardButton('Редактировать заказы', callback_data='edit')],
                    [InlineKeyboardButton('Отправить в доставку', callback_data='close')]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton('Удалить поставку', callback_data='delete')]
                ]
        else:
            keyboard = [
                [InlineKeyboardButton('Создать стикеры', callback_data='stickers')],
                [InlineKeyboardButton('QR-код поставки', callback_data='qr')]
            ]

        keyboard.append(
            [InlineKeyboardButton('Назад к списку поставок', callback_data='supplies')]
        )
        return keyboard

    def send_stickers(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        context.bot.answer_callback_query(
            update.callback_query.id,
            'Запущена подготовка стикеров. Подождите'
        )
        supply_id = params['supply_id']
        wb_client = WBApiClient()
        orders = wb_client.get_supply_orders(supply_id)
        order_qr_codes = wb_client.get_qr_codes_for_orders(
            [order.id for order in orders]
        )
        articles = set([order.article for order in orders])
        products = [wb_client.get_product(article) for article in articles]
        with get_orders_stickers(
                orders,
                products,
                order_qr_codes,
                supply_id
        ) as zip_file:
            context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=zip_file.getvalue(),
                filename=zip_file.name
            )
        return

    def close_supply(self, update: Update, context: CallbackContext, supply_id: str):
        wb_client = WBApiClient()
        if not wb_client.send_supply_to_deliver(supply_id):
            context.bot.answer_callback_query(
                update.callback_query.id,
                'Произошла ошибка. Попробуйте позже'
            )
        else:
            context.bot.answer_callback_query(
                update.callback_query.id,
                'Отправлено в доставку'
            )
            send_supply_qr_code(update, context, supply_id)

    def delete_supply(self, update: Update, context: CallbackContext, supply_id: str):
        wb_client = WBApiClient()
        if not wb_client.delete_supply_by_id(supply_id):
            context.bot.answer_callback_query(
                update.callback_query.id,
                'Произошла ошибка. Попробуйте позже'
            )
        else:
            context.bot.answer_callback_query(
                update.callback_query.id,
                'Поставка удалена'
            )
        return Locator('SUPPLIES')

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        query = update.callback_query.data
        match query:
            case 'stickers':
                self.send_stickers(update, context, **params)
            case 'edit':
                return Locator('EDIT_SUPPLY', params)
            case 'close':
                self.close_supply(update, context, params['supply_id'])
                return Locator(self.state_name, params)
            case 'delete':
                return self.delete_supply(update, context, params['supply_id'])
            case 'qr':
                send_supply_qr_code(update, context, params['supply_id'])
            case 'supplies':
                return Locator('SUPPLIES')
            case 'start':
                return Locator('MAIN_MENU')


@state_machine.register('NEW_SUPPLY')
class NewSupplyState(TelegramBaseState):
    def get_msg_text(self, state_data: dict) -> str:
        return 'Пришлите название для новой поставки'

    def get_keyboard(self, state_data: dict) -> list[list[InlineKeyboardButton]]:
        return [[InlineKeyboardButton('Назад к списку поставок', callback_data='cancel')]]

    def react_on_message(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        wb_client = WBApiClient()
        new_supply_name = update.message.text
        wb_client.create_new_supply(new_supply_name)
        return Locator('SUPPLIES')

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        query = update.callback_query.data
        match query:
            case 'cancel':
                return Locator('SUPPLIES')
            case 'start':
                return Locator('MAIN_MENU')


@state_machine.register('EDIT_SUPPLY')
class EditSupplyState(TelegramBaseState):
    def enter_state(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        wb_client = WBApiClient()
        orders = wb_client.get_supply_orders(params['supply_id'])
        order_ids = {order.id for order in orders}
        keyboard = [[InlineKeyboardButton('Вернуться к поставке', callback_data='supply')]]

        if orders:
            if params.get('order_ids') == order_ids:
                qr_codes = params['qr_codes']
            else:
                context.bot.answer_callback_query(
                    update.callback_query.id,
                    'Загружаются данные по заказам. Подождите'
                )
                sorted_orders = sorted(orders, key=lambda o: o.created_at)
                qr_codes = wb_client.get_qr_codes_for_orders([order.id for order in sorted_orders])
                params['order_ids'] = order_ids
                params['qr_codes'] = qr_codes

            def button_text_getter(order):
                with suppress(StopIteration):
                    qr_code = next(filter(
                        lambda qr: qr.order_id == order.id,
                        qr_codes
                    ))
                    return f'{order.article} | {qr_code.part_a} {qr_code.part_b}'
                return order.article

            paginator = Paginator(
                orders,
                button_text_getter=button_text_getter,
                button_callback_data_getter=lambda o: o.id,
                page_size=settings.BOT_PAGINATOR_PAGE_SIZE
            )
            paginator_keyboard = paginator.get_keyboard(
                page_number=params.get('page_number', 1),
            )
            keyboard = paginator_keyboard + keyboard
            text = f'Заказы в поставке - всего {len(orders)}шт'
        else:
            text = 'В поставке нет заказов'

        self.answer_to_user(
            update,
            context,
            text,
            keyboard,
            edit_current_message=True
        )

        return Locator(self.state_name, params)

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        query = update.callback_query.data
        match query:
            case query if query.isdigit():
                order_params = {
                    'supply_id': params['supply_id'],
                    'order_id': int(query)
                }
                return Locator('ORDER_DETAILS', order_params)
            case query if query.startswith('page'):
                params['page_number'] = int(query.split('#')[-1])
                return Locator(self.state_name, params)
            case 'supply':
                supply_params = {'supply_id': params['supply_id']}
                return Locator('SUPPLY', supply_params)
            case 'start':
                return Locator('MAIN_MENU')


@state_machine.register('CHECK_WAITING_ORDERS')
class CheckWaitingOrdersState(TelegramBaseState):
    def get_state_data(self, **params) -> dict:
        supplies = filter_supplies(SupplyFilter.CLOSED)[::-1]

        wb_client = WBApiClient()
        orders = []
        for supply in supplies[:10]:
            orders.extend(
                wb_client.get_supply_orders(supply.id)
            )

        order_statuses = wb_client.check_orders_status(
            [order.id for order in orders]
        )

        waiting_order_ids = [
            status.id
            for status in order_statuses
            if status.wb_status == 'waiting'
        ]

        waiting_orders = list(filter(
            lambda o: o.id in waiting_order_ids,
            orders
        ))

        return {'waiting_orders': waiting_orders}

    def get_msg_text(self, state_data: dict) -> str:
        if state_data['waiting_orders']:
            waiting_orders_articles = [
                f'{order.supply_id} | {order}'
                for order in state_data['waiting_orders']
            ]
            text = '\n'.join(waiting_orders_articles)
        else:
            text = 'Нет заказов, ожидающих сортировки'
        return text

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        query = update.callback_query.data
        match query:
            case 'start':
                return Locator('MAIN_MENU')


@state_machine.register('ORDER_DETAILS')
class OrderDetailsState(TelegramBaseState):
    def get_state_data(self, **params) -> dict | None:
        order_id = params['order_id']
        supply_id = params.get('supply_id')
        wb_client = WBApiClient()

        if supply_id:
            for order in wb_client.get_supply_orders(supply_id):
                if order.id == order_id:
                    return {
                        'supply_id': supply_id,
                        'order': order,
                        'order_qr_code': wb_client.get_qr_codes_for_orders([order.id])[-1]
                    }
        else:
            for order in wb_client.get_new_orders():
                if order.id == order_id:
                    return {'order': order}

    def get_keyboard(self, state_data: dict) -> list[list[InlineKeyboardButton]]:
        keyboard = [
            [InlineKeyboardButton('Перенести в поставку', callback_data='add_to_supply')]
        ]

        if state_data.get('supply_id'):
            keyboard.append([InlineKeyboardButton('Вернуться к поставке', callback_data='supply')])

        return keyboard

    def get_msg_text(self, state_data: dict) -> str:
        order = state_data['order']

        if supply_id := state_data.get('supply_id'):
            order_qr_code = state_data['order_qr_code']
            text = f'Номер заказа: <b>{order.id}</b>\n' \
                   f'Стикер: <b>{order_qr_code.part_a} {order_qr_code.part_b}</b>\n' \
                   f'Артикул: <b>{order.article}</b>\n' \
                   f'Поставка: <b>{supply_id}</b>\n' \
                   f'Время с момента заказа: <b>{order.created_ago}</b>\n' \
                   f'Цена: <b>{order.converted_price / 100} ₽</b>'
        else:
            text = f'Номер заказа: <b>{order.id}</b>\n' \
                   f'Артикул: <b>{order.article}</b>\n' \
                   f'Время с момента заказа: <b>{order.created_ago}</b>\n' \
                   f'Цена: <b>{order.converted_price / 100} ₽</b>'

        return text

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext, **params) -> Optional[Locator]:
        query = update.callback_query.data
        match query:
            case 'supply':
                return Locator('SUPPLY', {'supply_id': params['supply_id']})
            case 'add_to_supply':
                params = {
                    'supply_id': params['supply_id'],
                    'order_id': params['order'].id
                }
                return Locator('ADD_ORDER_TO_SUPPLY', params)  # TODO ADD_ORDER_TO_SUPPLY STATE
            case 'start':
                return Locator('MAIN_MENU')
