from collections import Counter
from contextlib import suppress

from django.conf import settings
from telegram import Update, InlineKeyboardButton  # noqa
from telegram.ext import CallbackContext  # noqa

from wb.wb_api import WBApiClient
from wb.wb_api.helpers import filter_supplies, SupplyFilter
from .helpers import send_stickers_job
from .state_machine import StateMachine
from .state_classes import Locator, EditMessageBaseState
from .paginator import Paginator
from .stickers import get_supply_sticker

state_machine = StateMachine(start_state_name='MAIN_MENU')
_MAIN_MENU_INLINE_BUTTON = [InlineKeyboardButton('Основное меню', callback_data='start')]


@state_machine.register('MAIN_MENU')
class MainMenuState(EditMessageBaseState):
    msg_text = 'Основное меню'
    inline_keyboard = [
        [InlineKeyboardButton('Показать поставки', callback_data='show_supplies')],
        [InlineKeyboardButton('Новые заказы', callback_data='new_orders')],
        [InlineKeyboardButton('Заказы, ожидающие сортировки', callback_data='check_orders')]
    ]

    def react_on_inline_keyboard(self) -> Locator:
        query = self.update.callback_query.data
        match query:
            case 'show_supplies':
                return Locator('SUPPLIES')
            case 'new_orders':
                return Locator('NEW_ORDERS')
            case 'check_orders':
                return Locator('CHECK_WAITING_ORDERS')


@state_machine.register('NEW_ORDERS')
class NewOrdersState(EditMessageBaseState):

    def get_state_data(self, **params) -> dict:
        wb_client = WBApiClient()
        new_orders = wb_client.get_new_orders()
        return {'new_orders': new_orders}

    def get_msg_text(self) -> str:
        new_orders = self.state_data.get('new_orders')

        if new_orders:
            text = f'Новые заказы - {len(new_orders)} шт.'
        else:
            text = 'Нет новых заказов'

        return text

    def get_inline_keyboard(self) -> list[list[InlineKeyboardButton]]:
        new_orders = self.state_data.get('new_orders')
        keyboard = []
        if new_orders:
            sorted_orders = sorted(new_orders, key=lambda o: o.created_at)
            paginator = Paginator(
                sorted_orders,
                button_text_getter=lambda o: str(o),
                button_callback_data_getter=lambda o: str(o.id),
                page_size=settings.BOT_PAGINATOR_PAGE_SIZE
            )
            keyboard.append(paginator.get_keyboard(
                page_number=self.state_data.get('page_number', 1),
            ))
        keyboard.append(_MAIN_MENU_INLINE_BUTTON)
        return keyboard

    def react_on_inline_keyboard(self) -> Locator | None:
        query = self.update.callback_query.data
        match query:
            case query if query.startswith('page'):
                self.state_data['page_number'] = int(query.split('#')[-1])
                return Locator(self.state_name, self.state_data)
            case 'start':
                return Locator('MAIN_MENU')
            case query if query.isdigit():
                order_params = {'order_id': int(query)}
                return Locator('ORDER_DETAILS', order_params)


@state_machine.register('SUPPLIES')
class SuppliesState(EditMessageBaseState):

    def get_state_data(self, **params) -> dict:
        only_active = params.get('only_active', True)

        supplies = filter_supplies(SupplyFilter.ACTIVE if only_active else SupplyFilter.ALL)
        supplies.sort(key=lambda s: s.created_at, reverse=True)

        return {'supplies': supplies}

    def get_msg_text(self) -> str:
        supplies = self.state_data['supplies']

        if supplies:
            text = 'Список поставок'
        else:
            text = 'У вас еще нет поставок. Создайте первую'

        return text

    def get_inline_keyboard(self) -> list[list[InlineKeyboardButton]]:
        supplies = self.state_data['supplies']
        only_active = self.state_data.get('only_active', True)
        page_number = self.state_data.get('page_number', 1)

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

        keyboard.append(_MAIN_MENU_INLINE_BUTTON)
        return keyboard

    def react_on_inline_keyboard(self) -> Locator | None:
        query = self.update.callback_query.data
        match query:
            case 'closed_supplies':
                self.state_data['only_active'] = False
                return Locator(self.state_name, self.state_data)
            case query if query.startswith('page'):
                self.state_data['page_number'] = int(query.split('#')[-1])
                return Locator(self.state_name, self.state_data)
            case query if query.startswith('supply'):
                supply_params = {'supply_id': query.split('#')[-1]}
                return Locator('SUPPLY', supply_params)
            case 'new_supply':
                return Locator('NEW_SUPPLY')
            case 'start':
                return Locator('MAIN_MENU')


@state_machine.register('SUPPLY')
class SupplyState(EditMessageBaseState):

    def get_state_data(self, **params) -> dict:
        supply_id = params['supply_id']

        wb_client = WBApiClient()
        return {
            'supply': wb_client.get_supply(supply_id),
            'orders': wb_client.get_supply_orders(supply_id)
        }

    def get_msg_text(self) -> str:
        supply = self.state_data.get('supply')

        if orders := self.state_data.get('orders'):
            articles = [order.article for order in orders]
            joined_orders = '\n'.join(
                [f'{article} - {count}шт.'
                 for article, count in Counter(sorted(articles)).items()]
            )
            text = f'Продукция в поставке {supply.name}:\n\n{joined_orders}'
        else:
            text = f'В поставке {supply.name} нет заказов'

        return text

    def get_inline_keyboard(self) -> list[list[InlineKeyboardButton]]:
        supply = self.state_data.get('supply')
        orders = self.state_data.get('orders')

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

        keyboard.extend([
            [InlineKeyboardButton('Назад к списку поставок', callback_data='supplies')],
            _MAIN_MENU_INLINE_BUTTON
        ])
        return keyboard

    def send_stickers(self) -> Locator | None:
        self.context.bot.answer_callback_query(
            self.update.callback_query.id,
            'Запущена подготовка стикеров'
        )
        job_context = {
            'chat_id': self.update.effective_chat.id,
            'supply_id': self.state_data['supply_id'],
        }
        self.context.job_queue.run_once(send_stickers_job, when=0, context=job_context)

    def close_supply(self):
        wb_client = WBApiClient()
        if not wb_client.send_supply_to_deliver(self.state_data['supply_id']):
            self.context.bot.answer_callback_query(
                self.update.callback_query.id,
                'Произошла ошибка. Попробуйте позже'
            )
        else:
            self.context.bot.answer_callback_query(
                self.update.callback_query.id,
                'Отправлено в доставку'
            )
            self.send_supply_qr_code()

    def delete_supply(self):
        wb_client = WBApiClient()
        if not wb_client.delete_supply_by_id(self.state_data['supply_id']):
            self.context.bot.answer_callback_query(
                self.update.callback_query.id,
                'Произошла ошибка. Попробуйте позже'
            )
        else:
            self.context.bot.answer_callback_query(
                self.update.callback_query.id,
                'Поставка удалена'
            )
        return Locator('SUPPLIES')

    def send_supply_qr_code(self):
        wb_client = WBApiClient()
        supply_qr_code = wb_client.get_supply_qr_code(self.state_data['supply_id'])
        supply_sticker = get_supply_sticker(supply_qr_code)
        self.context.bot.send_photo(
            chat_id=self.update.effective_chat.id,
            photo=supply_sticker
        )

    def react_on_inline_keyboard(self) -> Locator | None:
        query = self.update.callback_query.data
        match query:
            case 'stickers':
                self.send_stickers()
            case 'edit':
                return Locator('EDIT_SUPPLY', self.state_data)
            case 'close':
                self.close_supply()
                return Locator(self.state_name, self.state_data)
            case 'delete':
                return self.delete_supply()
            case 'qr':
                self.send_supply_qr_code()
            case 'supplies':
                return Locator('SUPPLIES')
            case 'start':
                return Locator('MAIN_MENU')


@state_machine.register('NEW_SUPPLY')
class NewSupplyState(EditMessageBaseState):
    msg_text = 'Пришлите название для новой поставки'
    inline_keyboard = [
        [InlineKeyboardButton('Назад к списку поставок', callback_data='cancel')],
        _MAIN_MENU_INLINE_BUTTON
    ]

    def react_on_message(self) -> Locator | None:
        wb_client = WBApiClient()
        new_supply_name = self.update.message.text
        wb_client.create_new_supply(new_supply_name)
        return Locator('SUPPLIES')

    def react_on_inline_keyboard(self) -> Locator | None:
        query = self.update.callback_query.data
        match query:
            case 'cancel':
                return Locator('SUPPLIES')
            case 'start':
                return Locator('MAIN_MENU')


@state_machine.register('EDIT_SUPPLY')
class EditSupplyState(EditMessageBaseState):

    def get_state_data(self, **params) -> dict:
        wb_client = WBApiClient()
        orders = wb_client.get_supply_orders(params['supply_id'])
        order_ids = {order.id for order in orders}

        if params.get('order_ids') == order_ids:
            qr_codes = params['qr_codes']
        else:
            self.context.bot.answer_callback_query(
                self.update.callback_query.id,
                'Загружаются данные по заказам. Подождите'
            )
            sorted_orders = sorted(orders, key=lambda o: o.created_at)
            qr_codes = wb_client.get_qr_codes_for_orders([order.id for order in sorted_orders])

        params['order_ids'] = order_ids
        params['qr_codes'] = qr_codes

        return params

    def get_msg_text(self) -> str:
        orders = self.state_data['orders']
        if orders:
            return f'Заказы в поставке - всего {len(orders)}шт'
        else:
            return 'В поставке нет заказов'

    def get_inline_keyboard(self) -> list[list[InlineKeyboardButton]]:
        orders = self.state_data['orders']
        qr_codes = self.state_data['qr_codes']
        page_number = self.state_data.get('page_number', 1)

        keyboard = [[InlineKeyboardButton('Вернуться к поставке', callback_data='supply')]]

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
        paginator_keyboard = paginator.get_keyboard(page_number=page_number, )
        inline_keyboard = paginator_keyboard + keyboard + [_MAIN_MENU_INLINE_BUTTON]

        return inline_keyboard

    def react_on_inline_keyboard(self) -> Locator | None:
        query = self.update.callback_query.data
        match query:
            case query if query.isdigit():
                order_params = {
                    'supply_id': self.state_data['supply_id'],
                    'order_id': int(query)
                }
                return Locator('ORDER_DETAILS', order_params)
            case query if query.startswith('page'):
                self.state_data['page_number'] = int(query.split('#')[-1])
                return Locator(self.state_name, self.state_data)
            case 'supply':
                supply_params = {'supply_id': self.state_data['supply_id']}
                return Locator('SUPPLY', supply_params)
            case 'start':
                return Locator('MAIN_MENU')


@state_machine.register('CHECK_WAITING_ORDERS')
class CheckWaitingOrdersState(EditMessageBaseState):
    inline_keyboard = [_MAIN_MENU_INLINE_BUTTON]

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

    def get_msg_text(self) -> str:
        if self.state_data['waiting_orders']:
            waiting_orders_articles = [
                f'{order.supply_id} | {order}'
                for order in self.state_data['waiting_orders']
            ]
            text = '\n'.join(waiting_orders_articles)
        else:
            text = 'Нет заказов, ожидающих сортировки'
        return text

    def react_on_inline_keyboard(self) -> Locator | None:
        return Locator('MAIN_MENU')


@state_machine.register('ORDER_DETAILS')
class OrderDetailsState(EditMessageBaseState):
    message_sending_params = {'parse_mode': 'HTML'}

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

    def get_inline_keyboard(self) -> list[list[InlineKeyboardButton]]:
        keyboard = [
            [InlineKeyboardButton('Перенести в поставку', callback_data='add_to_supply')]
        ]

        if self.state_data.get('supply_id'):
            keyboard.append(
                [InlineKeyboardButton('Вернуться к поставке', callback_data='supply')],
            )

        return keyboard + [_MAIN_MENU_INLINE_BUTTON]

    def get_msg_text(self) -> str:
        order = self.state_data['order']

        if supply_id := self.state_data.get('supply_id'):
            order_qr_code = self.state_data['order_qr_code']
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

    def react_on_inline_keyboard(self) -> Locator | None:
        query = self.update.callback_query.data
        match query:
            case 'supply':
                return Locator('SUPPLY', {'supply_id': self.state_data['supply_id']})
            case 'add_to_supply':
                return Locator('ADD_ORDER_TO_SUPPLY', {'order_id': self.state_data['order_id']})
            case 'start':
                return Locator('MAIN_MENU')


@state_machine.register('ADD_ORDER_TO_SUPPLY')
class AddOrderToSupplyState(EditMessageBaseState):
    msg_text = 'Выберите поставку из существующих либо сообщением пришлите название новой поставки'

    def get_state_data(self, **params) -> dict | None:
        active_supplies = filter_supplies(SupplyFilter.ACTIVE)
        return {'supplies': active_supplies}

    def get_inline_keyboard(self) -> list[list[InlineKeyboardButton]]:
        keyboard = [
            [InlineKeyboardButton(str(supply), callback_data=supply.id)]
            for supply in self.state_data['supplies']
        ]
        keyboard.append(_MAIN_MENU_INLINE_BUTTON)
        return keyboard

    def add_to_supply(self, supply_id: str):
        order_id = self.state_data['order_id']
        wb_client = WBApiClient()
        if wb_client.add_order_to_supply(supply_id, order_id):
            if self.update.callback_query:
                self.context.bot.answer_callback_query(
                    self.update.callback_query.id,
                    f'Заказ {order_id} добавлен к поставке {supply_id}'
                )
        else:
            if self.update.callback_query:
                self.context.bot.answer_callback_query(
                    self.update.callback_query.id,
                    'Произошла ошибка. Попробуйте позже'
                )

    def react_on_message(self) -> Locator | None:
        wb_client = WBApiClient()
        new_supply_name = self.update.message.text
        supply_id = wb_client.create_new_supply(new_supply_name)
        self.add_to_supply(supply_id)
        return Locator('SUPPLY', {'supply_id': supply_id})

    def react_on_inline_keyboard(self) -> Locator | None:
        query = self.update.callback_query.data
        match query:
            case 'start':
                return Locator('MAIN_MENU')
            case _:
                self.add_to_supply(query)
                return Locator('SUPPLY', {'supply_id': query})
