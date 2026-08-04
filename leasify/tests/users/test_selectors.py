from functools import partial
from unittest.mock import MagicMock

import pytest

from django.utils import timezone
from django.core.cache import cache
from django.db.models import QuerySet
from django.urls import reverse
from django.core.mail import EmailMessage

from rest_framework.exceptions import NotFound

from leasify.users.models import User, Account, EMAIL_COOLDOWN
from leasify.users.selectors import *
from leasify.tests.types import Factory


class TestUserListFor:
    def test_user_list_filtering(self, user_factory: Factory[User], superuser: User):
        """Users should be filterable by is_active and searchable fields."""
        user1 = user_factory(first_name="John", last_name="Doe")[0]
        user2 = user_factory(first_name="Jane", last_name="Smith", is_active=False)[0]
        user3 = user_factory(first_name="Mike", last_name="Jones", phone_number="0791200200", is_active=False)[0]
        user4 = user_factory(first_name="Felix", last_name="Brown", is_active=False)[0]
        user5 = user_factory(first_name="Felix", last_name="Wilson", email="peny@gmail.com")[0]

        fetch = partial(user_list_for, user=superuser)

        # -- Filter by is_active --
        assert fetch(filters={"is_active": False}).count() == 3

        # -- Search by similar first name --
        assert fetch(filters={"search": user4.first_name}).count() == 2

        # -- Search by last name --
        assert fetch(filters={"search": user1.last_name}).count() == 1

        # -- Search by phone number --
        phone_number = user3.account.phone_number
        assert phone_number is not None
        assert fetch(filters={"search": phone_number[2:]}).count() == 1

        # -- Search by email --
        assert fetch(filters={"search": user5.email[2:]}).count() == 1

        # -- Multiple filters --
        fetched = fetch(filters={"search": user4.first_name, "is_active": False})
        assert fetched.count() == 1
        assert user4 in fetched

    def test_role_based_filtering(
        self,
        superuser: User,
        manager_user: User,
        caretaker_user: User,
        tenant_user: User,
        user: User,
    ):
        """Users should only see roles permitted by UserFilterPolicy."""

        superuser_list = user_list_for(user=superuser)
        assert {manager_user, caretaker_user, tenant_user, user} == set(superuser_list)

        manager_user_list = user_list_for(user=manager_user)
        assert {caretaker_user, tenant_user, user} == set(manager_user_list)

        caretaker_list = user_list_for(user=caretaker_user)
        assert {tenant_user, user} == set(caretaker_list)

        assert user_list_for(user=tenant_user).count() == 0
        assert user_list_for(user=user).count() == 0


class TestUserGet:

    def test_success(self, user: User):
        assert user_get(user.pk) == user

    def test_not_found(self):
        with pytest.raises(NotFound):
            user_get(999)


class TestUserGetByEmail:

    def test_success(self, user: User):
        assert user_get_by_email(user.email) == user

    def test_normalizes_email(self, user: User):
        assert user_get_by_email(user.email.upper()) == user

    def test_not_found(self):
        with pytest.raises(NotFound):
            user_get_by_email("nonexistent@example.com")


class TestUserGetFor:

    def test_role_based_access(
        self,
        superuser: User,
        manager_user: User,
        caretaker_user: User,
        tenant_user: User,
        user: User,
    ):
        """Each role can only access users permitted by UserFilterPolicy."""
        # manager can get caretaker, tenant, regular
        assert user_get_for(user=manager_user, user_id=caretaker_user.pk) == caretaker_user
        assert user_get_for(user=manager_user, user_id=tenant_user.pk) == tenant_user
        assert user_get_for(user=manager_user, user_id=user.pk) == user

        # caretaker can get tenant and regular
        assert user_get_for(user=caretaker_user, user_id=tenant_user.pk) == tenant_user
        assert user_get_for(user=caretaker_user, user_id=user.pk) == user

        # caretaker cannot get manager or superuser
        with pytest.raises(NotFound):
            user_get_for(user=caretaker_user, user_id=manager_user.pk)
        with pytest.raises(NotFound):
            user_get_for(user=caretaker_user, user_id=superuser.pk)

        # tenant can only get themselves
        assert user_get_for(user=tenant_user, user_id=tenant_user.pk) == tenant_user
        with pytest.raises(NotFound):
            user_get_for(user=tenant_user, user_id=user.pk)

        # regular can only get themselves
        assert user_get_for(user=user, user_id=user.pk) == user
        with pytest.raises(NotFound):
            user_get_for(user=user, user_id=tenant_user.pk)


class TestGetGroup:

    def test_success(self):
        group = Group.objects.create(name="test_group")
        assert get_group("test_group") == group

    def test_not_found(self):
        with pytest.raises(NotFound):
            get_group("nonexistent")

    def test_cached(self, django_assert_num_queries):
        """Multiple calls should result in only one query due to lru_cache."""
        Group.objects.create(name="cached_group")
        with django_assert_num_queries(1):
            get_group("cached_group")
            get_group("cached_group")
            get_group("cached_group")
