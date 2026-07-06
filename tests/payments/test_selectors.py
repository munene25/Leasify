import pytest
from functools import partial
from rest_framework.exceptions import NotFound
from tests.types import Factory
from users.models import User
from billing.models import BillingPeriod as BP
from billing.choices import BillingStatus as BS
from tenancy.models import Tenancy
from payments.models import Payment
from payments.selectors import *
from payments.choices import PaymentMode as PM, PaymentStatus as PS

class TestBaseQS:
    def test_no_queries(self, payment_factory: Factory[Payment], django_assert_num_queries):
        """
        Should match the expected query count
        1. Payment + JOINS
        """
        payment = payment_factory(2)
        with django_assert_num_queries(1):
            fetched = BASE_QS.get(pk=1)
            assert fetched == payment[0]
            assert fetched.billing is not None
            assert fetched.billing.tenancy is not None
            assert fetched.billing.tenancy.user is not None



class TestPaymentListFor:
    def test_role_based_filtering(
        self,
        superuser: User,
        manager_user: User,
        caretaker_user: User,
        user_factory: Factory[User],
        billing_factory: Factory[BP],
        payment_factory: Factory[Payment],
        tenancy_factory: Factory[Tenancy]
    ):
        """Role based filtering based on user"""
        users = user_factory(3)
        tenancies = tenancy_factory(users=users)
        bill1 = billing_factory(tenancy=tenancies[0], statuses=[BS.UNPAID])[0]
        bill2 = billing_factory(tenancy=tenancies[1], statuses=[BS.UNPAID])[0]
        # Two payments for user1
        payment_factory(billing=bill1, statuses=[PS.FAILED, PS.SUCCESS])
        # One payemnt for user2
        payment_factory(billing=bill2, statuses=[PS.PENDING])
        assert payment_list_for(user=superuser).count() == 3
        assert payment_list_for(user=manager_user).count() == 3
        assert payment_list_for(user=caretaker_user).count() == 3
        assert payment_list_for(user=users[0]).count() == 2
        assert payment_list_for(user=users[1]).count() == 1

    def test_filtering(self, superuser: User, user_factory: Factory[User], payment_factory: Factory[Payment], tenancy_factory: Factory[Tenancy], billing_factory: Factory[BP]):
        """Test filtering based on query params"""
        user1 = user_factory(first_name="Adam", last_name="Kuria")
        user2 = user_factory(first_name="Janice", last_name="Akinyi")
        user3 = user_factory(first_name="Philip", last_name="Momanyi")
        billing1 = billing_factory(tenancy=tenancy_factory(users=user1)[0])[0]
        billing2 = billing_factory(tenancy=tenancy_factory(users=user2)[0])[0]
        payment_factory(billing=billing1, statuses=[PS.FAILED, PS.SUCCESS, PS.PENDING], phone_number="0710 130 000")
        payment_factory(billing=billing2, statuses=[PS.SUCCESS, PS.PENDING])
        payment_factory(payment_mode=PM.CASH, recorded_by=user3[0], receipt_no="XYZ2040")

        payment_list = partial(payment_list_for, user=superuser)
        # Filter on billing
        assert payment_list(filters={"billing": 1}).count() ==  3
        assert payment_list(filters={"billing": 2}).count() ==  2
        # Filter on status
        assert payment_list(filters={"status": PS.SUCCESS}).count() == 3
        # Filter on payment_mode
        assert payment_list(filters={"payment_mode": PM.CASH}).count() == 1
        assert payment_list(filters={"payment_mode": PM.MPESA}).count() == 5
        # Filter on phone_number
        assert payment_list(filters={"search": "710130000"}).count() == 3
        # Filter on receipt_no
        assert payment_list(filters={"search": "XYZ2040"}).count() == 1
        # Filter on recorded_by
        assert payment_list(filters={"search": "philip"}).count() == 1
        # filter on payee
        assert payment_list(filters={"search": "adam"}).count() == 3
        assert payment_list(filters={"search": "akin"}).count() == 2


class TestPaymentGetFor:
    def test_raises_not_found(self, manager_user: User):
        """Should raise a not found if there is not payment found"""
        with pytest.raises(NotFound, match="Payment not found"):
            payment_get_for(user=manager_user, payment_id=1)
        
    
    def test_role_based_filtering(self, manager_user: User, caretaker_user: User, superuser: User, payment_factory: Factory[Payment]):
        """Should filter gets based on the type of user"""
        user1 = payment_factory(1)[0].billing.tenancy.user
        user2 = payment_factory(1)[0].billing.tenancy.user
        assert payment_get_for(user=manager_user, payment_id=1) is not None
        assert payment_get_for(user=caretaker_user, payment_id=1) is not None
        assert payment_get_for(user=superuser, payment_id=1) is not None
        with pytest.raises(NotFound, match="Payment not found"):
            payment_get_for(user=user1, payment_id=2)
        with pytest.raises(NotFound, match="Payment not found"):
            payment_get_for(user=user2, payment_id=1)
    
            
