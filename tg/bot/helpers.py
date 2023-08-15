from enum import Enum

from wb_api import WBApiClient


class SupplyFilter(Enum):
    ALL = lambda s: True  # noqa
    ACTIVE = lambda s: not s.is_done  # noqa
    CLOSED = lambda s: s.is_done  # noqa


def filter_supplies(supply_filter: SupplyFilter):
    wb_client = WBApiClient()

    params = {
        'next': 0,
        'limit': 1000
    }
    all_supplies = []
    while True:  # Находим последнюю страницу с поставками
        supplies, params['next'] = wb_client.get_supplies(**params)
        all_supplies.extend(supplies)
        if len(supplies) == params['limit']:
            continue
        else:
            break

    filtered_supplies = list(filter(  # noqa
        supply_filter,
        all_supplies
    ))
    return filtered_supplies
