from tg.bot.state_machine import StateDecoratorType
from tg.bot.state_classes import BaseState


class Router(dict[str, BaseState]):
    decorators: tuple[StateDecoratorType]

    def __init__(self, decorators: list[StateDecoratorType] | None = None):  # noqa
        self.decorators = tuple(decorators) if decorators else tuple()

    def register(self, state_class_locator: str):
        def register_state_class(state_class: BaseState) -> BaseState:
            wrapped_state_class = state_class
            for decorator in reversed(self.decorators):
                wrapped_state_class = decorator(wrapped_state_class)

            self[state_class_locator] = wrapped_state_class

            return wrapped_state_class

        return register_state_class