from dataclasses import dataclass
from threading import Lock
from typing import Optional

from locust_async_chat.config import LoadTestConfig
from locust_async_chat.models.login import LoginRequestPayload


@dataclass
class TestUser:
    index: int
    given_name: str
    surname: str
    email: str
    locale: str

    def to_login_payload(self) -> LoginRequestPayload:
        return LoginRequestPayload(
            given_name=self.given_name,
            surname=self.surname,
            email=self.email,
            avatar_url="https://www.gravatar.com/avatar/00000000000000000000000000000000.png?s=200&d=mm",
            locale=self.locale,
            locale_origin="apiRequest",
        )


class UserPool:
    def __init__(self, config: LoadTestConfig):
        self._config = config
        self._users: list[TestUser] = []
        self._lock = Lock()
        self._next_index = 1

    def _build_user(self, index: int) -> TestUser:
        surname = f"{self._config.user_surname_prefix}{index}"
        email = (
            f"{self._config.user_given_name.lower()}."
            f"{surname.lower()}@{self._config.user_email_domain}"
        )
        return TestUser(
            index=index,
            given_name=self._config.user_given_name,
            surname=surname,
            email=email,
            locale=self._config.user_locale,
        )

    def acquire(self) -> TestUser:
        with self._lock:
            user = self._build_user(self._next_index)
            self._users.append(user)
            self._next_index += 1
            return user

    @property
    def size(self) -> int:
        return len(self._users)

    def get_user(self, index: int) -> Optional[TestUser]:
        if 0 <= index < len(self._users):
            return self._users[index]
        return None

    def reset(self) -> None:
        """Reset the user pool counter to start from 1 for a new test run."""
        with self._lock:
            self._next_index = 1
            self._users.clear()


_pool: Optional[UserPool] = None


def get_user_pool() -> Optional[UserPool]:
    return _pool


def set_user_pool(pool: UserPool) -> None:
    global _pool
    _pool = pool
