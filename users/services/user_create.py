from phonenumber_field.phonenumber import PhoneNumber
from users.models import User
from users.utils import send_verification_email
from ..mixins import UserFieldValidatorMixin


class UserCreateService(UserFieldValidatorMixin):
    def __init__(
        self,
        *,
        email: str,
        phone_number: PhoneNumber | str,
        password: str,
        username: str,
        first_name: str,
        last_name: str,
        verified: bool = False,
        silence: bool = True,
    ):
        self.email = email
        self.phone_number = phone_number
        self.password = password
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.verified = verified
        self.silence = silence

    def create(self) -> None:
        # Verify structure before
        self._validate_username_length(username=self.username)
        self._validate_phone_number_format(phone_number=self.phone_number)
        # Email is structure is already verified on the serializer
        self._validate_uniqueness(
            username=self.username, email=self.email, phone_number=self.phone_number
        )
        # Create user first to validate password
        self.user = User(
            email=self.email,
            username=self.username,
            phone_number=self.phone_number,
            first_name=self.first_name,
            last_name=self.last_name,
        )
        self._validate_password_format(password=self.password, user=self.user)
        self.user.set_password(self.password)
        self.user.verified = True if self.verified else False
        self.user.save()
        if not self.silence and not self.verified:
            send_verification_email(user=self.user)
        return self.user
