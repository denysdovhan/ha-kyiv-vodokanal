"""Data models of the Kyivvodokanal API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Self


def parse_date(value: str | None) -> date | None:
    """Parse an API timestamp into its calendar date (billing month labels are UTC)."""
    return datetime.fromisoformat(value).date() if value else None


@dataclass(slots=True)
class Account:
    """A personal account, shared by all its service records."""

    provider_id: int
    provider_code: str
    provider_name: str
    code: str

    @property
    def key(self) -> str:
        """Return a stable identifier for the account."""
        return f"{self.provider_code}_{self.code}"


@dataclass(slots=True)
class Meter:
    """A water meter with its latest reported reading."""

    id: int
    number: str
    model: str | None
    reading: float | None
    period_usage: float | None
    billing_period: date | None

    @classmethod
    def from_dict(cls: type[Self], data: dict[str, Any]) -> Self:
        """Initialize from a last-factors item."""
        factors = [f for f in data.get("factors") or [] if f.get("invoicePeriod")]
        latest = max(factors, key=lambda f: f["invoicePeriod"], default={})
        return cls(
            id=data["id"],
            number=data.get("counterNumber")
            or data.get("counterCode")
            or str(data["id"]),
            model=(data.get("model") or {}).get("name"),
            reading=latest.get("endFactor"),
            period_usage=latest.get("difference"),
            billing_period=parse_date(latest.get("invoicePeriod")),
        )


@dataclass(slots=True)
class Balance:
    """Totals of the last closed billing month, all services of an account."""

    debt: float
    bill_amount: float
    amount_to_pay: float


@dataclass(slots=True)
class InvoiceRow:
    """One service's monthly balance row."""

    provider_code: str
    account_code: str
    billing_period: date
    finalized: bool
    debt: float
    paid: float

    @classmethod
    def from_dict(cls: type[Self], data: dict[str, Any]) -> Self:
        """Initialize from an invoice history item."""
        detail = data["detail"]
        return cls(
            provider_code=data["serviceProvider"]["code"],
            account_code=data["invoiceAccount"]["code"],
            billing_period=parse_date(detail["billingDate"]),
            # Current-month rows are provisional and have no ID yet.
            finalized=data.get("id") is not None,
            debt=detail.get("debt") or 0.0,
            paid=detail.get("amountPaided") or 0.0,
        )


@dataclass(slots=True)
class Payment:
    """One successful payment row; a checkout creates one per service."""

    account_code: str
    paid_at: datetime
    amount: float


@dataclass(slots=True)
class Tariff:
    """A tariff row; flat fees in UAH, volumetric tariffs in UAH/m³."""

    service_code: str | None
    sub_service_code: str | None
    amount: float
    billing_date: date | None
