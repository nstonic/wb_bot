from functools import partial

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
        handle_users_reply_with_owner_id = partial(
            handle_users_reply,
            user_ids=[879491290]
        )
        updater = Updater(settings.TG_TOKEN)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CallbackQueryHandler(handle_users_reply_with_owner_id))  # noqa
        dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply_with_owner_id))  # noqa
        dispatcher.add_handler(CommandHandler('start', handle_users_reply_with_owner_id))  # noqa
        updater.start_polling()
        updater.idle()
