from collections import Counter
from contextlib import suppress

from django.conf import settings
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, TelegramError  # noqa
from telegram.ext import CallbackContext  # noqa

from .stickers import get_supply_sticker, get_orders_stickers
from .utils import PaginatorItem, Paginator
from ..models import Supply
from wb_api import WBApiClient, SupplyFilter

_MAIN_MENU_BUTTON = InlineKeyboardButton('Основное меню', callback_data='start')
_SUPPLIES_QUANTITY = settings.SUPPLIES_QUANTITY
_PAGE_SIZE = settings.PAGINATOR_PAGE_SIZE


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
        keyboard.append([_MAIN_MENU_BUTTON])

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


def show_start_menu(update: Update, context: CallbackContext):
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
    return 'HANDLE_MAIN_MENU'


def show_supplies(
        update: Update,
        context: CallbackContext,
        page_number: int = 0,
        quantity: int = _SUPPLIES_QUANTITY,
        page_size: int = _PAGE_SIZE,
        only_active: bool = True
):
    wb_client = WBApiClient()
    supply_filter = SupplyFilter.ACTIVE if only_active else SupplyFilter.ALL
    supplies = list(filter(  # noqa
        supply_filter,
        wb_client.get_supplies(quantity=quantity)
    ))
    for supply in supplies:
        Supply.objects.update_or_create(
            id=supply.id,
            name=supply.name,
            closed_at=supply.closed_at,
            created_at=supply.created_at,
            is_open=not supply.is_done
        )

    keyboard = [[InlineKeyboardButton('Создать новую поставку', callback_data='new_supply')]]
    if only_active:
        keyboard.insert(
            0,
            [InlineKeyboardButton('Показать закрытые поставки', callback_data='closed_supplies')]
        )
    if supplies:
        paginator_items = [
            PaginatorItem(
                callback_data=supply.id,
                button_text=str(supply)
            )
            for supply in supplies
        ]
        paginator = Paginator(paginator_items, page_size)
        paginator_keyboard = paginator.get_keyboard(
            page_number=page_number,
            callback_data_prefix='supply_',
            page_callback_data_postfix=f'_{only_active}',
            main_menu_button=_MAIN_MENU_BUTTON
        )
        keyboard = paginator_keyboard + keyboard
        add_main_menu_button = False
        text = 'Список поставок'
        if paginator.is_paginated:
            text = f'{text}\n(стр. {page_number + 1})'
    else:
        text = 'У вас еще нет поставок. Создайте первую'
        add_main_menu_button = True
    answer_to_user(
        update,
        context,
        text,
        keyboard,
        add_main_menu_button=add_main_menu_button,
        edit_current_message=True
    )
    return 'HANDLE_SUPPLIES_MENU'


def show_new_orders(
        update: Update,
        context: CallbackContext,
        page_number: int = 0,
        page_size: int = _PAGE_SIZE
):
    wb_client = WBApiClient()
    new_orders = wb_client.get_new_orders()
    if new_orders:
        sorted_orders = sorted(new_orders, key=lambda o: o.created_at)
        paginator_items = [
            PaginatorItem(
                callback_data=str(order.id),
                button_text=str(order)
            )
            for order in sorted_orders
        ]

        paginator = Paginator(paginator_items, page_size)
        keyboard = paginator.get_keyboard(
            page_number=page_number,
            main_menu_button=_MAIN_MENU_BUTTON,
        )
        add_main_menu_button = False
        page_info = f' (стр. {page_number + 1})' if paginator.is_paginated else ''
        text = f'Новые заказы{page_info}:\n' \
               f'Всего {paginator.items_count}шт\n' \
               f'(Артикул | Время с момента заказа)'
    else:
        keyboard = None
        add_main_menu_button = True
        text = 'Нет новых заказов'
    answer_to_user(
        update,
        context,
        text,
        keyboard,
        add_main_menu_button=add_main_menu_button,
        edit_current_message=True
    )
    return 'HANDLE_NEW_ORDERS'


def show_supply(update: Update, context: CallbackContext, supply_id: str):
    wb_client = WBApiClient()
    supply = Supply.objects.get(id=supply_id)
    orders = wb_client.get_supply_orders(supply_id)

    if not supply.is_done:
        if orders:
            keyboard = [
                [InlineKeyboardButton('Создать стикеры', callback_data=f'stickers_{supply_id}')],
                [InlineKeyboardButton('Редактировать заказы', callback_data=f'edit_{supply_id}')],
                [InlineKeyboardButton('Отправить в доставку', callback_data=f'close_{supply_id}')]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton('Удалить поставку', callback_data=f'delete_{supply_id}')]
            ]
    else:
        keyboard = [
            [InlineKeyboardButton('Создать стикеры', callback_data=f'stickers_{supply_id}')],
            [InlineKeyboardButton('QR-код поставки', callback_data=f'qr_{supply_id}')]
        ]

    if orders:
        articles = [order.article for order in orders]
        joined_orders = '\n'.join(
            [f'{article} - {count}шт.'
             for article, count in Counter(sorted(articles)).items()]
        )
        text = f'Заказы по поставке {supply.name}:\n\n{joined_orders}'
    else:
        text = f'В поставке нет заказов'

    keyboard.append(
        [InlineKeyboardButton('Назад к списку поставок', callback_data='show_supplies')]
    )
    answer_to_user(
        update,
        context,
        text,
        keyboard
    )
    return 'HANDLE_SUPPLY'


def edit_supply(
        update: Update,
        context: CallbackContext,
        supply_id: str,
        page_number: int = 0,
        page_size: int = _PAGE_SIZE
):
    wb_client = WBApiClient()
    keyboard = [[InlineKeyboardButton('Вернуться к поставке', callback_data=f'supply_{supply_id}')]]

    orders = wb_client.get_supply_orders(supply_id)
    order_ids = {order.id for order in orders}
    if orders:
        sorted_orders = sorted(orders, key=lambda o: o.created_at)
        if context.user_data.get('order_ids') == order_ids:
            qr_codes = context.user_data.get('qr_codes')
        else:
            context.bot.answer_callback_query(
                update.callback_query.id,
                'Загружаются данные по заказам. Подождите'
            )
            qr_codes = wb_client.get_qr_codes_for_orders([order.id for order in sorted_orders])
            context.user_data['order_ids'] = order_ids
            context.user_data['qr_codes'] = qr_codes
            context.user_data['current_supply'] = supply_id
        paginator_items = []
        for order in sorted_orders:
            with suppress(StopIteration):
                qr_code = next(filter(
                    lambda qr: qr.order_id == order.id,
                    qr_codes
                ))
                paginator_items.append(
                    PaginatorItem(
                        callback_data=str(order.id),
                        button_text=f'{order.article} | {qr_code.part_a} {qr_code.part_b}'
                    )
                )

        paginator = Paginator(paginator_items, page_size)
        paginator_keyboard = paginator.get_keyboard(
            page_number=page_number,
            callback_data_prefix=f'{supply_id}_',
            page_callback_data_postfix=f' supply_{supply_id}',
            main_menu_button=_MAIN_MENU_BUTTON
        )
        keyboard = paginator_keyboard + keyboard
        add_main_menu_button = False
        page_info = f' (стр. {page_number + 1})' if paginator.is_paginated else ''
        text = f'Заказы в поставке {supply_id}{page_info}:\n' \
               f'Всего {paginator.items_count}шт'
    else:
        text = 'В поставке нет заказов'
        add_main_menu_button = True
    answer_to_user(
        update,
        context,
        text,
        keyboard,
        add_main_menu_button=add_main_menu_button,
        edit_current_message=True
    )
    return 'HANDLE_EDIT_SUPPLY'


def show_order_details(
        update: Update,
        context: CallbackContext,
        order_id: int,
        supply_id: str
):
    wb_client = WBApiClient()
    context.bot.answer_callback_query(
        update.callback_query.id,
        f'Информация по заказу {order_id}'
    )
    orders = wb_client.get_supply_orders(supply_id)
    for order in orders:
        if order.id == order_id:
            current_order = order
            break
    else:
        return

    order_qr_code, *_ = wb_client.get_qr_codes_for_orders([current_order.id])

    keyboard = [
        [InlineKeyboardButton('Перенести в поставку', callback_data=f'add_to_supply_{order.id}')],
        [InlineKeyboardButton('Вернуться к поставке', callback_data=f'supply_{supply_id}')]
    ]

    text = f'Номер заказа: <b>{current_order.id}</b>\n' \
           f'Стикер: <b>{order_qr_code.part_a} {order_qr_code.part_b}</b>\n' \
           f'Артикул: <b>{current_order.article}</b>\n' \
           f'Поставка: <b>{supply_id}</b>\n' \
           f'Время с момента заказа: <b>{current_order.created_ago}</b>\n' \
           f'Цена: <b>{current_order.converted_price / 100} ₽</b>'

    answer_to_user(
        update,
        context,
        text,
        keyboard
    )
    return 'HANDLE_ORDER_DETAILS'


def show_new_order_details(update: Update, context: CallbackContext, order_id: int):
    wb_client = WBApiClient()
    for order in wb_client.get_new_orders():
        if order.id == order_id:
            current_order = order
            break
    else:
        return

    context.bot.answer_callback_query(
        update.callback_query.id,
        f'Информация по заказу {current_order.id}'
    )
    keyboard = [
        [InlineKeyboardButton('Перенести в поставку', callback_data=f'add_to_supply_{order.id}')],
        [InlineKeyboardButton('Вернуться к списку заказов', callback_data=f'new_orders')]
    ]

    text = f'Номер заказа: <b>{current_order.id}</b>\n' \
           f'Артикул: <b>{current_order.article}</b>\n' \
           f'Время с момента заказа: <b>{current_order.created_ago}</b>\n' \
           f'Цена: <b>{current_order.converted_price / 100} ₽</b>'

    answer_to_user(
        update,
        context,
        text,
        keyboard
    )
    return 'HANDLE_ORDER_DETAILS'


def send_stickers(update: Update, context: CallbackContext, supply_id: str):
    wb_client = WBApiClient()
    context.bot.answer_callback_query(
        update.callback_query.id,
        'Запущена подготовка стикеров. Подождите'
    )
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


def ask_to_choose_supply(update: Update, context: CallbackContext):
    wb_client = WBApiClient()
    active_supplies = list(filter(  # noqa
        SupplyFilter.ACTIVE,
        wb_client.get_supplies()
    ))
    order_id = update.callback_query.data.replace('add_to_supply_', '')
    keyboard = []
    for supply in active_supplies:
        button_name = f'{supply.name} | {supply.id}'
        keyboard.append([
            InlineKeyboardButton(button_name, callback_data=f'{supply.id}_{order_id}')
        ])

    keyboard.append(
        [InlineKeyboardButton('Создать новую поставку', callback_data='new_supply')]
    )
    text = 'Выберите поставку'
    answer_to_user(
        update,
        context,
        text,
        keyboard
    )
    return 'HANDLE_SUPPLY_CHOICE'


def add_order_to_supply(update: Update, context: CallbackContext):
    supply_id, order_id = update.callback_query.data.split('_')
    wb_client = WBApiClient()
    if not wb_client.add_order_to_supply(supply_id, order_id):
        context.bot.answer_callback_query(
            update.callback_query.id,
            'Произошла ошибка. Попробуйте позже'
        )
    else:
        context.bot.answer_callback_query(
            update.callback_query.id,
            f'Заказ {order_id} добавлен к поставке {supply_id}'
        )
    next_supply_id = context.user_data.get('current_supply', supply_id)
    return show_supply(update, context, next_supply_id)


def ask_for_supply_name(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton('Назад к списку поставок', callback_data='cancel')]
    ]
    text = 'Пришлите мне название для новой поставки'
    message = answer_to_user(
        update,
        context,
        text,
        keyboard
    )
    context.chat_data['message_to_delete'] = message.message_id
    return 'HANDLE_NEW_SUPPLY_NAME'


def create_new_supply(update: Update, context: CallbackContext):
    wb_client = WBApiClient()
    new_supply_name = update.message.text
    wb_client.create_new_supply(new_supply_name)
    message_to_delete = context.chat_data.get('message_to_delete')
    if message_to_delete:
        context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=message_to_delete
        )
    update.message = None
    return show_supplies(update, context)


def delete_supply(update, context, supply_id: str):
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
    return show_supplies(update, context)


def close_supply(update: Update, context: CallbackContext, supply_id: str):
    wb_client = WBApiClient()
    if not wb_client.send_supply_to_deliver(supply_id):
        context.bot.answer_callback_query(
            update.callback_query.id,
            'Произошла ошибка. Попробуйте позже'
        )
        return show_supplies(update, context)
    else:
        context.bot.answer_callback_query(
            update.callback_query.id,
            'Отправлено в доставку'
        )
        send_supply_qr_code(update, context, supply_id)
        return show_supplies(update, context)


def send_supply_qr_code(update: Update, context: CallbackContext, supply_id: str):
    wb_client = WBApiClient()
    supply_qr_code = wb_client.get_supply_qr_code(supply_id)
    supply_sticker = get_supply_sticker(supply_qr_code)
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=supply_sticker
    )


def get_confirmation_to_close_supply(update: Update, context: CallbackContext, supply_id: str):
    text = 'Вы уверены, что хотите закрыть поставку? Это действие невозможно отменить.'
    keyboard = [
        [InlineKeyboardButton('Да', callback_data=f'yes_{supply_id}'),
         InlineKeyboardButton('Нет', callback_data='no')]
    ]
    answer_to_user(
        update,
        context,
        text,
        keyboard,
        add_main_menu_button=False
    )
    return 'HANDLE_CONFIRMATION_TO_CLOSE_SUPPLY'


def show_waiting_orders(update: Update, context: CallbackContext, supplies_quantity: int = 7):
    wb_client = WBApiClient()
    supplies = list(filter(  # noqa
        SupplyFilter.CLOSED,
        wb_client.get_supplies(quantity=supplies_quantity)
    ))
    orders = []
    for supply in supplies:
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
    waiting_orders = filter(
        lambda o: o.id in waiting_order_ids,
        orders
    )
    waiting_orders_articles = [f'{order.supply_id} | {order}' for order in waiting_orders]
    text = '\n'.join(waiting_orders_articles)
    answer_to_user(update, context, text)
