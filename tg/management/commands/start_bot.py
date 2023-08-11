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
from tg.bot.states import state_machine


class Command(BaseCommand):

    def handle(self, *args, **options):
        updater = Updater(settings.TG_TOKEN)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CallbackQueryHandler(state_machine.process))
        dispatcher.add_handler(MessageHandler(Filters.text, state_machine.process))
        dispatcher.add_handler(CommandHandler('start', state_machine.process))
        updater.start_polling()
        updater.idle()
