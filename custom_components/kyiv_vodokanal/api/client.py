"""Asynchronous client for the Kyivvodokanal personal account."""

from __future__ import annotations

import base64
import json
import time
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import BASE_URL, PATHS, PROVIDER_GROUP_ID, TOKEN_RENEW_MARGIN
from .exceptions import (
    KyivVodokanalAuthError,
    KyivVodokanalConnectionError,
    KyivVodokanalResponseError,
)
from .models import Account, Balance, InvoiceRow, Meter, Payment, Tariff, parse_date


def _iso(value: datetime) -> str:
    """Format a datetime the way the portal frontend sends it."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _jwt_claims(token: str) -> dict[str, Any]:
    """Decode JWT payload without verifying it; only used for expiry and user ID."""
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


class KyivVodokanalApi:
    """Asynchronous API for the Kyivvodokanal personal account."""

    def __init__(
        self,
        session: ClientSession,
        email: str,
        password: str,
        timeout: int = 30,
    ) -> None:
        """Initialize the API."""
        self.session = session
        self.timeout = ClientTimeout(total=timeout)
        self._email = email
        self._password = password
        self._token: str | None = None
        self._token_expires_at = 0.0

    async def _send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> tuple[int, Any]:
        """Send one request and return status and decoded JSON (None on errors)."""
        headers = {"Accept": "application/json"}
        if auth:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            async with self.session.request(
                method,
                BASE_URL + path,
                params=params,
                json=body,
                headers=headers,
                timeout=self.timeout,
            ) as response:
                if response.status != HTTPStatus.OK:
                    return response.status, None
                return response.status, await response.json(content_type=None)
        except TimeoutError as err:
            msg = "Request timed out"
            raise KyivVodokanalConnectionError(msg) from err
        except ClientError as err:
            msg = f"Connection error: {err}"
            raise KyivVodokanalConnectionError(msg) from err
        except ValueError as err:
            msg = f"Invalid JSON from {path}"
            raise KyivVodokanalResponseError(msg) from err

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Make an authenticated request, logging in again when needed."""
        if (
            self._token is None
            or self._token_expires_at - time.time() < TOKEN_RENEW_MARGIN
        ):
            await self.login()
        status, data = await self._send(method, path, params=params, body=body)
        if status == HTTPStatus.UNAUTHORIZED:
            await self.login()
            status, data = await self._send(method, path, params=params, body=body)
        if status == HTTPStatus.UNAUTHORIZED:
            msg = "Token rejected right after login"
            raise KyivVodokanalAuthError(msg)
        if status != HTTPStatus.OK:
            msg = f"HTTP {status} from {path}"
            raise KyivVodokanalResponseError(msg)
        return data

    async def login(self) -> str:
        """Log in and return the account's user ID."""
        status, data = await self._send(
            "POST",
            PATHS["login"],
            body={"account": self._email, "password": self._password},
            auth=False,
        )
        if status in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNAUTHORIZED):
            msg = "Invalid email or password"
            raise KyivVodokanalAuthError(msg)
        if (
            status != HTTPStatus.OK
            or not isinstance(data, dict)
            or "accessToken" not in data
        ):
            msg = f"Unexpected login response: HTTP {status}"
            raise KyivVodokanalResponseError(msg)
        self._token = data["accessToken"]
        claims = _jwt_claims(self._token)
        self._token_expires_at = float(claims["exp"])
        return str(claims["sub"])

    async def get_accounts(self) -> list[Account]:
        """Return personal accounts, merging their per-service records."""
        data = await self._request(
            "GET",
            PATHS["accounts"],
            params={"serviceProviderGroupIds": PROVIDER_GROUP_ID},
        )
        accounts: dict[str, Account] = {}
        for item in data:
            provider = item["serviceProvider"]
            account = Account(
                provider_id=provider["id"],
                provider_code=provider["code"],
                provider_name=provider["name"],
                code=item["invoiceAccount"]["code"],
            )
            accounts.setdefault(account.key, account)
        return list(accounts.values())

    async def get_meters(self) -> list[Meter]:
        """Return meters with their latest readings."""
        data = await self._request(
            "GET",
            PATHS["meters"],
            params={"serviceProviderGroupIds": PROVIDER_GROUP_ID},
        )
        return [Meter.from_dict(item) for item in data]

    async def get_balance(self, account: Account) -> Balance:
        """Return the balance of the last closed billing month."""
        data = await self._request(
            "GET",
            PATHS["balance"],
            params={"serviceProviderCode": account.provider_code, "code": account.code},
        )
        return Balance(
            debt=data["debt"],
            bill_amount=data["billAmount"],
            amount_to_pay=data["amountToPay"],
        )

    async def get_invoices(self, start: datetime, end: datetime) -> list[InvoiceRow]:
        """Return monthly invoice rows of all accounts, including provisional ones."""
        data = await self._request(
            "GET",
            PATHS["invoices"],
            params={
                "serviceProviderGroupIds": PROVIDER_GROUP_ID,
                "from": _iso(start),
                "to": _iso(end),
            },
        )
        return [InvoiceRow.from_dict(item) for item in data if item.get("detail")]

    async def get_payments(
        self, provider_id: int, start: datetime, end: datetime
    ) -> list[Payment]:
        """Return successful payments of all accounts at a provider."""
        data = await self._request(
            "POST",
            PATHS["payments"],
            body={
                "from": _iso(start),
                "to": _iso(end),
                "serviceProviderId": provider_id,
            },
        )
        # statusId 1 is what the portal treats as a completed payment.
        return [
            Payment(
                account_code=item["invoiceAccount"]["code"],
                paid_at=datetime.fromisoformat(item["payment"]["date"]),
                amount=item["payment"]["amount"],
            )
            for item in data
            if item["payment"].get("statusId") == 1
        ]

    async def get_tariffs(self, account: Account) -> list[Tariff]:
        """Return the account's current tariffs."""
        data = await self._request(
            "GET",
            PATHS["tariffs"],
            params={
                "serviceProviderCode": account.provider_code,
                "invoiceAccountCode": account.code,
            },
        )
        return [
            Tariff(
                service_code=(item.get("service") or {}).get("code"),
                sub_service_code=(item.get("subService") or {}).get("code"),
                amount=item["tariffAmount"],
                billing_date=parse_date(item.get("billingDate")),
            )
            for item in data
        ]
