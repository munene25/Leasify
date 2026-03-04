import pytest
from dataclasses import dataclass, field, asdict
from faker import Faker
from phonenumber_field.phonenumber import PhoneNumber
from users.services import user_account_create
from typing import Callable, Any

_fake = Faker("en_KE")


@dataclass
class APIPayload:
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


@pytest.fixture(autouse=True)
def enable_db_access(db):
    """Automatically enable db access for all tests."""
    pass


@pytest.fixture
def phone_no() -> Callable[[str | None], PhoneNumber]:
    phone = lambda num=None: PhoneNumber.from_string(
        num or _fake.numerify("+254-7##-###-###")
    )
    return phone

@pytest.fixture(params=["+101-999-222-222","+222-222-222-222","+256-722-222-222","+255712345678"],)
def wrong_phone_number(phone_no, request) -> PhoneNumber:
    return phone_no(request.param)

@pytest.fixture
def fake():
    """Return a faker instance with a locale already set"""
    return Faker("en_KE")


@pytest.fixture(autouse=True)
def settings_override(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    # django-pytest needs locmem backend to capture the mail
    # settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


@pytest.fixture
def payload() -> type[APIPayload]:
    return APIPayload


@pytest.fixture
def user(payload):
    return user_account_create(**payload(password="Pa55word!").to_dict)
