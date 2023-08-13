from typing import Type, cast

from telegram import Update
from telegram.ext import CallbackContext

from employers.models import Worker
from tg.bot.state_classes import Locator, BaseState


class StateMachine(dict[str, BaseState]):

    def __init__(self, start_state_name: str):
        self.start_state_name = Locator(start_state_name)

    def register(self, state_name: str):
        def decorator(cls: Type[BaseState]):
            self[state_name] = cls(state_name)

        return decorator

    def process(self, update: Update, context: CallbackContext):
        users = Worker.objects.filter(has_access_to_wb_bot=True)
        user_ids = [user.tg_id for user in users]

        if update.effective_chat.id not in user_ids:
            return

        if self.react_on_commands(update, context):
            return

        locator = context.user_data.get('locator')
        locator = cast(Locator, locator)
        if not locator:
            self.switch_state(update, context, self.start_state_name)
            return
        else:
            state = self.get(locator.state_name)
            next_state_locator = state.process(update, context, **locator.params)

        if next_state_locator:
            self.switch_state(update, context, next_state_locator, state)

    def react_on_commands(self, update: Update, context: CallbackContext) -> bool:
        commands = ['/start']

        if not update.message or update.message.text not in commands:
            return False

        if update.message.text == '/start':
            self.switch_state(update, context, next_state_locator=self.start_state_name)

        return True

    def switch_state(
            self,
            update: Update,
            context: CallbackContext,
            next_state_locator: Locator,
            current_state: BaseState = None
    ):
        if current_state:
            current_state.exit_state(update, context)

        next_state = self.get(next_state_locator.state_name)
        next_state.enter_state(update=update, context=context, **next_state_locator.params)
        context.user_data['locator'] = next_state_locator
