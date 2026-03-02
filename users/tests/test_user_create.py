from dataclasses import asdict
from .conftest import UserData
import pytest
from rest_framework.exceptions import ValidationError
from phonenumber_field.phonenumber import PhoneNumber
from users.models import User
from users.services import user_account_create
from unittest.mock import patch
from django.conf import settings


@pytest.fixture
def userdata():
    # Returns a creator function
    def _create(**overrides) -> UserData:
        userdata = UserData()
        if overrides:
            for k, v in overrides.items():
                setattr(userdata, k, v)
        return userdata

    return _create


class TestSuccessfulAccountCreation:
    def test_account_creation_successful(self, userdata):
        """Test whether account creation is successfull and data is data matches"""
        data = userdata()
        user_account_create(**asdict(data))
        user = User.objects.get(email=data.email)
        account = user.account # type: ignore
        assert user == account.user

        assert user.first_name == data.first_name
        assert user.last_name == data.last_name
        assert user.email == data.email
        assert user.password != data.password
        assert user.account.phone_number == data.phone_number # type: ignore

        user.check_password(data.password)

        assert User.objects.count() == 1

    def test_skip_mail_sending(self, mod, django_capture_on_commit_callbacks):
        """Test whether mail will be ignored with notify flag added"""
        with django_capture_on_commit_callbacks() as callback:
            user_account_create(**asdict(mod()), notify=False)
        assert len(callback) == 0
        assert User.objects.count() == 1

    def test_mail_sent_upon_creation(
        self, mod, mailoutbox, django_capture_on_commit_callbacks
    ):
        """Test normal mail sending with notify flag set to True. Requires always eager for delay calls"""

        data: UserData = mod()
        with django_capture_on_commit_callbacks() as callback:
            user_account_create(**asdict(data), notify=True)
        assert len(callback) == 1
        # Execute callback
        callback[0]()
        assert len(mailoutbox) == 1
        sent = mailoutbox[0]
        assert sent.to == [data.email]
        assert sent.from_email == settings.DEFAULT_FROM_EMAIL
        assert User.objects.count() == 1

    @patch("users.tasks.send_welcome_email.delay")
    def test_user_creation_success_on_cache_fail(
        self, mock, mod, django_capture_on_commit_callbacks
    ):
        """Regardless of cache failure i.e., celery cant reach broker, user should be created nonetheless"""

        mock.side_effect = Exception("Cache Down")
        with pytest.raises(Exception, match="Cache Down"):
            with django_capture_on_commit_callbacks(execute=True):
                data = asdict(mod())
                user_account_create(**data)

        assert User.objects.count() == 1


class TestPasswordValidators:
    @pytest.mark.parametrize(
        "password,exception",
        [
            ("", "short"),
            ("foo", "short"),
            ("aeiou", "short"),
            ("1235151545", "numeric"),
        ],
    )
    def test_password_validators_fail(self, mod, password, exception):
        """Different variations of passwords that should be fail validation"""

        data = mod(password=password)
        with pytest.raises(ValidationError) as exc:
            user_account_create(**asdict(data))
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
        self, mod, field, value, password
    ):
        """Different variations of passwords that should fail based on user similarity"""

        data = mod(**{field: value, "password": password})
        with pytest.raises(ValidationError) as exc:
            user_account_create(**asdict(data))
        assert "password" in exc.value.detail
        assert "similar" in str(exc.value.detail)
        assert User.objects.count() == 0

    @pytest.mark.parametrize(
        "phone_number",
        [
            PhoneNumber.from_string("+254 000 100 100"),
            PhoneNumber.from_string("+255 700 100 100"),
            PhoneNumber.from_string("+104 700 100 100"),
        ],
    )
    def test_phone_number_validator_fail_for_wrong_format(self, mod, phone_number):
        """Assert wrong phone number formats and phone number regions are rejected"""

        data = mod(phone_number=phone_number)
        with pytest.raises(Exception) as exc:
            user_account_create(**asdict(data))
        assert "phone_number" in str(exc.value)
        assert User.objects.count() == 0


class TestDBConstraints:
    @pytest.mark.parametrize(
        "field,value,duplicate",
        [
            ("email", "test@test.com", "test@test.com"),
            ("email", "phil@TEST.com", "phil@test.com"),
            (
                "phone_number",
                PhoneNumber.from_string("0710-100-100"),
                PhoneNumber.from_string("254710100100"),
            ),
            (
                "phone_number",
                PhoneNumber.from_string("0710100100"),
                PhoneNumber.from_string("+254-710-100-100"),
            ),
        ],
    )
    def test_account_creation_fails_with_db_contraints(
        self, mod, field, value, duplicate
    ):
        data1 = asdict(mod(**{field: value}))
        data2 = asdict(mod(**{field: duplicate}))
        print(data1["email"])
        print(data2["email"])

        user_account_create(**data1)
        with pytest.raises(ValidationError) as exc:
            user_account_create(**data2)

        assert User.objects.count() == 1
        assert field in exc.value.detail
