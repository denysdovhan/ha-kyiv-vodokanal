"""Parser and derived-value checks on synthetic API data."""

from datetime import UTC, date, datetime

from custom_components.kyiv_vodokanal.api import (
    Account,
    InvoiceRow,
    Meter,
    Payment,
    Tariff,
)
from custom_components.kyiv_vodokanal.coordinator import (
    last_payment,
    tariffs_by_key,
    unpaid_previous,
)

ACCOUNT = Account(provider_id=10, provider_code="889", provider_name="KVK", code="ACC")


def test_meter_uses_latest_factor() -> None:
    meter = Meter.from_dict(
        {
            "id": 501,
            "counterNumber": "00123",
            "model": None,
            "factors": [
                {
                    "invoicePeriod": "2026-10-01T00:00:00Z",
                    "endFactor": 102.5,
                    "difference": 2.5,
                },
                {
                    "invoicePeriod": "2026-09-01T00:00:00Z",
                    "endFactor": 100.0,
                    "difference": 1.0,
                },
            ],
        }
    )
    assert (meter.number, meter.reading, meter.period_usage) == ("00123", 102.5, 2.5)
    assert meter.billing_period == date(2026, 10, 1)


def test_meter_without_factors() -> None:
    meter = Meter.from_dict({"id": 501, "factors": None})
    assert (meter.reading, meter.billing_period) == (None, None)


def _row(
    period: str, *, debt: float, paid: float, row_id: int | None = 1
) -> InvoiceRow:
    return InvoiceRow.from_dict(
        {
            "id": row_id,
            "serviceProvider": {"code": "889"},
            "invoiceAccount": {"code": "ACC"},
            "detail": {"billingDate": period, "debt": debt, "amountPaided": paid},
        }
    )


def test_unpaid_previous_uses_last_finalized_month() -> None:
    rows = [
        _row("2026-08-01T00:00:00Z", debt=9.0, paid=0.0),
        # Two services in the last finalized month: one fully paid, one not.
        _row("2026-09-01T00:00:00Z", debt=4.25, paid=4.25),
        _row("2026-09-01T00:00:00Z", debt=47.52, paid=40.0),
        # Provisional current month is ignored.
        _row("2026-10-01T00:00:00Z", debt=99.0, paid=0.0, row_id=None),
    ]
    assert unpaid_previous(rows, ACCOUNT) == 7.52
    assert unpaid_previous([], ACCOUNT) is None


def test_last_payment_sums_latest_day() -> None:
    payments = [
        Payment("ACC", datetime(2026, 8, 19, 14, 59, tzinfo=UTC), 3.95),
        Payment("ACC", datetime(2026, 9, 20, 10, 0, 0, tzinfo=UTC), 47.52),
        Payment("ACC", datetime(2026, 9, 20, 10, 0, 1, tzinfo=UTC), 4.25),
        Payment("OTHER", datetime(2026, 10, 1, tzinfo=UTC), 1.0),
    ]
    result = last_payment(payments, ACCOUNT)
    assert result is not None
    assert (result.day, result.amount) == (date(2026, 9, 20), 51.77)


def test_tariffs_by_code_latest_wins() -> None:
    tariffs = [
        Tariff("2", "12", 15.0, date(2026, 1, 1)),
        Tariff("2", "12", 16.164, date(2026, 10, 1)),
        Tariff("2", "11", 14.22, date(2026, 10, 1)),
        Tariff("35", None, 47.52, date(2026, 10, 1)),
        Tariff("99", None, 1.0, None),
    ]
    assert tariffs_by_key(tariffs) == {
        "water_supply": 16.164,
        "wastewater": 14.22,
        "subscription_fee": 47.52,
        "service_price": 30.384,
    }
    assert "service_price" not in tariffs_by_key(tariffs[:2])
