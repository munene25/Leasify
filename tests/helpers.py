from rest_framework import status
from typing import Any
from tests.types import IsResponse
import json


def parse_error(
    response: IsResponse, status_code: int, err_type: str = "client_error", err_len: int = 1
) -> list[dict[str, str]]:
    """
    Helper func parsing errors
    """
    msg = parse_response(response)
    assert response.status_code == status_code, msg
    assert response.data["type"] == err_type, msg
    errors: list[dict[str, str]] = response.data["errors"]
    assert len(errors) == err_len, msg
    return errors


def parse_message(response: IsResponse, status_code: int = status.HTTP_200_OK) -> dict[str, Any]:
    """helper function"""
    msg = parse_response(response)
    assert response.status_code == status_code, msg
    return response.data


def parse_response(response: IsResponse):
    data = {
        "RESPONSE": {
            "STATUS_CODE": response.status_code,
            "DATA": response.data,
            "HEADERS": dict(response.headers),
            "COOKIES": dict(response.cookies)
        }
    }
    return json.dumps(data, indent=4)
