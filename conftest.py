import pytest
from faker import Faker
from django.core.management import call_command
from users.services import user_account_create
from django.contrib.auth.models import Group
import random


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'fixtures/roles.json')


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
def user(payload):
    return user_account_create(**payload(password="Pa55word!").to_dict)

@pytest.fixture
def roles_list():
    return list(Group.objects.all())

@pytest.fixture
def get_role():
    def role(name: str | None = None):
        if not name:
            name = random.choice(["manager", "tenant", "caretaker"])
        return Group.objects.get(name=name)
    return role

@pytest.fixture
def manager_user(user, get_role):
    user.groups.add(get_role("manager"))
    return user
    
@pytest.fixture
def caretaker_user(user, get_role):
    user.groups.add(get_role("caretaker"))
    return user

@pytest.fixture
def tenant_user(user, get_role):
    user.groups.add(get_role("tenant"))
    return user
