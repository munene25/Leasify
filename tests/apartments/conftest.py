from typing import Any
from unittest.mock import MagicMock

import pytest
from tests.types import Factory
from apartments.choices import Wing, Block


@pytest.fixture
def apartment_data() -> dict[str, Any]:
    return {
        "block": Block.A,
        "unit_number": 1,
        "floor": 0,
        "rent": 10_000,
        "rentable": True,
        "wing": Wing.WEST,
    }


@pytest.fixture
def full_clean_patch(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    full_clean = MagicMock()
    monkeypatch.setattr("apartments.services.Apartment.full_clean", full_clean)
    return full_clean
