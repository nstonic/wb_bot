from django.conf import settings
from django.core.management import BaseCommand
from telegram.ext import (
    Updater,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    Filters
)

from tg.bot import handle_users_reply


class Command(BaseCommand):

    def handle(self, *args, **options):
        updater = Updater(settings.TG_TOKEN)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
        dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
        dispatcher.add_handler(CommandHandler('start', handle_users_reply))
        updater.start_polling()
        updater.idle()
