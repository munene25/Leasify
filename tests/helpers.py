import json
from typing import Any
from django.conf import settings
from django.core.mail import EmailMessage
from rest_framework import status
from tests.types import IsResponse
from users.models import User

def parse_error(
    response: IsResponse, status_code: int, err_type: str = "client_error", err_len: int = 1
) -> list[dict[str, str]]:
    """
        Helper func for parsing drf error response objects
    """
    msg = parse_response(response)
    assert response.status_code == status_code, msg
    assert response.data["type"] == err_type, msg
    errors: list[dict[str, str]] = response.data["errors"]
    assert len(errors) == err_len, msg
    return errors


def parse_message(response: IsResponse, status_code: int = status.HTTP_200_OK) -> dict[str, Any]:
    """
        Helper func for parsing drf success response objects
    """
    msg = parse_response(response)
    assert response.status_code == status_code, msg
    return response.data


def parse_response(response: IsResponse) -> str:
    """
        This parses the error responses to allow inspection of response body on test failures
    """
    data = {
        "RESPONSE": {
            "STATUS_CODE": response.status_code,
            "DATA": getattr(response, "data", {}),
            "HEADERS": dict(response.headers),
            "COOKIES": dict(response.cookies)
        }
    }
    return json.dumps(data, indent=4)

def check_links_in_mail(user: User, mail: EmailMessage, path: str)-> None:
    """Checks whether the links present and valid in the mail message"""

    from users.tokens import token_validate, get_user_from_uidb64
    
    # get links and check if they match 
    links = [word for word in mail.body.split() if path in word]
    assert len(set(links)) == 1, json.dumps({"links": links})

    # get uidb64 and token if it exists
    base_url = settings.FRONTEND_URL + "/" + path + "/"
    params = links[0].replace(base_url, "").split("/")
    assert len(params) >= 1, json.dumps({"params": params})
    uidb64 = params[0]
    u = get_user_from_uidb64(uidb64)
    assert u == user
    try:
        token_validate(user=u, token=params[1])
    except KeyError:
        pass

