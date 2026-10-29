# Proposed Home Assistant integration

Proposal based on the [observed API](api.md), not implemented behavior.
The requested product is login, retained authentication, and water-meter data.
Email/password login via the mobile backend is confirmed working. Renewal is
re-login with the stored password, since no refresh endpoint exists.

Proposed renewal flow, invisible to the user:

1. Keep the token in memory; read `exp` from the JWT payload.
2. Before a fetch, log in again if `exp` is within one day.
3. On a 401 from a data call, log in once and retry the call.
4. Only if login itself returns 401 raise `ConfigEntryAuthFailed` (password
   changed); HA then shows its standard reauth prompt.

Re-login does not revoke other sessions, so the user's phone app stays signed in.

## Authentication decision

| Approach                                         | Assessment                                                                                                                                                                                                                                                                                  |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Login/password via mobile endpoint               | **Chosen.** `warreg.ssmt.com.ua:5443/api/account/authentication` accepts email/password without reCAPTCHA. Confirmed with a real account: 7-day JWT, no refresh token, bearer-only reads work (see [mobile-api.md](mobile-api.md)). Store the password, log in again before `exp` or on 401 |
| Login/password via website host                  | Website frontend attaches reCAPTCHA; avoid depending on the browser path when the mobile host accepts a plain POST                                                                                                                                                                          |
| User supplies a session token                    | Small read-only prototype, but the observed token expires after seven days. Does not meet a seamless login/renewal requirement                                                                                                                                                              |
| Provider-supported browser authorization/renewal | Durable fallback if password login proves unreliable; no suitable callback/refresh contract established                                                                                                                                                                                     |

Do not silently choose manual token entry as the finished product. A redirect to
the portal alone cannot transfer authentication back to HA. A proper browser
login needs a supported return/exchange mechanism. Google login is tied to the
portal's client registration; it is not automatically usable by HA.

Once a supported mechanism is established, persist the minimum auth material in
config entry data and keep the live client/coordinator in `entry.runtime_data`.
Treat persisted credentials as secrets covered by HA config storage and backups,
not as an encrypted credential vault. Do not place them in options displayed as
ordinary text, entity attributes, logs, diagnostics, fixtures, or repository files.

Validate authentication with an account/meter API call before creating the
entry. On confirmed invalid/expired credentials, raise `ConfigEntryAuthFailed`
from setup/coordinator to start reauthentication. Network errors should remain
retryable and should not prompt for a new password. A reauth flow should update
the existing entry and preserve entity identity, while rejecting an unintended
account switch. See [HA config flows](https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/core/integration/config_flow.md)
and [setup failures](https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/integration_setup_failures.md).

## Smallest useful read-only scope

One config entry per portal login, with account discovery and selection as
needed. One shared API client and coordinator can fetch all latest meter
snapshots, avoiding one request per sensor. Start with a six-hour poll and
standard refresh support; this interval is a design suggestion, not a confirmed
server limit. No browser automation should be required for regular data polling.

Use plain API data objects and typed runtime data. Entities read the coordinator
cache without I/O. Distinguish successful empty results from failed requests.
Keep unavailable data unavailable instead of reporting zero.
See [HA fetching data](https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/integration_fetching_data.md)
and [runtime data](https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/core/integration-quality-scale/rules/runtime-data.md).

## Entities

Suggested first-version entities per meter:

| Entity                 | Source                   | HA representation                                                |
| ---------------------- | ------------------------ | ---------------------------------------------------------------- |
| Reported meter reading | Latest `endFactor`       | Sensor, `water`, m³; cumulative statistics policy below          |
| Reported period usage  | Matching `difference`    | Sensor, m³, no statistical state class initially                 |
| Billing period         | Matching `invoicePeriod` | Sensor, `date`                                                   |
| Next verification      | `nextCheckDate`          | Sensor, `date`                                                   |
| Meter status           | `counterStatus`          | Diagnostic sensor; enum only after known status codes are mapped |

Model, meter type, and serial belong in device metadata or stable attributes.
Do not guess manufacturer from `model.name`: the observed value `APATOR` alone
does not establish that it is a model rather than a manufacturer label.
An additional record-created timestamp is possible, labelled carefully; it is
not a physical reading timestamp.

Optional later account entities can expose amount due, last payment amount/date,
and correctly classified tariffs. Currency amounts use UAH; a rate in UAH/m³
should not claim the monetary device class, which expects a currency unit.
Monthly invoice history and annual averages need separate reconciliation work.

## Water statistics

For a stable physical meter whose cumulative register does not reset, propose
`SensorDeviceClass.WATER`, m³, and `SensorStateClass.TOTAL` without `last_reset`.
Current developer guidance favors that for lifetime totals. Use
`TOTAL_INCREASING` only after establishing reset semantics; it can treat a
decrease as a reset and corrupt usage totals when the real cause is a correction.
See [HA sensor semantics](https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/core/entity/sensor.md).

This is a delayed register value. Ordinary entity updates record the increase
when HA receives it, not spread across the month when water was consumed.
Energy dashboard compatibility does not create accurate daily usage or import
old history automatically. Document this limitation in the eventual UI/docs.
Do not publish historic monthly volume as a current `MEASUREMENT`, or invent
hourly/daily points. Leave historical-statistics import outside the first version.
See [HA water tracking](https://www.home-assistant.io/docs/energy/water/).

A meter replacement should normally create a separate device/entity identity.
Confirm whether provider meter IDs/codes change on replacement before promising
continuity. Never use an array index, display name, or historical detail ID as
an entity unique ID.

## Identity and data ownership

Discover service-specific accounts and meters from the server. Candidate stable
keys are provider code plus meter `counterCode`/numeric `id`; validate stability
across reloads and changes before finalizing. Sensor unique IDs add the sensor
key. Keep physical meter identity independent of mutable names and account labels.

Group the account picker by provider/account code, retaining all associated
service-specific numeric account IDs. Do not collapse water, subscription, and
penalty rows into one internal account object. Prevent duplicate device creation
when the same meter is visible through more than one login.

The copied LUN Misto Air station-subentry rules are not automatically the right
model for this service. Do not retain station selection, geographic lookup,
AQI calculations, or its historical migrations when scaffolding Kyiv Vodokanal.

## Validation before claiming support

1. Verify fresh login, token persistence across HA restart, expiry, and supported
   renewal without automating or bypassing CAPTCHA. Test bearer-only API access.
2. Add synthetic parser tests for missing values, multiple service accounts,
   multiple meters/factor types, corrections, and meter replacement.
3. Test config flow, reauth, initial refresh, retryable outages, unload, stable
   unique IDs, and diagnostic redaction.
4. Validate sensor units and statistics with the supported HA version. The
   template currently pins HA 2026.2.3; current docs may describe newer APIs.
5. Run repository lint/tests and the current HA Bronze checklist when actual
   integration code exists. No runtime checks or quality-scale compliance are
   claimed by this documentation-only investigation.

## Unresolved decisions

- Supported login/renewal mechanism versus accepting manual reauthentication?
- First release limited to meter data, or include amount due as well?

Reading submission, payments, verification orders, charts, and historical
statistics import were not requested for the first implementation. Documenting
their existence does not authorize adding or invoking them.
