import pytest
from dataclasses import dataclass, field, asdict
from faker import Faker
from phonenumber_field.phonenumber import PhoneNumber
from typing import Callable, Any

_fake = Faker("en_KE")

@dataclass
class UserCreationPayload:
    first_name: str = field(default_factory=_fake.first_name)
    last_name: str = field(default_factory=_fake.last_name)
    email: str = field(default_factory=_fake.email)
    password: str = field(default_factory=_fake.password)
    phone_number: PhoneNumber = field(
        default_factory=lambda: PhoneNumber.from_string(
            _fake.numerify("+254-7##-###-###")
        )
    )

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@pytest.fixture
def payload() -> type:
    return UserCreationPayload


@pytest.fixture(params=["+101-999-222-222","+222-222-222-222","+256-722-222-222","+255712345678"],)
def wrong_phone_number(phone_no, request) -> PhoneNumber:
    return phone_no(request.param)

@pytest.fixture
def password():
    return "Pa55word!"