import pytest
from dataclasses import dataclass, asdict, replace
from faker import Faker
from rest_framework.exceptions import ValidationError
from phonenumber_field.phonenumber import PhoneNumber
from users.models import User
from users.services import user_account_create
from unittest.mock import patch
fake = Faker("en_KE")


@dataclass
class UserData:
    # user_data
    first_name: str
    last_name: str
    email: str
    password: str
    # acc_data
    phone_number: PhoneNumber


@pytest.fixture
def user_data() -> UserData:
    return UserData(
        fake.first_name(),
        fake.last_name(),
        fake.email(),
        fake.password(),
        PhoneNumber.from_string(f"+2547{fake.random_number(digits=8, fix_len=True)}"),
    )


@pytest.mark.django_db
@patch("users.tasks.send_welcome_email.delay")
def test_account_creation_successful(_, user_data):
    user_data.email = "test@ExamplE.CoM"
    raw_password = user_data.password 

    # assert user & acc creation
    created_user = user_account_create(**asdict(user_data))
    user = User.objects.get(pk=created_user.pk)
    account = user.account # type: ignore

    # assert user_data matches
    assert user.first_name == user_data.first_name
    assert user.last_name == user_data.last_name
 
    # assert email normalisation
    assert user.email == "test@example.com"

    # assert password hashed
    assert user.password != raw_password
    assert user.check_password(raw_password) is True


    # assert account_data matches
    
    assert account.user == user
    assert account.phone_number == user_data.phone_number

@pytest.mark.django_db
@patch("users.tasks.send_welcome_email.delay")
def test_password_validators_work(_, user_data):
    user_data.password = str(user_data.email).split("@")[0]
    with pytest.raises(ValidationError) as exc:
        user_account_create(**asdict(user_data))
    assert "password" in str(exc.value)

@pytest.mark.django_db
@patch("users.tasks.send_welcome_email.delay")
def test_account_creation_fails_with_duplicate_phone_numbers(_, user_data):

    data2 = replace(user_data)
    data2.phone_number = user_data.phone_number
    user_account_create(**asdict(user_data))
    with pytest.raises(ValidationError):
        user_account_create(**asdict(data2))


@pytest.mark.django_db
@patch("users.tasks.send_welcome_email.delay")
def test_account_creation_fails_with_duplicate_emails(_, user_data):
    data2 = replace(user_data)
    user_account_create(**asdict(user_data))
    with pytest.raises(ValidationError):
        user_account_create(**asdict(data2))

@pytest.mark.django_db
@patch("users.tasks.send_welcome_email.delay")
def test_email_sender(mock_email, user_data):
    user = user_account_create(**asdict(user_data))
    mock_email.assert_called_once_with(user.pk)

@pytest.mark.django_db
@patch("users.tasks.send_welcome_email.delay", side_effect=Exception("Cache unavailable"))
def test_chache_down(mock_email, user_data):
    user = user_account_create(**asdict(user_data))
    with pytest.raises(Exception) as exc:
        mock_email.assert_called_once_with(user.pk)
    assert user is not None


