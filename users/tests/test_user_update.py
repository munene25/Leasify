from __future__ import annotations
import pytest
from users.models import User
from rest_framework.exceptions import ValidationError
from users.services.update import user_update
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conftest import APIPayload


class TestUserUpdate:
    def test_updating_existing_data_succeeds(
        self, payload: type[APIPayload], user: User
    ):
        data = payload()
        mod_user = user_update(user, **data.to_dict)
        mod_account = mod_user.account
        # assert same user returned
        assert user == mod_user
        assert user.account == mod_account

        # assert persistence
        assert User.objects.get(pk=mod_user.pk) == user
        assert mod_user.first_name == data.first_name
        assert mod_user.last_name == data.last_name
        assert mod_account.phone_number == data.phone_number

        # Assert key fields not mod_user
        assert mod_user.email == user.email
        assert mod_user.password == user.password

    def test_email_validation(self, user):
        backup_email = "test@GMAIl.com"
        mod_user = user_update(user, backup_email=backup_email)
        mod_acc = mod_user.account
        assert mod_acc.backup_email == "test@gmail.com"

        wrong_format = "test@gmail"
        with pytest.raises(ValidationError) as exc:
            user_update(mod_user, backup_email=wrong_format)
        assert "backup_email" in exc.value.detail

        db_version = User.objects.get(pk=user.pk)
        
        assert db_version.account.backup_email == "test@gmail.com"



    @pytest.mark.parametrize(
        "field, model, value",
        [
            ("backup_email", "account", "test@test.com"),
            ("bio", "account", "This is a test bio"),
            ("last_name", "user", "Guest"),
            ("first_name", "user", "Mike"),
        ],
    )
    def test_inserting_new_data_succeeds(self, field, model, value, user):
        """
        Originally, these fields are marked as null, should be able to modify
        """
        mod_user = user_update(user, **{field: value})
        mod_account = mod_user.account
        obj = mod_user if model == "user" else mod_account
        assert getattr(obj, field) == value



    @pytest.mark.parametrize(
        "tel",
        [
            "+101-999-222-222",
            "+255-222-222-222",
            "+256-722-222-222",
            "+255712345678"
        ],
    )
    def test_phone_number_validators_fail(self, phone_no, tel, user):
        """Phone numbers that should be rejected because of either incorrect countrycode or wrong format"""
        with pytest.raises(ValidationError) as exc:
            phone = phone_no(tel)
            user_update(user, **{"phone_number": phone})
            
        assert "phone_number" in exc.value.detail
        assert exc.value.detail is 0



    @pytest.mark.parametrize(
            "field,value,exception",
        [   
            ("first_name", "E", "Ensure this value has at least 2 characters"),
            ("last_name", "M", "Ensure this value has at least 2 characters"),
            ("first_name", "Edwin_", "field accepts only alphabetic characters"),
            ("last_name", "Munene!", "field accepts only alphabetic characters"),
        ]
    )
    def test_null_name_fields_are_not_allowed(self, user, field, value, exception):
        with pytest.raises(ValidationError) as exc:
            user_update(user, **{field: value})
        assert exception in str(exc.value.detail)
