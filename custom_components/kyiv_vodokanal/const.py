"""Constants for Kyiv Vodokanal integration."""

from datetime import timedelta

from homeassistant.const import UnitOfVolume

DOMAIN = "kyiv_vodokanal"

PORTAL_URL = "https://my.vodokanal.kiev.ua"

# All amounts are in hryvnias; HA has no built-in UAH constant.
CURRENCY = "UAH"
PRICE_PER_CUBIC_METER = f"{CURRENCY}/{UnitOfVolume.CUBIC_METERS}"

# Readings and bills change monthly; payments a few times a month.
UPDATE_INTERVAL = timedelta(hours=6)

# Long enough to include the last finalized monthly invoice.
INVOICE_LOOKBACK = timedelta(days=125)
# The portal itself looks back up to 12 months for the last payment.
PAYMENT_LOOKBACK = timedelta(days=366)

# Tariff rows by (sub)service code, as returned by the tariff endpoint.
TARIFF_CODES = {
    "12": "water_supply",
    "11": "wastewater",
    "35": "subscription_fee",
}
