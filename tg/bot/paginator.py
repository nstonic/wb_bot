from typing import Callable

import more_itertools
from telegram import InlineKeyboardButton  # noqa


class Paginator:

    def __init__(
            self,
            item_list: list,
            button_text_getter: Callable,
            button_callback_data_getter: Callable,
            page_size: int = 10,
            page_callback_data_prefix: str = 'page'
    ):
        self.button_callback_data_getter = button_callback_data_getter
        self.button_text_getter = button_text_getter
        self.item_list = item_list
        self.page_size = page_size
        self.pages = list(more_itertools.chunked(self.item_list, self.page_size))
        self.total_pages = len(self.pages)
        self.is_paginated = self.total_pages > 1
        self.page_callback_data_prefix = page_callback_data_prefix

    def get_keyboard(
            self,
            page_number: int = 1,
    ) -> list[list[InlineKeyboardButton]]:
        page_number = min(max(1, page_number), self.total_pages)
        page_keyboard = [
            [InlineKeyboardButton(
                self.button_text_getter(item),
                callback_data=self.button_callback_data_getter(item)
            )]
            for item in self.pages[page_number - 1]
        ]
        if self.is_paginated:
            pagination_keyboard = [
                InlineKeyboardButton(
                    '1', callback_data=f'{self.page_callback_data_prefix}#1'
                ),
                InlineKeyboardButton(
                    '<',
                    callback_data=f'{self.page_callback_data_prefix}#{page_number - 1}'
                ),
                InlineKeyboardButton(
                    str(page_number),
                    callback_data=f'{self.page_callback_data_prefix}#{page_number}'
                ),
                InlineKeyboardButton(
                    '>',
                    callback_data=f'{self.page_callback_data_prefix}#{page_number + 1}'
                ),
                InlineKeyboardButton(
                    str(self.total_pages),
                    callback_data=f'{self.page_callback_data_prefix}#{self.total_pages}'
                )
            ]
            page_keyboard.append(pagination_keyboard)
        return page_keyboard
