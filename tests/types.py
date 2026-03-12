from typing import Protocol, Any, TypedDict, Mapping
from typing_extensions import Unpack
from phonenumber_field.phonenumber import PhoneNumber



class UserCreatePayload(TypedDict):
    first_name: str
    last_name: str
    email: str
    password: str
    phone_number: PhoneNumber
    notify: bool


class UserUpdatePayload(TypedDict, total=False):
    first_name: str
    last_name: str
    bio: str
    backup_email: str
    phone_number: PhoneNumber


class IsResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def data(self) -> dict[str, Any]: ...


class IsClient(Protocol):
    def post(self, path: str, data: Mapping[str, Any]) -> IsResponse: ...
    def patch(self, path: str, data: Mapping[str, Any]) -> IsResponse: ...
    def put(self, path: str, data: Mapping[str, Any]) -> IsResponse: ...
    def get(self, path: str, data: Mapping[str, Any] | None = None) -> IsResponse: ...


_UserCreatePayload = Unpack[UserCreatePayload]