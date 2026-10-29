# Authentication renewal investigation

Evidence date: 2026-10-28. Research only; no integration code changed.
This file supplements the parallel investigation in [mobile-api.md](mobile-api.md)
without changing that agent's files.

## Conclusion

Weekly **manual** sign-in is not inherently required by a seven-day access token.
The verified mechanism is repeated password authentication: retain the
Vodokanal account/password and request a new access token when needed. This is
a fresh login performed by the client, not an OAuth refresh-token exchange.

The parallel investigation records a successful real-account, password-only
login without reCAPTCHA and successful bearer-only reads. That establishes the
required building block. A subsequent user-run test confirmed repeated login:
the second login issued a different token for the same subject with a later
expiry, both tokens authorized reads, and the first remained valid afterward.
Automatic renewal in HA is still a proposal; actual seven-day expiry and HA
runtime behavior have not been tested.

No Vodokanal refresh-token endpoint was identified in the inspected clients.
That is narrower than saying no refresh endpoint exists anywhere on the server.
Do not guess endpoint names or infer a refresh grant from unrelated SDK code.

## Evidence and confidence

| Observation                                                                                                      | Source                                                                                                | What it establishes                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Password POST returns `accessToken` and `tokenType`; JWT lifetime 604800 seconds                                 | Parallel agent's real-account result recorded in `mobile-api.md`; its local test script was inspected | Noninteractive password login is possible for the tested account; no refresh token in that response                          |
| Mobile-issued bearer works without cookies on both hosts                                                         | Same recorded live test                                                                               | A browser session is not required for the tested reads                                                                       |
| Two consecutive password logins succeed; token B differs and expires five seconds later; A still works afterward | User-provided output from `vodokanal-renewal-check.py`, 2026-10-28                                    | New access tokens can be obtained without manual browser login or immediately invalidating the first tested token            |
| `LoginResponse`, `accessToken`, `tokenType` are visible in the installed app                                     | Independent static inspection, app 1.1.6, bundle `com.kyivvodocanal.kvk`                              | Native client model agrees with the recorded response                                                                        |
| Password, email-checking, and social-token authentication paths are visible; no refresh/renew path identified    | Readable strings in `INFOMISTO` executable                                                            | Supports password reauthentication as the available route; not an exhaustive server contract                                 |
| `currentUserSessionHasExpired`, `AuthManager`, `KeychainManager` are visible                                     | Same executable                                                                                       | App has session-expiry and credential-storage concepts; does not prove which credentials are stored or how expiry is handled |
| `refreshToken` appears alongside Firebase Installations validation and methods                                   | Same executable                                                                                       | These strings are not evidence of a Vodokanal account refresh token                                                          |
| Website checks JWT expiry and its route guard redirects expired sessions to `sign-in`                            | Previously captured public Angular bundle                                                             | The inspected website does not demonstrate transparent Vodokanal renewal                                                     |

The executable reports `LC_ENCRYPTION_INFO_64`, `cryptid 1` (4,096 bytes encrypted).
Readable strings and metadata remain available, but runtime method behavior was
not verified. No decryption, patching, pinning bypass, app-data modification, or
Keychain credential extraction was performed.

Website evidence comes from `main.5d6e6972443c9cf7.js`, SHA-256
`304c9c2a005b4200697a276c03231fdcaff1df38b1b29ca994b738bea2236d0e`.
Its `isLoggedIn()` delegates to `jwtHelper.isTokenExpired()`, and `canActivate()`
redirects to `sign-in` when false. `refreshAuthToken`/`refreshAccessToken` occur
in the social-login library; no application invocation was identified. The
Google implementation's method named `refreshToken` invokes Google ID revocation,
so its name alone is particularly misleading.

## Observed login contract for automatic renewal

Send a new request over verified HTTPS:

```http
POST https://warreg.ssmt.com.ua:5443/api/account/authentication
Content-Type: application/json
Accept: application/json
```

```json
{ "account": "user@example.invalid", "password": "<stored password>" }
```

The observed successful response fields are:

```json
{ "accessToken": "<new JWT>", "tokenType": "<server value>" }
```

No previous token, cookie, browser automation, or CAPTCHA response was needed
in the recorded password-login test. Consequently, the previous token's expiry
should not prevent this independent login; this is an inference to validate,
not an observed expired-session test. Never edit a JWT's `exp` to test expiry:
that invalidates its signature and tests a different failure condition.

This proposal covers Vodokanal password accounts. Google/Apple-only accounts
need a separately established credential or supported authorization flow. Do
not assume their SDK refresh tokens can refresh the Vodokanal bearer, reuse
the app's OAuth client identity in HA, or ask users for their Google password.

## Home Assistant behavior proposal

1. During setup, authenticate once and validate a read-only account request.
   Persist the account/password and current token/expiry in config entry data;
   keep client/coordinator objects in `entry.runtime_data`.
2. Before a poll, replace a missing token or one within five minutes of expiry.
   Read `exp` for scheduling only; server validation determines token validity.
   Persist a replacement only after validating its response and account identity.
3. On an unexpected HTTP 401, authenticate once and retry the original read once.
   Serialize login attempts with one client-level lock and recheck the token
   after acquiring it so concurrent reads do not produce a login burst.
4. If login confirms invalid credentials, request user reauthentication. Network
   errors, 429, and 5xx remain retryable with backoff; they must not produce a
   weekly password prompt or an unbounded authentication loop. A generic 403
   is not automatically proof that the password is wrong.
5. After restart or a long outage, reuse a still-valid stored token or obtain a
   new one using the stored password. Polling need not run exactly at expiry:
   the client checks before its next request.

Five minutes is a proposed clock-skew margin, not a provider requirement. With
six-hour polling, authentication occurs before the first poll that needs it,
approximately once a week, rather than on every sensor read.

Use `ConfigEntryAuthFailed` from setup/coordinator only after automatic recovery
cannot resolve an authentication failure. See current HA
[setup failure guidance](https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/integration_setup_failures.md)
and [reauthentication flows](https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/core/integration/config_flow.md).
The provider interface observed here is not an OAuth token endpoint; the HA
OAuth helper must not be adopted merely because the response contains a JWT.

Persisted passwords are a material tradeoff. Treat HA configuration and backups
as sensitive; do not describe config entry storage as an encrypted vault.
Redact passwords, tokens, account identifiers, addresses, and authentication
response bodies from logs/diagnostics. See HA
[diagnostics guidance](https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/core/integration/diagnostics.md).

## Repeated-login validation

A temporary local script, `/tmp/vodokanal-renewal-check.py`, was prepared for
the user. It reads a password through `getpass`, performs two password logins
with no cookie jar or previous bearer attached to login, and prints only status
and nonsecret metadata. Its JWT metadata parser self-check passed. The user ran
the live test and supplied these sanitized results on 2026-10-28:

```text
LOGIN_A 200
RESPONSE_FIELDS ['accessToken', 'tokenType']
TOKEN_A {"lifetime_seconds": 604800}
READ_A 200
LOGIN_B 200
RESPONSE_FIELDS ['accessToken', 'tokenType']
TOKEN_B {"lifetime_seconds": 604800}
READ_B 200
RENEWAL {"token_changed": true, "same_subject": true, "expiry_advanced_seconds": 5}
READ_A_AFTER_B 200
```

The sequence checked login A and an authenticated read, then login B and a read,
whether the token changed with a later `exp` and the same subject, and whether
token A still worked after B was issued. No immediate revocation of A was
observed; this does not prove all mobile/browser sessions remain valid.
No credentials, tokens, or account response data are written to disk.

## Validation still needed

The successful two-login check does not prove behavior after seven days,
server policy stability, rate limits, or provider support for third-party use.
An integration should separately test simulated expiry/401, concurrent renewal,
restart persistence, rejected credentials, and transient failures, then validate
one real expiry boundary before claiming long-term reliability.
