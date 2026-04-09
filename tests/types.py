from typing import Protocol, Any, TypedDict, Mapping
from typing_extensions import Unpack



class UserCreatePayload(TypedDict):
    first_name: str
    last_name: str
    email: str
    password: str
    phone_number: str
    notify: bool


class UserUpdatePayload(TypedDict, total=False):
    first_name: str
    last_name: str
    bio: str
    backup_email: str
    phone_number: str


class IsResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def data(self) -> dict[str, Any]: ...
  
    @property
    def cookies(self) -> dict[str, Any]: ...

    @property
    def headers(self) -> dict[str, Any]: ...


class IsClient(Protocol):
    def post(self, path: str, data: Mapping[str, Any], **extra) -> IsResponse: ...
    def patch(self, path: str, data: Mapping[str, Any], **extra) -> IsResponse: ...
    def put(self, path: str, data: Mapping[str, Any], **extra) -> IsResponse: ...
    def get(self, path: str, data: Mapping[str, Any] | None = None,) -> IsResponse: ...
    def delete(self, path: str, **extra) -> IsResponse: ...
    def login(self, **credentials: str) -> bool: ...

_UserCreatePayload = Unpack[UserCreatePayload]