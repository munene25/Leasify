import pytest
from rest_framework.exceptions import ValidationError
from phonenumber_field.phonenumber import PhoneNumber
from users.models import User
from users.services import user_account_create, user_add_roles
from unittest.mock import patch
from .conftest import APIPayload


class TestAccountCreation:
    def test_account_creation_successful(self, payload: type[APIPayload]):
        """
        Test whether account creation is successfull and data is data matches
        """
        data: APIPayload = payload()
        user_account_create(**data.to_dict)
        user = User.objects.get(email=data.email)
        account = user.account
        # Assert reverse relationship
        assert user == account.user
        assert user.first_name == data.first_name
        assert user.last_name == data.last_name
        assert user.email == data.email
        # Assert password hashed correctly
        assert user.password != data.password
        assert account.phone_number == data.phone_number
        user.validate_password(data.password)
        assert User.objects.count() == 1

    def test_skip_mail_sending(
        self, payload: type[APIPayload], django_capture_on_commit_callbacks
    ):
        """
        Test whether mailing will be ignored with notify flag set to false
        """
        with django_capture_on_commit_callbacks() as callback:
            user_account_create(**payload().to_dict, notify=False)
        assert len(callback) == 0
        assert User.objects.count() == 1

    def test_mail_sent_upon_creation(
        self, payload: type[APIPayload], mailoutbox, django_capture_on_commit_callbacks
    ):
        """
        Test normal mail sending with notify flag set to True. Requires always eager for delay calls
        """
        from config.emails import EmailConfig

        config = EmailConfig.load()

        data = payload()
        with django_capture_on_commit_callbacks() as callback:
            user_account_create(**data.to_dict, notify=True)
        assert User.objects.count() == 1
        # Assert callback stores the mail sender
        assert len(callback) == 1
        # Execute callback
        callback[0]()
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [data.email]
        assert mail.from_email == config.default_from_email
        assert mail.subject == f"Welcome to {config.app_name}"
        assert "email-verify" in mail.body

    @patch("users.tasks.send_welcome_email.delay")
    def test_user_creation_success_on_cache_fail(
        self, mock, payload: type[APIPayload], django_capture_on_commit_callbacks
    ):
        """
        Regardless of cache failure i.e., celery cant reach broker, user should be created nonetheless
        """
        # Cache raises an exception
        mock.side_effect = Exception("Cache Down")
        with pytest.raises(Exception, match="Cache Down"):
            with django_capture_on_commit_callbacks(execute=True):
                data = payload()
                user_account_create(**data.to_dict)
        assert User.objects.count() == 1

    @pytest.mark.parametrize(
        "password,exception",
        [
            ("", "short"),
            ("foo", "short"),
            ("aeiou", "short"),
            ("1235151545", "numeric"),
        ],
    )
    def test_password_validators_fail(
        self, payload: type[APIPayload], password, exception
    ):
        """
        Different variations of passwords that should fail validation
        """
        data = payload(password=password)
        with pytest.raises(ValidationError) as exc:
            user_account_create(**data.to_dict)
        assert "password" in exc.value.detail
        assert exception in str(exc.value.detail)
        assert User.objects.count() == 0

    @pytest.mark.parametrize(
        "field,value,password",
        [
            ("first_name", "Bethany", "Bethany!"),
            ("last_name", "Florence", "_floReNCE_"),
            ("email", "benedicturs@gmail.com", "benedictorial"),
        ],
    )
    def test_password_validators_fail_for_user_similarity(
        self, payload: type[APIPayload], field, value, password
    ):
        """
        Different variations of passwords that should fail based on user similarity
        """

        data = payload(**{field: value, "password": password})
        with pytest.raises(ValidationError) as exc:
            user_account_create(**data.to_dict)
        assert "password" in exc.value.detail
        assert "similar" in str(exc.value.detail)
        assert User.objects.count() == 0

    @pytest.mark.parametrize(
        "field,value,duplicate",
        [
            ("email", "test@test.com", "test@test.com"),
            ("email", "phil@TEST.com", "phil@test.com"),
            (
                "phone_number",
                PhoneNumber.from_string("0710-100-100"),
                PhoneNumber.from_string("+254 710 100 100"),
            ),
        ],
    )
    def test_account_creation_fails_with_db_contraints(
        self, payload: type[APIPayload], field, value, duplicate
    ):
        """
        Test that db constraints with multiple
        """
        data1 = payload(**{field: value})
        data2 = payload(**{field: duplicate})

        user_account_create(**data1.to_dict)
        with pytest.raises(ValidationError) as exc:
            user_account_create(**data2.to_dict)

        assert User.objects.count() == 1
        assert field in exc.value.detail

    def test_phone_number_validator_fail_for_wrong_format(
        self, payload: type[APIPayload], wrong_phone_number
    ):
        """
        Assert wrong phone number formats and phone number regions are rejected
        """
        data = payload(phone_number=wrong_phone_number)
        with pytest.raises(ValidationError) as exc:
            user_account_create(**data.to_dict)
        assert "phone_number" in exc.value.detail
        assert User.objects.count() == 0


class TestRoleAssignment:
    def test_role_assignment_succeeds(self, user: User, get_role):
        """
        A single role should be successfully added to a user 
        It also should reflect in the user.role property
        """
        assert user.groups.count() == 0
        role = get_role()
        mod_user = user_add_roles(user=user, roles=[role])
        
        assert mod_user == user

        groups = mod_user.groups 

        assert groups.count() == 1
        assert role in groups.all()
        assert user.roles == [role.name]

    def test_multiple_role_assignment_succeeds(self, user: User, roles_list):
        assert user.groups.count() == 0
        mod_user = user_add_roles(user=user, roles=roles_list)
        
        assert mod_user.groups.count() == len(roles_list)
        assert list(mod_user.groups.all()) == roles_list
        assert user.roles == [r.name for r in roles_list]