# Authentication and API

Base URL: `https://my.vodokanal.kiev.ua`. Evidence date: 2026-10-28.
This is the portal's internal API, not a documented public contract.
See [evidence definitions](README.md#evidence-levels).

The mobile backend `https://warreg.ssmt.com.ua:5443` serves the **same API**
(identical paths, identical 401 JSON). Its `/api/account/authentication` accepts
email/password without reCAPTCHA; see [mobile-api.md](mobile-api.md). Prefer it
for an unattended login flow.

## Authentication

### Password login: source contract

```http
POST /api/account/authentication
Content-Type: application/json
```

```json
{
  "account": "person@example.invalid",
  "password": "<password>",
  "recaptcha": "<user-completed challenge token>"
}
```

The login form sends its complete value. `account`, `password`, and `recaptcha`
are its controls. The account field's placeholder says email. Do not assume
telephone or utility account number login is supported.

The frontend expects a response containing `accessToken`. Its `createSession`
stores that value under local storage key `access_token`. No complete fresh-login
response was captured during the initial investigation; do not assume this is the
only response field. The user subsequently completed a fresh sign-in in the
in-app browser and reached `/dashboard/home`. The method they chose and the
login request/response were not captured, so this confirms interactive login
without validating this password payload or a renewal flow end to end.

**Live:** the fresh login page presents a Google reCAPTCHA checkbox and a
Google sign-in button. **Source:** the deployed configuration has
`recaptcha.show = true` and `show_in_sign_in = true`; the form requires a
challenge value. No attempt was made to omit or bypass the challenge.
Backend enforcement and possible additional login checks are untested.

### Google login: source contract

```http
POST /api/account/authentication/by-social-network-token
Content-Type: application/json
```

```json
{
  "token": "<Google ID token>",
  "socialNetwork": "GOOGLE"
}
```

The frontend passes the Google library's `idToken` and provider value, then uses
the same `createSession` path. The provider constant in that library is `GOOGLE`.
Related registration-status and registration endpoints exist, but registration
is outside a read-only integration's scope.

This is a Google ID-token exchange, not evidence that Vodokanal offers an OAuth
authorization-code flow with arbitrary redirects, a device flow, or refresh tokens.
Do not reuse the portal's Google client ID as an integration client without a
supported authorization arrangement.

### Authenticated requests and lifetime

**Live:** protected requests send `Authorization: Bearer <JWT>` and return JSON.
The observed JWT payload contains `iat`, `jti`, `sub`, and `exp`.
`exp - iat` was **604800 seconds, seven days**, for one session.
The actual token and subject are deliberately not recorded here.

**Source:** `isLoggedIn()` delegates to the JWT helper's expiry check. The app
also writes an `expires_at` local-storage value, but it is not the login validity
check. Use JWT expiry as a scheduling hint, not that auxiliary value.

The public frontend contains no identified Vodokanal refresh-token endpoint or
renewal flow. Google-library methods named `refreshToken` are not proof of
Vodokanal session renewal. Logout clears local auth/profile caches; server-side
revocation was not established.

The browser also sends cookies. Bearer-only calls from a clean Python HTTP client,
token revocation, expired-token errors, and server-side session renewal have not
been tested. Preserve these as unknowns instead of promising automatic relogin.

The JWT interceptor deliberately excludes authentication, public CMS, and
`/api/kvk/counters/verify/` URLs. Avoid sending credentials to unrelated hosts.

## Meter/account reads confirmed live

Paths below are relative to the base URL. All returned HTTP 200.

| Method | Path                                                       | Request                                     | Response                                         |
| ------ | ---------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------ |
| GET    | `/api/warehouse/consumer/invoice_accounts`                 | `serviceProviderGroupIds=22`                | Array of service-specific account links          |
| GET    | `/api/warehouse/consumer/counters/last-factors`            | `serviceProviderGroupIds=22`                | Array of meters with metadata and latest factors |
| GET    | `/api/warehouse/consumer/counters`                         | `serviceProviderCode`, `invoiceAccountCode` | Array of simpler meter objects                   |
| GET    | `/api/warehouse/consumer/counter/{counterId}/last-factors` | Numeric meter ID in path                    | One full meter/latest-factors object             |
| POST   | `/api/warehouse/consumer/counter/factors/history`          | JSON filter below                           | Array of factor history records                  |

`22` is the provider-group filter used by this deployment. The observed Kyiv
Vodokanal provider has code `"889"` and numeric ID `10`. These are different
namespaces. Discover account/provider IDs from the response, not private fixtures.

History supports two observed frontend request shapes:

```json
{
  "invoiceAccountCode": "EXAMPLE_ACCOUNT",
  "serviceProviderCode": "889",
  "range": {
    "from": "2026-06-30T21:00:00.000Z",
    "to": "2026-10-31T21:59:59.999Z"
  }
}
```

The meters-page request used this alternative filter, also captured live:

```json
{
  "counterId": 501,
  "range": {
    "from": "2025-09-30T21:00:00.000Z",
    "to": "2026-10-31T21:59:59.999Z"
  }
}
```

The numeric counter ID is synthetic. POST is a read operation for this history endpoint.
Date ranges come from local calendar boundaries serialized to UTC, so their
offset changes with daylight-saving time. Use `Europe/Kyiv`, not a fixed offset.

## Billing reads confirmed live

| Method | Path                                                             | Request                                       | Response                                                      |
| ------ | ---------------------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------- |
| GET    | `/api/warehouse/consumer/invoice/amount_to_pay`                  | `serviceProviderCode`, **`code`** for account | `{debt, billAmount, amountToPay}`                             |
| POST   | `/api/warehouse/consumer/payments/history`                       | `{from, to, serviceProviderId}` observed      | Array of payments with service/account references             |
| GET    | `/api/warehouse/consumer/tariff`                                 | `serviceProviderCode`, `invoiceAccountCode`   | Array of tariff rows                                          |
| GET    | `/api/warehouse/consumer/invoices/history-with-dynamic-invoices` | `serviceProviderGroupIds=22`, `from`, `to`    | Array of monthly service invoices, including provisional rows |

For payments, the captured dashboard request filtered by numeric provider ID
only. Filter returned account/service records explicitly; do not assume every
payment belongs to the selected account. Additional account filter support was
not verified.

The tariff service accepts optional `dateFrom` and `dateTo` ISO strings in
frontend source. Invoice history accepts optional `serviceProviderCode` and
`invoiceAccountCode` in source. Those variants were not exercised.

The dashboard also requests `GET /api/ud/profile`,
`GET /api/ud/contact_info/emails`, and `GET /api/ud/contact_info/phones`.
A meter integration should avoid fetching contact details it does not need.

## Other discovered endpoints

These are source discoveries unless otherwise marked; they are not validated
implementation contracts.

| Method | Path                                                   | Purpose                                          |
| ------ | ------------------------------------------------------ | ------------------------------------------------ |
| GET    | `/api/warehouse/consumer/last-invoices`                | Latest invoices                                  |
| GET    | `/api/warehouse/consumer/invoice-detail?invoiceId=...` | Invoice detail                                   |
| GET    | `/api/warehouse/receipt-default`                       | PDF receipt; request parameters not investigated |
| POST   | `/api/warehouse/consumer/counter/factor`               | Submit readings; **write, not tested**           |
| POST   | `/api/kvk/counters/verify/submit`                      | Verification workflow; command-dependent         |

The meters page automatically called the last endpoint with
`{"cmd":"search","company":"889","meter_uid":"EXAMPLE_COUNTER_CODE"}`.
**Live response:** `{"code":200,"applications":[]}`. No bearer header was
attached to this request. Other commands may submit real applications; do not
call them during read-only development. The path name alone does not establish
whether a particular request is a read or write.

## Errors and limits not yet characterized

No rate-limit probing, invalid-password attempts, expired-token tests, or
write tests were performed. HTTP 200 observations are not a complete error
contract. Validate status and JSON shape separately; malformed responses and
outages must not become zero readings or successful empty accounts.

No stable API version, pagination guarantee, history-retention limit, or
published polling allowance was established. A six-hour poll is a proposal,
not a provider promise.
