import pytest
from decimal import Decimal
from typing import Any
from rest_framework.exceptions import ValidationError
from rest_framework import status
from apartments.services import ApartmentUpdateData
from apartments.models import Apartment
from tests.types import IsClient, PaginatedResponse
from tests.helpers import parse_error, parse_message, parse_paginated_response


class TestApartmentListCreateView:
    path = "/apartments/"
    data = {"block": "NEW", "unit_number": 10, "rent": Decimal(10_000), "rentable": True}
    
    def test_apartment_creation_successful(self, manager_client: IsClient, settings):
        """
        Apartment should be created and returned in response message.
        """

        from zoneinfo import ZoneInfo

        res1 = manager_client.post(self.path, self.data)
        data = parse_message(res1, status.HTTP_201_CREATED)
        apartment = Apartment.objects.get(pk=1)
        
        assert data["apartment_id"] == apartment.pk
        assert data["block"] == apartment.block == self.data["block"]
        assert data["unit_number"] == apartment.unit_number == self.data["unit_number"]
        assert Decimal(data["rent"]) == apartment.rent == self.data["rent"]
        assert data["rentable"] == apartment.rentable == self.data["rentable"]
        assert data["created_at"] == apartment.created_at.astimezone(ZoneInfo(settings.TIME_ZONE)).isoformat()
        assert data["current_tenant"] == None
    
    def test_apartment_creation_rentable_field_ommission(self, manager_client: IsClient):
        """
        Need exclusive testing as was identified in user's notify field
        Bug fixed, added default=True to serializer
        """

        data = self.data.copy()
        data.pop("rentable")
        response = manager_client.post(self.path, data)
        response_data = parse_message(response, status.HTTP_201_CREATED)
        apt = Apartment.objects.get(pk=response_data["apartment_id"])
        assert apt.rentable == True

    @pytest.mark.parametrize("field,value", (("block", "old"), ("block", "new"), ("unit_number", "five"), ("rent", "20 thousand"), ("rentable", "okay")))
    def test_apartment_creation_serializer_validation(self, field: str, value: Any, manager_client: IsClient):
        """
        Test various validation failures are flagged by serializer
        """
        
        code = status.HTTP_400_BAD_REQUEST
        data = self.data.copy()
        data[field] = value

        response = manager_client.post(self.path, data)
        error = parse_error(response, code, err_type="validation_error")[0]
        assert error["attr"] == field

    def test_apartment_creation_authorization(self, caretaker_client: IsClient, tenant_client: IsClient, client: IsClient):
        """
        Should raise forbidden for users lacking proper credentials
        Or unauthenticated for non authenticated users
        """
       
        code = status.HTTP_403_FORBIDDEN

        res1 = caretaker_client.post(self.path, self.data)
        err1 = parse_error(res1, status_code=code)[0]
        assert err1["code"] == "permission_denied"

        res2 = tenant_client.post(self.path, self.data)
        err2 = parse_error(res2, status_code=code)[0]
        assert err2["code"] == "permission_denied"

        res3 = client.post(self.path, self.data)
        err3 = parse_error(res3, status.HTTP_401_UNAUTHORIZED)[0]
        assert err3["code"] == "not_authenticated"

    def test_apartment_list_serializer(self, manager_client: IsClient, apartment: Apartment):
        """
        Test list serializing is correct
        Bug: Without the current semester, the test was failing with 404 not found for the semester:
        Bug fixed: Tenancy prefetch does not rely wholy on the current semester, if not found it will just default to None
        """
        
        response = manager_client.get(self.path)
        data = parse_paginated_response(response, 1)["results"][0]
        assert data["apartment_id"] == apartment.pk, data
        assert data["apartment_name"] == apartment.apartment_name
        assert Decimal(data["rent"]) == apartment.rent
        assert data["occupied"] == False
        assert data["current_tenant"] == None

    def test_apartment_list_filters_based_on_role(self, manager_client: IsClient, caretaker_client: IsClient, user_client: IsClient, tenant_client: IsClient, client: IsClient, apartment_factory):
        """
        Manager or caretaker clients should be able to view all apartments
        Regular clients should only view rentable apartments
        """

        rentable_apartments = apartment_factory(quantity=2, overrides={"rentable": True})
        non_rentable_apartments = apartment_factory(quantity=2, overrides={"rentable": False})

        res1 = manager_client.get(self.path)
        parse_paginated_response(res1, 4)
        
        res2 = caretaker_client.get(self.path)
        parse_paginated_response(res2, 4)
        
        res3 = tenant_client.get(self.path)
        parse_paginated_response(res3, 2)
       
        res4 = user_client.get(self.path)
        parse_paginated_response(res4, 2)

        res5 = client.get(self.path)
        parse_paginated_response(res5, 2)

         