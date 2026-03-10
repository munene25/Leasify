import random
import pytest
import typing
from faker import Faker
from django.core.management import call_command
from django.contrib.auth.models import Group
from phonenumber_field.phonenumber import PhoneNumber
from users.models import User
from users.services import user_account_create
from rest_framework.test import APIClient


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "fixtures/roles.json")


@pytest.fixture(autouse=True)
def enable_db_access(db):
    """Automatically enable db access for all tests."""
    pass


@pytest.fixture(autouse=True)
def globals(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.LOGGING = None
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }



@pytest.fixture
def fake():
    """
    Return a faker instance with a locale already set
    """

    return Faker("en_KE")


@pytest.fixture
def user(fake, phone_no) -> User:
    """
    Returns a user object with an account created
    """
    
    return user_account_create(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        password="Pa55word!",
        email=fake.email(),
        phone_number=phone_no(),
        notify=False,
    )

@pytest.fixture
def roles_list() -> list[Group]:
    """
    Returns a list of all available roles|Groups
    """
    return list(Group.objects.all())


@pytest.fixture
def get_role() -> typing.Callable[[str], Group]:
    """
    Callable to return a specific group
    Pass in the str value of the group 
    """
    return lambda name: Group.objects.get(name=name)


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

@pytest.fixture
def password():
    return "Pa55word!"


@pytest.fixture
def phone_no(fake) -> typing.Callable[[str | None], PhoneNumber]:
    """
    A callable to generate a phone number object
    """

    return lambda num=None: PhoneNumber.from_string(
        num or fake.numerify("+254-7##-###-###")
    )


@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def auth_manager(client, manager_user):
    client.force_authenticate(user=manager_user)
    return client

@pytest.fixture
def auth_user(client, user):
    client.force_authenticate(user=user)
    return client

@pytest.fixture
def auth_tenant(client, tenant_user):
    client.force_authenticate(user=tenant_user)
    return client

@pytest.fixture
def auth_caretaker(client, caretaker_user):
    client.force_authenticate(user=caretaker_user)
    return client

