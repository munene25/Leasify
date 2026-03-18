from rest_framework import status
from typing import Any


def parse_error(response, status_code: int, err_type: str = "client_error", err_len: int = 1) -> list[dict[str, str]]:
    """
    Helper func parsing errors
    """
    assert response.status_code == status_code
    assert response.data["type"] == err_type
    errors: list[dict[str, str]] = response.data["errors"]
    assert len(errors) == err_len
    return errors


def parse_message(response, status_code: int = status.HTTP_200_OK) -> dict[str, Any]:
    """helper function"""
    assert response.status_code == status_code
    return response.data
