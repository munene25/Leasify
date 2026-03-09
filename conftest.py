import random
import pytest
import typing
from faker import Faker
from django.core.management import call_command
from django.contrib.auth.models import Group
from phonenumber_field.phonenumber import PhoneNumber
from users.models import User
from users.services import user_account_create


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "fixtures/roles.json")


@pytest.fixture(autouse=True)
def enable_db_access(db):
    """Automatically enable db access for all tests."""
    pass


@pytest.fixture(autouse=True)
def settings_override(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    # django-pytest needs locmem backend to capture the mail
    # settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    settings.LOGGING = None


@pytest.fixture
def fake():
    """Return a faker instance with a locale already set"""
    return Faker("en_KE")


@pytest.fixture
def phone_no(fake) -> typing.Callable[[str | None], PhoneNumber]:
    
    return lambda num=None: PhoneNumber.from_string(
        num or fake.numerify("+254-7##-###-###")
    )


@pytest.fixture
def user(fake, phone_no) -> User:
    return user_account_create(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        password="Pa55word!",
        email=fake.email(),
        phone_number=phone_no(),
    )


@pytest.fixture
def roles_list() -> list[Group]:
    return list(Group.objects.all())


@pytest.fixture
def get_role() -> typing.Callable[[str, None], Group]:
    def role(name: str | None = None):
        if not name:
            name = random.choice(["manager", "tenant", "caretaker"])
        return Group.objects.get(name=name)

    return role


@pytest.fixture
def manager_user(user, get_role) -> User:
    user.groups.add(get_role("manager"))
    return user


@pytest.fixture
def caretaker_user(user, get_role) -> User:
    user.groups.add(get_role("caretaker"))
    return user


@pytest.fixture
def tenant_user(user, get_role) -> User:
    user.groups.add(get_role("tenant"))
    return user
