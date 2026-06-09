from typing import Protocol, Any, TypedDict, Mapping, TypeVar, TYPE_CHECKING
from typing_extensions import Unpack

if TYPE_CHECKING:
    from users.models import User
    from apartments.models import Apartment
    from datetime import date


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

class TenancyPayload(TypedDict):
    user: "User"
    apartment: "Apartment"
    start_date: "date"
    duration_months: int



# ----------------------- Clients  -----------------------
class IsError(TypedDict):
    code: str
    detail: str
    attr: str

class PaginatedResponse(TypedDict):
    count: int
    next: str | None
    previous: str | None
    results: list[dict[str, Any]]

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
    def force_authenticate(self, user: "User"): ...

_UserCreatePayload = Unpack[UserCreatePayload]


# ----------------------- Factory  -----------------------
T = TypeVar("T")

class Factory[T](Protocol):
    def __call__(self, *args, **kwargs) -> list[T]: ...