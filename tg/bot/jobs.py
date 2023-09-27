from telegram.ext import CallbackContext

from tg.bot.stickers import get_orders_stickers
from wb.wb_api import WBApiClient


def send_stickers_job(context: CallbackContext):
    supply_id = context.job.context['supply_id']
    wb_client = WBApiClient()
    orders = wb_client.get_supply_orders(supply_id)
    order_qr_codes = wb_client.get_qr_codes_for_orders(
        [order.id for order in orders]
    )
    articles = set([order.article for order in orders])
    products = [wb_client.get_product(article) for article in articles]
    zip_file = get_orders_stickers(
        orders,
        products,
        order_qr_codes,
        supply_id
    )
    context.bot.send_document(
        chat_id=context.job.context['chat_id'],
        document=zip_file.getvalue(),
        filename=zip_file.name
    )