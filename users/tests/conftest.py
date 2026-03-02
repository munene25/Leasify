import pytest
from dataclasses import dataclass, field, asdict
from faker import Faker
from phonenumber_field.phonenumber import PhoneNumber
from users.services import user_account_create

_fake = Faker("en_KE")


@dataclass
class UserData:
    first_name: str = field(default_factory=_fake.first_name)
    last_name: str = field(default_factory=_fake.last_name)
    email: str = field(default_factory=_fake.email)
    password: str = field(default_factory=_fake.password)
    phone_number: PhoneNumber = field(default_factory=lambda: PhoneNumber.from_string(_fake.numerify("+254-7##-###-###")))


@pytest.fixture(autouse=True)
def enable_db_access(db):
    """Automatically enable db access for all tests."""
    pass

@pytest.fixture
def fake():
    """Return a faker instance with a locale already set"""
    return Faker("en_KE")

@pytest.fixture
def userdata():
    # Returns a creator function
    def _create(**overrides) -> UserData:
        userdata = UserData()
        if overrides:
            for k, v in overrides.items():
                setattr(userdata, k, v)
        return userdata

    return _create


@pytest.fixture(autouse=True)
def settings_override(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

@pytest.fixture
def user():
    return user_account_create(**asdict(UserData()))