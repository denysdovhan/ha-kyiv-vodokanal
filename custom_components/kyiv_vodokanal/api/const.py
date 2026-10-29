"""Constants of the Kyivvodokanal API."""

# Mobile app backend; serves the same API as my.vodokanal.kiev.ua but accepts
# email/password login without reCAPTCHA. See docs/mobile-api.md.
BASE_URL = "https://warreg.ssmt.com.ua:5443"
# Kyivvodokanal provider group on the shared billing platform.
PROVIDER_GROUP_ID = 22
# The JWT lives 7 days and cannot be refreshed: log in again with a day left.
TOKEN_RENEW_MARGIN = 24 * 60 * 60

PATHS = {
    "login": "/api/account/authentication",
    "accounts": "/api/warehouse/consumer/invoice_accounts",
    "meters": "/api/warehouse/consumer/counters/last-factors",
    "balance": "/api/warehouse/consumer/invoice/amount_to_pay",
    "invoices": "/api/warehouse/consumer/invoices/history-with-dynamic-invoices",
    "payments": "/api/warehouse/consumer/payments/history",
    "tariffs": "/api/warehouse/consumer/tariff",
}
