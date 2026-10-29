# Kyiv Vodokanal investigation

Investigated 2026-10-28. Research only; no integration implementation yet.

Start with [authentication and API](api.md), then [data structures](data-model.md)
and [Home Assistant design](home-assistant.md).
The ongoing [mobile API investigation](mobile-api.md) records proxy evidence
and the remaining capture/authentication questions.

## Findings

- The portal is an Angular application backed by same-origin JSON endpoints.
  Authenticated meter, history, account, tariff, payment, and billing requests
  returned HTTP 200 in an existing Chrome session.
- Login uses a bearer JWT. The observed token had a seven-day lifetime.
  The website's fresh login page attaches reCAPTCHA and offers Google sign-in.
- The mobile backend `warreg.ssmt.com.ua:5443` serves the same Spring API and
  its login endpoint accepts email/password **without** a `recaptcha` field
  (unknown-account probe returned "user not found", not a captcha rejection).
  A real-account login returned 200 with a 7-day bearer JWT and no refresh
  token. The token works without cookies on both hosts. See [mobile-api.md](mobile-api.md).
- Meter readings are dated billing/submission records, not live flow telemetry.
  There are cumulative readings, period usage, meter metadata, and verification dates.
- Multiple service records share an account number. History includes multiple
  entries for one meter and month. Neither account number nor month alone is unique.
- A read-only integration is feasible with unattended email/password login.
  Renewal means logging in again; no refresh endpoint or sliding session exists.
  Concurrent tokens stay valid, so re-login does not sign out other devices.

## Evidence levels

| Label    | Meaning                                                            |
| -------- | ------------------------------------------------------------------ |
| Live     | Observed portal UI or a successful browser API request/response    |
| Source   | Found in the deployed public JavaScript; not necessarily exercised |
| Proposal | Suggested integration behavior, not implemented or verified in HA  |
| Unknown  | Requires a targeted follow-up check                                |

Examples use synthetic identifiers, names, dates, and readings. They preserve
observed field names and types but are not raw account exports. Null fields
describe the observed sample, not a complete API specification.

## Sources and reproduction

Portal pages inspected:

- [Login](https://my.vodokanal.kiev.ua/sign-in)
- [Dashboard](https://my.vodokanal.kiev.ua/dashboard/home)
- [Meters and history](https://my.vodokanal.kiev.ua/dashboard/counters)
- [Billing history](https://my.vodokanal.kiev.ua/dashboard/invoices)

Public application source inspected:
[main.5d6e6972443c9cf7.js](https://my.vodokanal.kiev.ua/main.5d6e6972443c9cf7.js).
This filename will change on deployment. Find the current script in the page DOM.
Useful search terms: `/api/account/authentication`, `createSession`,
`getCountersLastFactors`, `getFactorsHistory`, `getTariffs`, `getDynamicInvoices`,
`tokenGetter`, `show_in_sign_in`, and `/api/kvk/counters/verify/submit`.

To repeat the investigation, sign in manually and inspect Network requests while
opening the pages above. Do not export raw HAR files into this repository.
They contain bearer tokens, cookies, account addresses, and payment identifiers.
No reading, payment, profile change, or verification application was submitted
by the investigator. The meters page automatically makes a verification
application **search** request; see `api.md`.

## Repository state

The current source, manifest, package metadata, and `agents.md` still describe
LUN Misto Air under `custom_components/lun_misto_air`. They are a starting template,
not Kyiv Vodokanal behavior. This investigation adds only documentation.
When implementation changes tooling or runtime structure, update `agents.md`
additively as required by its instructions.

## Open questions

1. Does the backend rate-limit or lock accounts after repeated logins? (Login
   once per ~7 days, not per poll.)
2. What does an expired token return? Assumed 401; not yet observed.
3. How are reading corrections, replacement meters, and multiple factor types represented?
4. How should historical monthly usage be deduplicated and reconciled?
5. Does the provider offer a documented API or authorize an integration-specific login flow?
