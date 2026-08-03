import json
from typing import Any
from django.conf import settings
from django.core.mail import EmailMessage
from rest_framework import status
from leasify.tests.types import IsResponse, IsError, PaginatedResponse
from leasify.users.models import User


def parse_error(response: IsResponse, status_code: int, err_type: str = "client_error", err_len: int = 1) -> list[IsError]:
    """
    Helper func for parsing drf error response objects
    """

    msg = parse_response(response)
    assert response.status_code == status_code, msg
    assert response.data["type"] == err_type, msg
    errors = response.data["errors"]
    assert len(errors) == err_len, msg
    return errors


def parse_message(response: IsResponse, status_code: int = status.HTTP_200_OK) -> dict[str, Any]:
    """
    Helper func for parsing drf success response objects
    """

    msg = parse_response(response)
    assert response.status_code == status_code, msg
    return response.data

def parse_paginated_response(response: IsResponse, count: int) -> PaginatedResponse:
    msg = parse_response(response)
    assert response.status_code == status.HTTP_200_OK, msg
    data: PaginatedResponse = response.data  #type: ignore
    assert data["count"] == count, msg
    return data

def parse_response(response: IsResponse) -> str:
    """
    This parses the error responses to allow inspection of response body on test failures
    """

    data = {
        "RESPONSE": {
            "STATUS_CODE": response.status_code,
            "DATA": getattr(response, "data", {}),
            "HEADERS": dict(response.headers),
            "COOKIES": dict(response.cookies),
        }
    }
    return json.dumps(data, indent=4)

def check_links_in_mail(*, mail: EmailMessage, path: str, with_uidb64: bool = False, with_token: bool = False, user: User | None = None) -> None:
    """Checks whether the links present and valid in the mail message
    
    Token is not include"""

    from leasify.authentication.tokens import token_validate, get_user_from_uidb64, build_url

    # get links and check if they match
    url = build_url(base_path=path, with_uidb64=False, with_token=False)
    links = [word for word in mail.body.split() if url in word]
    assert len(set(links)) == 1, json.dumps({"links": links})

    # get uidb64 and token if it exists
    if with_uidb64 or with_token:
        if not user:
            raise ValueError("User object not provided")
        
        params = links[0].lstrip(url).split("/")
        if with_uidb64:
            assert params[0], json.dumps({"params": params})
            assert get_user_from_uidb64(params[0]) == user
        if with_token: 
            token_validate(user=user, token=params[1])
