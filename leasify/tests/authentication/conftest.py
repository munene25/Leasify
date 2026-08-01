import pytest
from unittest.mock import MagicMock


@pytest.fixture
def patch_notify_password_change(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr("leasify.authentication.tasks.notify_password_change.delay", mock)
    return mock


@pytest.fixture
def patch_send_token_email(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr("leasify.authentication.tasks.send_token_email.delay", mock)
    return mock


