from abc import ABC, abstractmethod
from typing import Type, NamedTuple

from telegram import Update  # noqa
from telegram.ext import CallbackContext  # noqa


class Locator(NamedTuple):
    state_name: str
    params: dict = dict()


class BaseState(ABC):

    def __init__(self, state_name: str):
        self.state_name = state_name

    @abstractmethod
    def enter_state(self, update: Update, context: CallbackContext, **params) -> Locator | None:
        pass

    @abstractmethod
    def exit_state(self, update: Update, context: CallbackContext, **params) -> None:
        pass

    @abstractmethod
    def process(self, update: Update, context: CallbackContext, params) -> Locator | None:
        pass


class StateMachine(dict[str, BaseState]):

    def __init__(self, *, start_state_locator: Locator, commands_map: dict):
        super().__init__()
        self.commands_map = commands_map
        self.start_state_locator = start_state_locator
        self.update = None
        self.context = None

    def register(self, state_name: str):
        def decorator(cls: Type[BaseState]):
            self[state_name] = cls(state_name)

        return decorator

    def process(self, update: Update, context: CallbackContext):
        self.update = update
        self.context = context

        if update.message and update.message.text in self.commands_map:
            state_locator = self.commands_map[update.message.text]
            self.switch_state(state_locator)
            return

        locator = context.user_data.get('locator')

        if not locator:
            self.switch_state(self.start_state_locator)
            return
        else:
            state = self.get(locator.state_name)
            next_state_locator = state.process(self.update, self.context, locator.params)

        if not next_state_locator:
            return

        if locator != next_state_locator:
            state.exit_state(update, context)

        self.switch_state(next_state_locator)

    def switch_state(self, next_state_locator: Locator):
        next_state = self.get(next_state_locator.state_name)
        if locator := next_state.enter_state(self.update, self.context, **next_state_locator.params):
            next_state_locator = locator
        self.context.user_data['locator'] = next_state_locator
