from typing import Callable


class Router(dict[str, Callable]):

    def register(self, state_locator: str):
        def decorator(func):
            self[state_locator] = func

        return decorator
