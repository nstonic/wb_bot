from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Supply(BaseModel):
    id: str
    name: str
    closed_at: datetime | None = Field(alias='closedAt', default=None)
    created_at: datetime = Field(alias='createdAt')
    is_done: bool = Field(alias='done')

    def __str__(self):
        is_done = ('Открыта', 'Закрыта')
        return f'{self.name} | {self.id} | {is_done[self.is_done]}'


class Order(BaseModel):
    id: int
    supply_id: str = Field(alias='supplyId', default='')
    converted_price: int = Field(alias='convertedPrice')
    article: str
    created_at: datetime = Field(alias='createdAt')
    created_ago: str | None = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        created_ago = datetime.now().timestamp() - self.created_at.timestamp()
        hours, seconds = divmod(int(created_ago), 3600)
        minutes, seconds = divmod(seconds, 60)
        self.created_ago = f'{hours:02.0f}ч. {minutes:02.0f}м.'

    def __str__(self):
        return f'{self.article} | {self.created_ago}'


class OrderStatus(BaseModel):
    id: int
    supplier_status: str = Field(alias='supplierStatus')
    wb_status: str = Field(alias='wbStatus')


class OrderQRCode(BaseModel):
    order_id: int = Field(alias='orderId')
    file: str
    part_a: str = Field(alias='partA')
    part_b: str = Field(alias='partB')


class SupplyQRCode(BaseModel):
    barcode: str
    image_string: str = Field(alias='file')


@dataclass
class Product:
    article: str
    name: str = ''
    barcode: str = ''
    brand: str = ''
    countries: list[str] = tuple()
    colors: list[str] = tuple()
    media_urls: list[str] = tuple()
    media_files: list[bytes] = tuple()

    @staticmethod
    def parse_from_card(product_card: dict):
        characteristics = {
            key: value
            for characteristic in product_card.get('characteristics')
            for key, value in characteristic.items()
        }
        size, *_ = product_card.get('sizes')
        barcode, *_ = size.get('skus', '')
        return Product(
            article=product_card.get('vendorCode', ''),
            name=characteristics.get('Наименование', ''),
            brand=characteristics.get('Бренд', ''),
            barcode=barcode,
            colors=characteristics.get('Цвет', []),
            countries=characteristics.get('Страна производства', []),
            media_files=product_card.get('mediaFiles', [])
        )


class SupplyFilter(Enum):
    ALL = lambda s: True  # noqa
    ACTIVE = lambda s: not s.is_done  # noqa
    CLOSED = lambda s: s.is_done  # noqa
