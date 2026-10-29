"""Data update coordinator for Kyiv Vodokanal."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    Account,
    Balance,
    InvoiceRow,
    KyivVodokanalApi,
    KyivVodokanalAuthError,
    KyivVodokanalError,
    Meter,
    Payment,
    Tariff,
)
from .const import (
    DOMAIN,
    INVOICE_LOOKBACK,
    PAYMENT_LOOKBACK,
    TARIFF_CODES,
    UPDATE_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

type KyivVodokanalConfigEntry = ConfigEntry[KyivVodokanalCoordinator]


@dataclass(slots=True)
class LastPayment:
    """Total paid on the latest payment day."""

    day: date
    amount: float


@dataclass(slots=True)
class AccountData:
    """Everything shown for one personal account."""

    account: Account
    balance: Balance
    unpaid_previous: float | None
    last_payment: LastPayment | None
    tariffs: dict[str, float]


@dataclass(slots=True)
class KyivVodokanalData:
    """Coordinator data."""

    accounts: dict[str, AccountData]
    meters: dict[int, Meter]
    last_sync: datetime


def unpaid_previous(rows: list[InvoiceRow], account: Account) -> float | None:
    """Return what was still unpaid from earlier months in the last finalized month."""
    rows = [
        row
        for row in rows
        if row.finalized
        and row.provider_code == account.provider_code
        and row.account_code == account.code
    ]
    if not rows:
        return None
    last = max(row.billing_period for row in rows)
    # Opening balance minus payments; unaffected by benefits, see docs/data-model.md.
    return round(
        sum(row.debt - row.paid for row in rows if row.billing_period == last), 2
    )


def last_payment(payments: list[Payment], account: Account) -> LastPayment | None:
    """Return the total paid on the account's latest payment day."""
    days = [
        (dt_util.as_local(payment.paid_at).date(), payment.amount)
        for payment in payments
        if payment.account_code == account.code
    ]
    if not days:
        return None
    last = max(day for day, _ in days)
    # One checkout creates a separate row per service, so sum the whole day.
    return LastPayment(
        day=last, amount=round(sum(a for day, a in days if day == last), 2)
    )


def tariffs_by_key(tariffs: list[Tariff]) -> dict[str, float]:
    """Return current tariff amounts keyed by TARIFF_CODES values."""
    result: dict[str, float] = {}
    for tariff in sorted(tariffs, key=lambda t: t.billing_date or date.min):
        if key := TARIFF_CODES.get(
            tariff.sub_service_code or tariff.service_code or ""
        ):
            result[key] = tariff.amount
    # Every m³ is billed for both supply and wastewater: the Energy dashboard price.
    if "water_supply" in result and "wastewater" in result:
        result["service_price"] = round(
            result["water_supply"] + result["wastewater"], 5
        )
    return result


class KyivVodokanalCoordinator(DataUpdateCoordinator[KyivVodokanalData]):
    """Fetch meters, balances, payments, and tariffs for one login."""

    config_entry: KyivVodokanalConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: KyivVodokanalConfigEntry,
        api: KyivVodokanalApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> KyivVodokanalData:
        """Fetch data from the API."""
        try:
            return await self._fetch()
        except KyivVodokanalAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KyivVodokanalError as err:
            raise UpdateFailed(str(err)) from err

    async def _fetch(self) -> KyivVodokanalData:
        now = dt_util.utcnow()
        accounts = await self.api.get_accounts()
        meters = await self.api.get_meters()
        invoices = await self.api.get_invoices(now - INVOICE_LOOKBACK, now)
        # Keyed by provider: account codes are only unique within a provider.
        payments: dict[int, list[Payment]] = {}
        for provider_id in {account.provider_id for account in accounts}:
            payments[provider_id] = await self.api.get_payments(
                provider_id, now - PAYMENT_LOOKBACK, now
            )

        account_data: dict[str, AccountData] = {}
        for account in accounts:
            account_data[account.key] = AccountData(
                account=account,
                balance=await self.api.get_balance(account),
                unpaid_previous=unpaid_previous(invoices, account),
                last_payment=last_payment(payments[account.provider_id], account),
                tariffs=tariffs_by_key(await self.api.get_tariffs(account)),
            )
        LOGGER.debug("Fetched %s accounts and %s meters", len(accounts), len(meters))
        return KyivVodokanalData(
            accounts=account_data,
            meters={meter.id: meter for meter in meters},
            last_sync=now,
        )
