import pytest
from tests.types import Factory
from apartments.choices import Wing, Block


@pytest.fixture
def apartment_data() -> dict[str, str| int]:
    return {
        "block": Block.A,
        "unit_number": 1,
        "floor": 0,
        "rent": 10_000,
        "rentable": True,
        "wing": Wing.WEST,
    }
