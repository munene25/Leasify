import pytest
from datetime import timedelta

from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction, IntegrityError

from rest_framework.exceptions import ValidationError
from leasify.users.models import User, EMAIL_COOLDOWN
from leasify.tests.types import Factory
from leasify.common.exceptions import PasswordError


class TestUserModel:

    def test_password_verify(self, user: User, password: str):
        """verify_password should not raise if password matches."""
        user.verify_password(password)

        with pytest.raises(PasswordError):
            user.verify_password("wrongpassword")

    def test_password_validate(self, user: User):
        """validate_password should raise based on password validators."""

        user.validate_password("StrongPassword123!")

        with pytest.raises(ValidationError, match="password"):
            user.validate_password("123")  # too short

        with pytest.raises(ValidationError, match="password"):
            user.validate_password(user.email.split("@")[0]) 
        
    def test_next_email_change_none_if_no_last_change(self, user: User):
        """next_email_change should return None if last_email_change is not set."""
        user.last_email_change = None
        assert user.next_email_change is None

    def test_next_email_change_returns_datetime_if_within_cooldown(self, user: User):
        """next_email_change should return datetime if cooldown has not passed."""
        now = timezone.now()
        user.last_email_change = now
        assert user.next_email_change is not None
        assert user.next_email_change == now + EMAIL_COOLDOWN

    def test_next_email_change_returns_none_if_cooldown_passed(self, user: User):
        """next_email_change should return None if cooldown has passed."""
        user.last_email_change = timezone.now() - EMAIL_COOLDOWN - timedelta(days=1)
        assert user.next_email_change is None

    def test_full_name(self, user: User):
        """full_name should return first and last name."""
        assert user.full_name == user.first_name + " " + user.last_name

    def test_role_property(self, superuser: User, manager_user: User, caretaker_user: User, tenant_user: User, user: User):
        """Roles should align with the users roles"""
        assert superuser.role == "superuser"
        assert manager_user.role == "manager"
        assert caretaker_user.role == "caretaker"
        assert tenant_user.role == "tenant"
        assert user.role == "regular"

    def test_db_constraints(self, user: User, password: str):
        """Two users cannot share the same email."""
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create(email=user.email, password=password, first_name="", last_name="")


    @pytest.mark.parametrize(
        "overrides,match",
        [
            ({"email": ""}, "email"),
            ({"email": "not-an-email"}, "email"),
            ({"first_name": "123"}, "first_name"),
            ({"last_name": "123"}, "last_name"),
        ],
    )
    def test_non_nullable_fields(self, overrides: dict, match: str):
        """Call full_clean on a model and assert whether it raises."""
        default = {
            "email": "test@email.com",
            "first_name": "Test",
            "last_name": "User",
        }
        with pytest.raises(ValidationError, match=match):
            User(**{**default, **overrides}).full_clean()

class TestAccountModel:

    def test_account_created_with_user(self, user: User):
        """Account should be linked to user."""
        assert user.account.user == user

    def test_phone_number_unique(self, user_factory: Factory[User]):
        """Two accounts cannot share the same phone number."""
        user1 = user_factory(phone_number="+254700100100")[0]
        user2 = user_factory(phone_number="+254700100101")[0]

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                user2.account.phone_number = user1.account.phone_number
                user2.account.save()

class TestUserManager:

    def test_superuser_creation(self, password: str):
        """Should be superuser, active, staff. Does not require phone number."""
        user = User.objects.create_superuser(
            email="ADMIN@LEASIFY.COM",
            password=password,
            first_name="Admin",
            last_name="User",
        )
        assert user.is_superuser is True
        assert user.is_active is True
        assert user.email == "admin@leasify.com"  # normalized

    def test_email_normalization(self, password: str):
        """Email should be lowercased and stripped on creation."""
        user = User.objects.create_superuser(
            email="  EDWIN@LEASIFY.COM  ",
            password=password,
            first_name="Admin",
            last_name="User",
        )
        assert user.email == "edwin@leasify.com"