"""Login, token renewal, and 401 retry against a fake HTTP session."""

import asyncio
import base64
import json
import time
from contextlib import asynccontextmanager
from typing import Any

import pytest

from custom_components.kyiv_vodokanal.api import (
    KyivVodokanalApi,
    KyivVodokanalAuthError,
)
from custom_components.kyiv_vodokanal.api.const import PATHS, TOKEN_RENEW_MARGIN

LOGIN = PATHS["login"]
METERS = PATHS["meters"]


def _token(exp: float) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp, "sub": 7}).encode())
    return f"header.{payload.decode().rstrip('=')}.signature"


class FakeResponse:
    def __init__(self, status: int, body: Any) -> None:
        self.status = status
        self._body = body

    async def json(self, **_: Any) -> Any:
        return self._body


class FakeSession:
    """Answers each path from a queue of (status, body); records requested paths."""

    def __init__(self, replies: dict[str, list[tuple[int, Any]]]) -> None:
        self.replies = replies
        self.calls: list[str] = []

    @asynccontextmanager
    async def request(self, _method: str, url: str, **_: Any) -> Any:
        path = url.split(":5443", 1)[1]
        self.calls.append(path)
        yield FakeResponse(*self.replies[path].pop(0))


def _login_ok(exp: float | None = None) -> tuple[int, Any]:
    return 200, {"accessToken": _token(exp or time.time() + 7 * 86400)}


def _api(session: FakeSession) -> KyivVodokanalApi:
    return KyivVodokanalApi(session, "user@example.com", "secret")  # type: ignore[arg-type]


def test_login_returns_user_id() -> None:
    session = FakeSession({LOGIN: [_login_ok()]})
    assert asyncio.run(_api(session).login()) == "7"


def test_login_rejected() -> None:
    session = FakeSession({LOGIN: [(401, None)]})
    with pytest.raises(KyivVodokanalAuthError):
        asyncio.run(_api(session).login())


def test_renews_token_before_expiry() -> None:
    almost_expired = time.time() + TOKEN_RENEW_MARGIN - 60
    session = FakeSession(
        {LOGIN: [_login_ok(almost_expired), _login_ok()], METERS: [(200, [])] * 2}
    )
    api = _api(session)

    async def run() -> None:
        await api.get_meters()
        await api.get_meters()

    asyncio.run(run())
    # First call logs in; second sees the token inside the margin and renews it.
    assert session.calls == [LOGIN, METERS, LOGIN, METERS]


def test_retries_once_after_401() -> None:
    session = FakeSession(
        {LOGIN: [_login_ok(), _login_ok()], METERS: [(401, None), (200, [])]}
    )
    assert asyncio.run(_api(session).get_meters()) == []
    assert session.calls == [LOGIN, METERS, LOGIN, METERS]


def test_second_401_is_auth_error() -> None:
    session = FakeSession(
        {LOGIN: [_login_ok(), _login_ok()], METERS: [(401, None), (401, None)]}
    )
    with pytest.raises(KyivVodokanalAuthError):
        asyncio.run(_api(session).get_meters())
