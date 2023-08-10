from typing import Callable

import more_itertools
from telegram import InlineKeyboardButton  # noqa


class Paginator:

    def __init__(
            self,
            item_list: list,
            button_text_getter: Callable,
            button_callback_data_getter: Callable,
            page_size: int = 10
    ):
        self.button_callback_data_getter = button_callback_data_getter
        self.button_text_getter = button_text_getter
        self.item_list = item_list
        self.items_count = len(item_list)
        self.page_size = page_size
        self.pages = list(more_itertools.chunked(self.item_list, self.page_size))
        self.total_pages = len(self.pages)
        self.is_paginated = self.total_pages > 1
        self.max_page_number = self.total_pages - 1
        self.current_page = 1

    def get_keyboard(
            self,
            page_number: int = 1,
            callback_data_prefix: str = '',
            page_callback_data_postfix: str = ''
    ) -> list[list[InlineKeyboardButton]]:
        self.current_page = min(max(1, page_number), self.total_pages)
        page_keyboard = [
            [InlineKeyboardButton(
                self.button_text_getter(item),
                callback_data=f'{callback_data_prefix}{self.button_callback_data_getter(item)}'
            )]
            for item in self.pages[self.current_page-1]
        ]
        if self.is_paginated:
            pagination_keyboard = [
                InlineKeyboardButton(
                    '1', callback_data=f'page_1{page_callback_data_postfix}'
                ),
                InlineKeyboardButton(
                    '<',
                    callback_data=f'page_{self.current_page - 1}{page_callback_data_postfix}'
                ),
                InlineKeyboardButton(
                    str(self.current_page),
                    callback_data=f'page_{self.current_page}{page_callback_data_postfix}'
                ),
                InlineKeyboardButton(
                    '>',
                    callback_data=f'page_{self.current_page + 1}{page_callback_data_postfix}'
                ),
                InlineKeyboardButton(
                    str(self.total_pages),
                    callback_data=f'page_{self.total_pages}{page_callback_data_postfix}'
                )
            ]
            page_keyboard.append(pagination_keyboard)
        return page_keyboard
