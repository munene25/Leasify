import pytest
from decimal import Decimal
from typing import Any, TYPE_CHECKING
from rest_framework import status
from apartments.models import Apartment
from tests.types import IsClient, Factory
from tests.helpers import parse_error, parse_message, parse_paginated_response

if TYPE_CHECKING:
    from semesters.models import Semester
    from users.models import User

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

    @pytest.mark.parametrize(
        "field,value",
        (("block", "old"), ("block", "new"), ("unit_number", "five"), ("rent", "20 thousand"), ("rentable", "okay")),
    )
    def test_apartment_creation_serializer_validation(self, field: str, value: str, manager_client: IsClient):
        """
        Test various validation failures are flagged by serializer
        """

        code = status.HTTP_400_BAD_REQUEST
        data = self.data.copy()
        data[field] = value

        response = manager_client.post(self.path, data)
        error = parse_error(response, code, err_type="validation_error")[0]
        assert error["attr"] == field

    def test_apartment_creation_authorization(
        self, caretaker_client: IsClient, tenant_client: IsClient, client: IsClient
    ):
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

    def test_apartment_list_filters_based_on_role(
        self,
        manager_client: IsClient,
        caretaker_client: IsClient,
        user_client: IsClient,
        tenant_client: IsClient,
        client: IsClient,
        apartment_factory: Factory[Apartment],
    ):
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

    @pytest.mark.parametrize(
        "field,query_param,value,expected",
        [
            ("block", "search", "NEW", 1),
            ("block", "search", "OLD", 6),
            ("rent", "search", Decimal(15_000), 1),
            ("rent", "search", Decimal(12_000), 6),
            ("unit_number", "search", 100, 1),
            ("rentable", "rentable", False, 1),
            ("rentable", "rentable", False, 1),
            ("rent", "rent_min", Decimal(15_000), 1),
            ("rent", "rent_max", Decimal(8_000), 1),
        ],
    )
    def test_apartment_list_filter_sets(
        self,
        field: str,
        query_param: str,
        value: Any,
        expected: int,
        manager_client: IsClient,
        apartment_factory: Factory[Apartment],
    ):
        """
        Filters for fields should work correctly:
        search: block, unit_number, rent
        rent_min and rent_max
        rentable bool
        """

        other_apartments = apartment_factory(
            quantity=5, ordered=True, overrides={"block": "OLD", "rent": Decimal(12_000), "rentable": True}
        )
        apartment = apartment_factory(overrides={field: value}, quantity=1)[0]
        path = self.path + f"?{query_param}={value}"

        response = manager_client.get(path)
        data = parse_paginated_response(response, expected)
        filtered = data["results"][0]
        assert filtered["apartment_id"] == apartment.pk

    def test_apartment_pagination(self, apartment_factory: Factory[Apartment], override_pagination: int, caretaker_client: IsClient):
        """
        Pages should reflect whats defined in the restframework settings
        """

        base_url = lambda page: f"{self.path}?page={page}"
        next_url = lambda page: f"http://testserver/apartments/?page={page}"

        q: int = 3
        apartments = apartment_factory(quantity=q, ordered=True)
        # Reverse coz list is sorted by created at

        page1 = caretaker_client.get(self.path)
        data1 = parse_paginated_response(page1, q)
        assert data1["previous"] is None
        assert data1["next"] == next_url(2)
        assert len(data1["results"]) == override_pagination
        assert data1["results"][0]["apartment_id"] == apartments[2].pk
        assert data1["results"][1]["apartment_id"] == apartments[1].pk

        page2 = caretaker_client.get(base_url(2))
        data2 = parse_paginated_response(page2, q)
        assert data2["results"][0]["apartment_id"] == apartments[0].pk
        assert data2["next"] == None

    @pytest.mark.parametrize(
        "field,first,last",
        [
            ("rent", 3, 1),
            ("-rent", 1, 3),
            ("-unit_number", 3, 2),
            ("unit_number", 2, 3),
        ],
    )
    def test_ordering_of_filtersets(self, field: str, first: int, last: int, apartment_factory: Factory[Apartment], manager_client: IsClient):
        """Ordering by price or unit_number should possible"""

        apartment1 = apartment_factory(overrides={"unit_number": 20, "rent": Decimal(30_000)})[0]
        apartment2 = apartment_factory(overrides={"unit_number": 10, "rent": Decimal(20_000)})[0]
        apartment3 = apartment_factory(overrides={"unit_number": 30, "rent": Decimal(10_000)})[0]

        apts = [apartment1, apartment2, apartment3]

        response1 = manager_client.get(f"{self.path}?order_by={field}")
        data1 = parse_paginated_response(response1, 3)["results"]
        assert data1[0]["apartment_id"] == apts[first - 1].pk
        assert data1[-1]["apartment_id"] == apts[last - 1].pk


class TestApartmentDetailUpdateDeleteView:

    patch_data = {"block": Apartment.ApartmentChoices.OLD, "unit_number": 4, "rentable": False, "rent": 30_000}
    
    @staticmethod
    def path(apt):
        return f"/apartments/{apt.pk}/"

    
    def test_apartment_detail_correctly_serializes_apartment(
        self,
        user: "User",
        current_semester: "Semester",
        apartment: Apartment,
        manager_client: IsClient,
        django_assert_num_queries,
    ):
        """
        Checking especially for current tenant
        """
        from tenancy.models import Tenancy

        response1 = manager_client.get(self.path(apartment))
        data1 = parse_message(response1)

        assert data1["apartment_id"] == apartment.pk
        assert data1["block"] == apartment.block
        assert data1["unit_number"] == apartment.unit_number
        assert Decimal(data1["rent"]) == apartment.rent
        assert data1["rentable"] == apartment.rentable
        assert data1["current_tenant"] == None

        tenant = Tenancy.objects.create(
            total_paid=0, semester_id=current_semester.pk, apartment_id=apartment.pk, user_id=user.pk
        )

        # Queries:
        # 1. groups -> exclusions
        # 2. apartment -> main qs
        # 3. tenancy -> current_tenant
        with django_assert_num_queries(3):
            response2 = manager_client.get(self.path(apartment))

        data2 = parse_message(response2)
        assert data2["apartment_id"] == apartment.pk
        assert data2["current_tenant"] == tenant.user.full_name

    @pytest.mark.parametrize(
        "selected,get,patch,delete",
        [
            ("manager_client", status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            ("caretaker_client", status.HTTP_200_OK, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN),
            ("tenant_client", status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            ("user_client", status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            ("client", status.HTTP_401_UNAUTHORIZED, status.HTTP_401_UNAUTHORIZED, status.HTTP_401_UNAUTHORIZED),
        ],
    )
    def test_apartment_detail_update_delete_authorization_and_authentication(
        self,
        selected: str,
        get: int,
        patch: int,
        delete: int,
        apartment: Apartment,
        manager_client: IsClient,
        caretaker_client: IsClient,
        tenant_client,
        user_client: IsClient,
        client: IsClient,
    ):
        selected_client: IsClient = {
            "manager_client": manager_client,
            "caretaker_client": caretaker_client,
            "tenant_client": tenant_client,
            "user_client": user_client,
            "client": client,
        }[selected]
        
        assert selected_client.get(self.path(apartment)).status_code == get
        assert selected_client.patch(self.path(apartment), self.patch_data).status_code == patch
        assert selected_client.delete(self.path(apartment)).status_code == delete


    def test_apartment_update_successful(self, apartment: Apartment, manager_client: IsClient):
        """
        An apartment can be updated correctly
        """
        
        response = manager_client.patch(self.path(apartment), self.patch_data)
        data = parse_message(response)
        apartment.refresh_from_db() # type: ignore
        assert data["apartment_id"] == apartment.pk
        assert data["unit_number"] == apartment.unit_number
        assert data["rentable"] == apartment.rentable
        assert Decimal(data["rent"]) == apartment.rent
    
    @pytest.mark.parametrize(
            "field,value",
            [
                ("block", "free"),
                ("unit_number", "free"),
                ("rent", 1000000000),
                ("rentable", "null"),
            ]
    )
    def test_apartment_update_serializer_raises_on_invalid_fields(self, field: str, value: Any, apartment: Apartment, caretaker_client: IsClient):
        """
        Raises validation Error on wrong formatted fields
        """

        patch_data = self.patch_data.copy()
        patch_data[field] = value
        response = caretaker_client.patch(self.path(apartment), patch_data)
        error = parse_error(response, status.HTTP_400_BAD_REQUEST, "validation_error", 1)[0]
        assert error["attr"] == field

    def test_apartment_deletion_successful(self, apartment: Apartment, manager_client: IsClient):
        """
        Apartment can be deleted if it does not have tenancies associated with it.
        """

        response = manager_client.delete(self.path(apartment))
        data = parse_message(response, status.HTTP_204_NO_CONTENT)

    def test_apartment_deletion_fails_if_it_has_associated_tenancies(self, user: "User", current_semester: "Semester", manager_client: IsClient, apartment: Apartment):
        """
        First assign a tenancy to the apartment then try deletion
        Should fail
        """
        from tenancy.models import Tenancy

        tenant = Tenancy.objects.create(user=user, semester=current_semester, apartment=apartment, total_paid=0)
        assert Tenancy.objects.count() == 1
        response = manager_client.delete(self.path(apartment))
        parse_error(response, status.HTTP_400_BAD_REQUEST, err_type="validation_error")

    
    def test_not_found_for_apartment_ids(self, caretaker_client: IsClient):
        """Not found is raised"""

        res = caretaker_client.get("/apartments/22/")
        assert parse_error(res, status.HTTP_404_NOT_FOUND)

    
class TestApartmentOverviewView:
    
    @staticmethod
    def path(semester: "Semester"):
        return f"/apartments/overview?semester={semester.pk}"
    
    def test_overview_works_based_on_semesters(self, user_factory: Factory["User"], semester_factory: Factory["Semester"], apartment_factory: Factory[Apartment], manager_client: IsClient):
        """should return the correct values"""

        from tenancy.models import Tenancy

        semesters = semester_factory(2026, 2026)
        
        users = user_factory(quantity=5)
        
        apartments = [
            *apartment_factory(quantity=2, overrides={"rent": 12000, "rentable": True}),
            *apartment_factory(quantity=3, overrides={"rent": 18000, "rentable": False}),
            *apartment_factory(quantity=2, overrides={"rent": 17000, "rentable": True}),
        ]
        
        sem_one_tenancies = [Tenancy(apartment=apartments[i], semester=semesters[0], user=users[i], total_paid=0) for i, _ in enumerate(range(3))]
        sem_two_tenancies = [Tenancy(apartment=apartments[i], semester=semesters[1], user=users[i], total_paid=0) for i, _ in enumerate(range(5))]
        Tenancy.objects.bulk_create([*sem_two_tenancies, *sem_one_tenancies])
        
        response1 = manager_client.get(self.path(semesters[1]))
        data1 = parse_message(response1)
        total_rent = sum(apt.rent for apt in apartments)
        assert data1["total_apartments"] == len(apartments)
        assert data1["occupied"] == len(sem_two_tenancies)
        assert data1["rentable"] == 4
        assert Decimal(data1["average_rent"]) == total_rent/len(apartments)
        assert Decimal(data1["min_rent"]) == Decimal(12000)
        assert Decimal(data1["max_rent"]) == Decimal(18000)
        assert Decimal(data1["expected_income"]) == total_rent

        # assert that the current semester will be used
        response2 = manager_client.get("/apartments/overview")
        data2 = parse_message(response2)
        assert data2["occupied"] == len(sem_one_tenancies)