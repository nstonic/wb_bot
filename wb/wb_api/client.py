from pprint import pprint
from typing import Generator

import more_itertools
from requests import Response, request

from .errors import check_response, retry_on_network_error, AuthError
from .types import Supply, Order, Product, OrderQRCode, SupplyQRCode, OrderStatus


class WBApiClient:
    instance = None

    def __new__(cls, *args, **kwargs):
        if not cls.instance:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self, token=None):
        if not hasattr(self, '_token'):
            if token:
                self._token = token
            else:
                raise AuthError('WBClient is not initialised')

    @retry_on_network_error
    def make_request(self, method: str, url: str, headers_extra: dict = None, **kwargs) -> Response:
        headers = {'Authorization': self._token}
        if headers_extra:
            headers.update(headers_extra)
        response = request(method, url, headers=headers, **kwargs)
        check_response(response)
        return response

    def get_supply_orders(self, supply_id: str) -> list[Order]:
        response = self.make_request(
            'get',
            f'https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}/orders'
        )
        orders = [Order.model_validate(order) for order in response.json()['orders']]
        for order in orders:
            order.supply_id = supply_id
        return orders

    def get_supply(self, supply_id: str) -> Supply:
        response = self.make_request(
            'get',
            f'https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}'
        )
        return Supply.model_validate(response.json())

    def get_products(self, articles: set[str]) -> Generator[Product, None, None]:
        limit = 100
        payload = {
            "settings": {
                "cursor": {
                    "limit": limit
                },
                "filter": {
                    "withPhoto": -1
                }
            }
        }
        while True:
            response = self.make_request(
                'post',
                'https://suppliers-api.wildberries.ru/content/v2/get/cards/list',
                json=payload,
            )
            data = response.json()
            for product_card in data['cards']:
                if product_card['vendorCode'] in articles:
                    yield Product.parse_from_card(product_card)
                    articles.remove(product_card['vendorCode'])
                    if not articles:
                        break
            else:
                if data['cursor']['total'] < limit:
                    break
                else:
                    payload['settings']['cursor']['updatedAt'] = data['cursor']['updatedAt']
                    payload['settings']['cursor']['nmID'] = data['cursor']['nmID']

    def get_supplies(self, limit: int = 1000, next: int = 0) -> tuple[list[Supply], int]:
        params = {
            'limit': limit,
            'next': next
        }
        response = self.make_request(
            'get',
            'https://suppliers-api.wildberries.ru/api/v3/supplies',
            params=params
        )
        supplies = [
            Supply.model_validate(supply)
            for supply in response.json()['supplies']
        ]
        return supplies, next

    def get_qr_codes_for_orders(self, order_ids: list[int]) -> list[OrderQRCode]:
        stickers = []
        params = {
            'type': 'png',
            'width': 58,
            'height': 40
        }
        for chunk in more_itertools.chunked(order_ids, 100):
            response = self.make_request(
                'post',
                'https://suppliers-api.wildberries.ru/api/v3/orders/stickers',
                json={'orders': chunk},
                params=params
            )
            stickers.extend([OrderQRCode.model_validate(sticker) for sticker in response.json()['stickers']])
        return stickers

    def send_supply_to_deliver(self, supply_id: str) -> bool:
        response = self.make_request(
            'patch',
            f'https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}/deliver'
        )
        return response.ok

    def get_supply_qr_code(self, supply_id: str) -> SupplyQRCode:
        response = self.make_request(
            'get',
            f'https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}/barcode',
            params={
                'type': 'png',
                'width': 58,
                'height': 40
            }
        )
        return SupplyQRCode.model_validate(response.json())

    def get_new_orders(self) -> list[Order]:
        response = self.make_request(
            'get',
            'https://suppliers-api.wildberries.ru/api/v3/orders/new'
        )
        return [
            Order.model_validate(order)
            for order in response.json()['orders']
        ]

    def get_orders(
            self,
            next: int = 0,  # noqa
            limit: int = 100,
            datestamp_from: int = None,
            datestamp_to: int = None
    ) -> tuple[list[Order], int]:
        params = {
            'next': next,
            'limit': limit
        }
        if datestamp_from:
            params['dateFrom'] = datestamp_from
        if datestamp_to:
            params['dateTo'] = datestamp_to
        response = self.make_request(
            'get',
            'https://suppliers-api.wildberries.ru/api/v3/orders',
            params=params
        )
        response_content = response.json()
        orders = [
            Order.model_validate(order)
            for order in response_content['orders']
        ]
        return orders, response_content['next']

    def add_order_to_supply(self, supply_id: str, order_id: int | str) -> int:
        response = self.make_request(
            'patch',
            f'https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}/orders/{order_id}'
        )
        return response.ok

    def create_new_supply(self, supply_name: str) -> str:
        response = self.make_request(
            'post',
            'https://suppliers-api.wildberries.ru/api/v3/supplies',
            json={'name': supply_name}
        )
        return response.json().get('id')

    def delete_supply_by_id(self, supply_id: str) -> int:
        response = self.make_request(
            'delete',
            f'https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}'
        )
        return response.ok

    def check_orders_status(self, order_ids: list[int]) -> Generator[OrderStatus, None, None]:
        for chunk in more_itertools.chunked(order_ids, 1000):
            response = self.make_request(
                'post',
                'https://suppliers-api.wildberries.ru/api/v3/orders/status',
                json={"orders": chunk}
            )
            for order in response.json()['orders']:
                yield OrderStatus.model_validate(order)
