import pytest
from django.core.management import call_command
import pytest
from faker import Faker



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
