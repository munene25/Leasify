import pytest

@pytest.fixture(params=["+101-999-222-222", "+222-222-222-222", "+256-722-222-222", "+255712345678"])
def wrong_phone_number(request) -> str:
    return request.param
