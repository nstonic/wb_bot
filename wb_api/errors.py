import time
from datetime import datetime

from requests import Response
from requests.exceptions import ChunkedEncodingError, JSONDecodeError


class AuthError(Exception):
    pass


class WBAPIError(Exception):
    def __init__(self, message: str, code: str | int = None):
        super().__init__()
        self.message = message
        self.code = code

    def __str__(self):
        return f'{self.code}: {self.message}' if self.code else self.message


def check_response(response: Response):
    response.raise_for_status()
    try:
        response_json = response.json()
    except (AttributeError, JSONDecodeError):
        return
    else:
        if response_json.keys() == ('code', 'message'):
            raise WBAPIError(
                code=response_json['code'],
                message=response_json['message']
            )
        if response_json.get('error'):
            raise WBAPIError(
                message=f'{response_json["errorText"]}: {response_json["additionalErrors"]}'
            )


def retry_on_network_error(func):
    def wrapper(*args, **kwargs):
        last_error_timestamp = 0
        delay = 0
        while True:
            try:
                return func(*args, **kwargs)
            except (ChunkedEncodingError, ConnectionError):
                right_now = datetime.now().timestamp()
                delay = min(
                    0 if right_now - last_error_timestamp > 30 else delay,
                    10
                )
                last_error_timestamp = datetime.now().timestamp()
                time.sleep(delay)
                delay += 1
                continue

    return wrapper
