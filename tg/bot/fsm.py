from telegram import Update  # noqa
from telegram.ext import CallbackContext  # noqa
from .handlers import (
    show_start_menu,
    show_supplies,
    show_new_orders,
    show_supply,
    show_new_order_details,
    send_stickers,
    close_supply,
    ask_to_choose_supply,
    add_order_to_supply,
    ask_for_supply_name,
    create_new_supply,
    delete_supply,
    edit_supply,
    show_order_details,
    get_confirmation_to_close_supply,
    send_supply_qr_code,
    show_waiting_orders
)


def handle_main_menu(update: Update, context: CallbackContext):
    query = update.callback_query.data
    actions = {
        'show_supplies': show_supplies,
        'new_orders': show_new_orders,
        'check_orders': show_waiting_orders
    }
    if action := actions.get(query):
        return action(update, context)


def handle_supplies_menu(update: Update, context: CallbackContext):
    query = update.callback_query.data
    if query.startswith('supply_'):
        _, supply_id = query.split('_', maxsplit=1)
        return show_supply(update, context, supply_id)
    if query == 'new_supply':
        return ask_for_supply_name(update, context)
    if query == 'closed_supplies':
        return show_supplies(update, context, only_active=False)
    if query.startswith('page_'):
        _, page_number, only_active = query.split('_', maxsplit=2)
        return show_supplies(
            update,
            context,
            page_number=int(page_number),
            only_active={'True': True, 'False': False}.get(only_active)
        )


def handle_supply(update: Update, context: CallbackContext):
    query = update.callback_query.data
    _, supply_id = query.split('_', maxsplit=1)
    if query.startswith('stickers_'):
        return send_stickers(update, context, supply_id)
    if query.startswith('close_'):
        return get_confirmation_to_close_supply(update, context, supply_id)
    if query.startswith('delete_'):
        return delete_supply(update, context, supply_id)
    if query.startswith('edit_'):
        return edit_supply(update, context, supply_id)
    if query.startswith('qr_'):
        return send_supply_qr_code(update, context, supply_id)
    if query.startswith('show_supplies'):
        return show_supplies(update, context)


def handle_confirmation_to_close_supply(update: Update, context: CallbackContext):
    query = update.callback_query.data
    if query.startswith('yes_'):
        supply_id = query.replace('yes_', '')
        return close_supply(update, context, supply_id)
    if query == 'no':
        return show_supplies(update, context)


def handle_order_details(update: Update, context: CallbackContext):
    query = update.callback_query.data
    if query.startswith('add_to_supply_'):
        return ask_to_choose_supply(update, context)
    if query.startswith('supply_'):
        _, supply_id = query.split('_', maxsplit=1)
        return show_supply(update, context, supply_id)
    if query == 'new_orders':
        return show_new_orders(update, context)


def handle_new_supply_name(update: Update, context: CallbackContext):
    if update.message:
        return create_new_supply(update, context)
    if update.callback_query.data == 'cancel':
        return show_supplies(update, context)


def handle_new_orders(update: Update, context: CallbackContext):
    query = update.callback_query.data
    if query.startswith('page_'):
        _, page = query.split('_', maxsplit=1)
        return show_new_orders(update, context, int(page))
    else:
        order_id = int(update.callback_query.data)
        return show_new_order_details(update, context, order_id)


def handle_supply_choice(update: Update, context: CallbackContext):
    query = update.callback_query.data
    if query == 'new_supply':
        return ask_for_supply_name(update, context)
    else:
        return add_order_to_supply(update, context)


def handle_edit_supply(update: Update, context: CallbackContext):
    query = update.callback_query.data
    if query.startswith('page_'):
        page_callback_data, supply_callback_data = query.split(' ', maxsplit=1)
        page = page_callback_data.replace('page_', '')
        supply_id = supply_callback_data.replace('supply_', '')
        return edit_supply(
            update,
            context,
            supply_id=supply_id,
            page_number=int(page)
        )
    elif query.startswith('supply_'):
        _, supply_id = query.split('_', maxsplit=1)
        return show_supply(update, context, supply_id)
    else:
        supply_id, order_id = query.split('_', maxsplit=1)
        return show_order_details(update, context, int(order_id), supply_id)


def handle_users_reply(update: Update, context: CallbackContext, user_ids: int):
    if update.effective_chat.id not in user_ids:
        return

    if update.message:
        user_reply = update.message.text
    elif update.callback_query:
        user_reply = update.callback_query.data
    else:
        return

    if user_reply in ['/start', 'start']:
        user_state = 'START'
        context.user_data['state'] = user_state
    else:
        user_state = context.user_data.get('state')

    if user_state not in ['HANDLE_NEW_SUPPLY_NAME', 'START']:
        if update.message:
            context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
            return

    state_functions = {
        'START': show_start_menu,
        'HANDLE_MAIN_MENU': handle_main_menu,
        'HANDLE_SUPPLIES_MENU': handle_supplies_menu,
        'HANDLE_NEW_ORDERS': handle_new_orders,
        'HANDLE_SUPPLY': handle_supply,
        'HANDLE_ORDER_DETAILS': handle_order_details,
        'HANDLE_NEW_SUPPLY_NAME': handle_new_supply_name,
        'HANDLE_SUPPLY_CHOICE': handle_supply_choice,
        'HANDLE_EDIT_SUPPLY': handle_edit_supply,
        'HANDLE_CONFIRMATION_TO_CLOSE_SUPPLY': handle_confirmation_to_close_supply
    }

    state_handler = state_functions.get(user_state, show_start_menu)
    next_state = state_handler(
        update=update,
        context=context
    ) or user_state
    context.user_data['state'] = next_state
