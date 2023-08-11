from typing import Optional, Type

from telegram import Update
from telegram.ext import CallbackContext

from employers.models import Worker


class BaseState:

    def enter_state(self, update: Update, context: CallbackContext) -> None:
        pass

    def exit_state(self, update: Update, context: CallbackContext, **kwargs) -> None:
        pass

    def process(self, update: Update, context: CallbackContext) -> Optional[str]:
        if update.message:
            return self.react_on_message(update, context)
        elif update.callback_query:
            return self.react_on_inline_keyboard(update, context)

    def react_on_inline_keyboard(self, update: Update, context: CallbackContext) -> Optional[str]:
        pass

    def react_on_message(self, update: Update, context: CallbackContext) -> Optional[str]:
        context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )


class StateMachine(dict[str, BaseState]):

    def __init__(self, start_state_locator: str):
        self.start_state_locator = start_state_locator

    def register(self, state_locator: str):
        def decorator(cls: Type[BaseState]):
            self[state_locator] = cls()

        return decorator

    def process(self, update: Update, context: CallbackContext):
        users = Worker.objects.filter(has_access_to_wb_bot=True)
        user_ids = [user.tg_id for user in users]

        if update.effective_chat.id not in user_ids:
            return

        if self.react_on_commands(update, context):
            return

        locator = context.user_data.get('locator')
        state = self.get(locator)

        if not state:
            next_state_locator = self[self.start_state_locator].enter_state(update, context)
        else:
            next_state_locator = state.process(update, context)

        if next_state_locator:
            self.switch_state(update, context, next_state_locator, state)

    def react_on_commands(self, update: Update, context: CallbackContext) -> bool:
        commands = ['/start']

        if not update.message or update.message.text not in commands:
            return False

        if update.message.text == '/start':
            self.switch_state(update, context, self.start_state_locator)

        return True

    def switch_state(
            self,
            update: Update,
            context: CallbackContext,
            next_state_locator: str,
            current_state: BaseState = None
    ):
        if current_state:
            current_state.exit_state(update, context)

        next_state = self.get(next_state_locator)
        next_state.enter_state(update=update, context=context)
        context.user_data['locator'] = next_state_locator
