import pytest
import typing
from phonenumber_field.phonenumber import PhoneNumber

class UserCreatePayload(typing.TypedDict):
    first_name: str
    last_name: str
    email: str
    password: str
    phone_number: PhoneNumber

@pytest.fixture
def user_create_payload(fake, password, phone_no) -> UserCreatePayload:
    return {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.email(),
        "password": password,
        "phone_number": phone_no(),
    }

@pytest.fixture(params=["+101-999-222-222","+222-222-222-222","+256-722-222-222","+255712345678"],)
def wrong_phone_number(phone_no, request) -> PhoneNumber:
    return phone_no(request.param)

