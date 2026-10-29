"""Sensors for Kyiv Vodokanal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfVolume
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CURRENCY, DOMAIN, PRICE_PER_CUBIC_METER
from .coordinator import (
    AccountData,
    KyivVodokanalConfigEntry,
    KyivVodokanalCoordinator,
    KyivVodokanalData,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .api import Meter

# Coordinator does all I/O.
PARALLEL_UPDATES = 0

type SensorValue = float | date | datetime | None


@dataclass(frozen=True, kw_only=True)
class MeterSensorDescription(SensorEntityDescription):
    """Describes a meter sensor."""

    value_fn: Callable[[Meter], SensorValue]


@dataclass(frozen=True, kw_only=True)
class AccountSensorDescription(SensorEntityDescription):
    """Describes a personal account sensor."""

    value_fn: Callable[[KyivVodokanalData, AccountData], SensorValue]


METER_SENSORS: tuple[MeterSensorDescription, ...] = (
    # Lifetime register value: the Energy dashboard water source.
    MeterSensorDescription(
        key="reading",
        translation_key="reading",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=3,
        value_fn=lambda meter: meter.reading,
    ),
    MeterSensorDescription(
        key="period_usage",
        translation_key="period_usage",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=3,
        value_fn=lambda meter: meter.period_usage,
    ),
    MeterSensorDescription(
        key="billing_period",
        translation_key="billing_period",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda meter: meter.billing_period,
    ),
)


ACCOUNT_SENSORS: tuple[AccountSensorDescription, ...] = (
    AccountSensorDescription(
        key="amount_to_pay",
        translation_key="amount_to_pay",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY,
        suggested_display_precision=2,
        value_fn=lambda _, account: account.balance.amount_to_pay,
    ),
    AccountSensorDescription(
        key="unpaid_previous",
        translation_key="unpaid_previous",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY,
        suggested_display_precision=2,
        value_fn=lambda _, account: account.unpaid_previous,
    ),
    AccountSensorDescription(
        key="bill_amount",
        translation_key="bill_amount",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY,
        suggested_display_precision=2,
        value_fn=lambda _, account: account.balance.bill_amount,
    ),
    AccountSensorDescription(
        key="last_payment",
        translation_key="last_payment",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY,
        suggested_display_precision=2,
        value_fn=lambda _, account: (
            account.last_payment and account.last_payment.amount
        ),
    ),
    AccountSensorDescription(
        key="last_payment_date",
        translation_key="last_payment_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda _, account: account.last_payment and account.last_payment.day,
    ),
    # A price per m³ is not a monetary amount, so no device class.
    AccountSensorDescription(
        key="water_supply",
        translation_key="water_supply",
        native_unit_of_measurement=PRICE_PER_CUBIC_METER,
        suggested_display_precision=2,
        value_fn=lambda _, account: account.tariffs.get("water_supply"),
    ),
    AccountSensorDescription(
        key="wastewater",
        translation_key="wastewater",
        native_unit_of_measurement=PRICE_PER_CUBIC_METER,
        suggested_display_precision=2,
        value_fn=lambda _, account: account.tariffs.get("wastewater"),
    ),
    AccountSensorDescription(
        key="service_price",
        translation_key="service_price",
        native_unit_of_measurement=PRICE_PER_CUBIC_METER,
        suggested_display_precision=2,
        value_fn=lambda _, account: account.tariffs.get("service_price"),
    ),
    AccountSensorDescription(
        key="subscription_fee",
        translation_key="subscription_fee",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY,
        suggested_display_precision=2,
        value_fn=lambda _, account: account.tariffs.get("subscription_fee"),
    ),
    AccountSensorDescription(
        key="last_sync",
        translation_key="last_sync",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: data.last_sync,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: KyivVodokanalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = entry.runtime_data
    known_meters: set[int] = set()
    known_accounts: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        # A replaced meter or a newly linked account appears in a later refresh.
        data = coordinator.data
        new_meters = data.meters.keys() - known_meters
        new_accounts = data.accounts.keys() - known_accounts
        known_meters.update(new_meters)
        known_accounts.update(new_accounts)
        entities: list[SensorEntity] = [
            MeterSensor(coordinator, meter_id, description)
            for meter_id in new_meters
            for description in METER_SENSORS
        ]
        entities += [
            AccountSensor(coordinator, key, description)
            for key in new_accounts
            for description in ACCOUNT_SENSORS
        ]
        if entities:
            async_add_entities(entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class MeterSensor(CoordinatorEntity[KyivVodokanalCoordinator], SensorEntity):
    """A sensor of one water meter."""

    _attr_has_entity_name = True
    entity_description: MeterSensorDescription

    def __init__(
        self,
        coordinator: KyivVodokanalCoordinator,
        meter_id: int,
        description: MeterSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._meter_id = meter_id
        meter = coordinator.data.meters[meter_id]
        self._attr_unique_id = f"meter_{meter_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"meter_{meter_id}")},
            translation_key="meter",
            translation_placeholders={"number": meter.number},
            model=meter.model,
            serial_number=meter.number,
        )

    @property
    def available(self) -> bool:
        """Return if the meter is still in the data."""
        return super().available and self._meter_id in self.coordinator.data.meters

    @property
    def native_value(self) -> SensorValue:
        """Return the state."""
        return self.entity_description.value_fn(
            self.coordinator.data.meters[self._meter_id]
        )


class AccountSensor(CoordinatorEntity[KyivVodokanalCoordinator], SensorEntity):
    """A sensor of one personal account."""

    _attr_has_entity_name = True
    entity_description: AccountSensorDescription

    def __init__(
        self,
        coordinator: KyivVodokanalCoordinator,
        account_key: str,
        description: AccountSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._account_key = account_key
        account = coordinator.data.accounts[account_key].account
        self._attr_unique_id = f"account_{account_key}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"account_{account_key}")},
            translation_key="account",
            translation_placeholders={"code": account.code},
            manufacturer=account.provider_name,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Return if the account is still in the data."""
        return super().available and self._account_key in self.coordinator.data.accounts

    @property
    def native_value(self) -> SensorValue:
        """Return the state."""
        data = self.coordinator.data
        return self.entity_description.value_fn(data, data.accounts[self._account_key])
