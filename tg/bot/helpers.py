from enum import Enum

from telegram import Update
from telegram.ext import CallbackContext

from tg.bot.stickers import get_supply_sticker
from wb_api import WBApiClient


class SupplyFilter(Enum):
    ALL = lambda s: True  # noqa
    ACTIVE = lambda s: not s.is_done  # noqa
    CLOSED = lambda s: s.is_done  # noqa


def filter_supplies(supply_filter: SupplyFilter):
    wb_client = WBApiClient()

    params = {
        'next': 0,
        'limit': 1000
    }
    all_supplies = []
    while True:  # Находим последнюю страницу с поставками
        supplies, params['next'] = wb_client.get_supplies(**params)
        all_supplies.extend(supplies)
        if len(supplies) == params['limit']:
            continue
        else:
            break

    filtered_supplies = list(filter(  # noqa
        supply_filter,
        all_supplies
    ))
    return filtered_supplies


def send_supply_qr_code(update: Update, context: CallbackContext, supply_id: str):
    wb_client = WBApiClient()
    supply_qr_code = wb_client.get_supply_qr_code(supply_id)
    supply_sticker = get_supply_sticker(supply_qr_code)
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=supply_sticker
    )
