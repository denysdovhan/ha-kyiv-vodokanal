# Mobile API investigation

Investigated 2026-10-28. This is capture setup evidence, not an API contract.

## Result: mobile backend shares the website API, without reCAPTCHA

The iOS app is a **native Swift app (codename INFOMISTO)**, not Flutter/React
Native. Its main binary is FairPlay-encrypted (`cryptid 1`), so method-level
logic was not read. The decisive facts came from **unauthenticated probes of the
backend host**, not from decrypting app traffic, so no pinning bypass was needed.

**`warreg.ssmt.com.ua:5443` runs the same Spring API as `my.vodokanal.kiev.ua`.**
Identical paths return identical JSON. Protected reads give HTTP 401
`{"status":401,"error":"Unauthorized","message":"Користувач не авторизований"}`
on both hosts (e.g. `/api/warehouse/consumer/counters/last-factors`,
`/api/ud/profile`). Server banner is `nginx`; responses carry a
`tmx-correlation-id` header.

**Login on the mobile host does not require reCAPTCHA (Live).**
`POST /api/account/authentication` with only `{account, password}` (no
`recaptcha` field) is accepted and proceeds to credential validation: an unknown
address returns HTTP 401
`{"message":"Користувача з логіном: '<account>' не знайдено."}`. The website
frontend attaches reCAPTCHA, but the backend does not reject a request that
omits it. **This resolves the integration's main blocker** — a plain
email/password POST to this endpoint is a candidate unattended login, no browser
or challenge solver needed.

**Real-account login confirmed (Live, 2026-10-28).** The user ran a local
script with their own credentials; only response shapes were shared.

- `POST /api/account/authentication` `{account, password}` → **200**,
  body `{"accessToken": str, "tokenType": str}`. **No refresh token.**
- JWT claims `exp`, `iat`, `jti`, `sub`; lifetime **604800 s (7 days)**,
  same as the website token.
- **Bearer-only works** (no cookies) from a plain Python `urllib` client.
- **Tokens are interchangeable across hosts.** The mobile-issued token
  returned 200 for `invoice_accounts` and `counters/last-factors` on both
  `warreg.ssmt.com.ua:5443` and `my.vodokanal.kiev.ua`, with identical shapes
  to [data-model.md](data-model.md).

Renewal implication: with no refresh endpoint, re-run the password login before
`exp` or on a 401. HA must therefore store the password, not only the token.

### Renewal investigation (2026-10-28): no renewal mechanism exists

| Check                  | Method                                                      | Result                                                                                                                                                            |
| ---------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend renewal code  | Read `main.*.js` + all 16 lazy chunks                       | None. Token stored once in `localStorage`; any 401 logs out. Only `refreshToken` is the Google library (it calls `google.accounts.id.revoke`)                     |
| Backend refresh routes | Unauthenticated GET/POST; real routes give 405, unknown 404 | 10 conventional paths (`/api/account/refresh`, `/token/refresh`, `/authentication/refresh`, `/api/auth/refresh`, …) all 404. No server-side `logout` route either |
| Sliding session        | Real token, compare response headers                        | No token-like or `Set-Cookie` headers on login or reads                                                                                                           |
| Concurrent sessions    | Log in twice, reuse first token                             | Both tokens 200. New `jti`, same `sub`. Re-login does **not** revoke earlier tokens                                                                               |

**Verdict:** the only renewal is a fresh password login. Concurrent tokens are
allowed, so HA re-logging in will not sign the user out of the phone app or website.

> Only one unknown-account request was sent per host. Do not script repeated
> login attempts against this endpoint — that is credential probing, not research.

**Firebase is not the auth backend.** The bundled `GoogleService-Info.plist`
(project `vodokanal-mob-app`, sender `323314470692`) and the linked frameworks
(FirebaseAnalytics, Crashlytics, DynamicLinks, GoogleSignIn, AppAuth) cover
analytics, crash reporting, deep links, and the same Google-login path the
website offers. Account auth is the Spring backend above, reached via Alamofire

- Moya (both linked in `Frameworks/`).

App Transport Security in `Info.plist` whitelists cleartext to
`94.131.241.17:18543` — a probable staging/dev host. Out of scope; not probed.

## Observed traffic

## Observed traffic

After the user opened the iPhone app and meters screen, Proxyman on the Mac
recorded HTTPS `CONNECT` requests to `warreg.ssmt.com.ua:5443`, returning 200.
This is a candidate mobile backend. A successful CONNECT establishes a proxy
tunnel; it does **not** establish a successful application API response.
No decrypted request path, authentication header, payload, or response schema
has been verified yet. Do not assume the website API or its JWT works here.

The user-supplied mobile web address, <https://vodokanal-mob-app.web.app>,
returned a Firebase Page Not Found page at its root during browser inspection.

## Capture setup and current blocker

The iPhone sends traffic through the Mac's Proxyman HTTP proxy. The user
installed and configured certificate trust on the iPhone. HTTPS decryption
was subsequently verified for Safari on the same host and port (see below).

Proxyman reported a free limit of two SSL inspection rules, including disabled
rules. With explicit user approval, the disabled `gs-loc.apple.com` rule was
replaced. The disabled `sandbox.itunes.apple.com` rule was preserved.

An enabled hostname-only rule for `warreg.ssmt.com.ua` still produced encrypted
CONNECT entries after a new connection. Replacing it with an enabled rule for
the exact `warreg.ssmt.com.ua:5443` target caused Proxyman to attempt TLS
interception. Flow **268**, displayed at **23:00:14.490** on the capture Mac,
shows CONNECT, Proxyman status **999**, and **Possible Certificate Pinning**:
"The app may be rejecting Proxyman's generated certificate." This is a proxy
failure diagnostic, not an HTTP status returned by the application API.

The user reported reopening the app and meters without an on-screen connection
error. That does not establish a fresh successful meter fetch.

The user then opened `https://warreg.ssmt.com.ua:5443/` in iPhone Safari and
reported the **Welcome to nginx!** page. Proxyman captured decrypted Safari
flow **292**, `GET /`, **200 OK**, with 612 response bytes and readable request
and response headers. Flow **293** was `GET /favicon.ico`, **404**, with readable
headers. The Safari user agent and the same remote-device source were visible.
The root response's `Server` was `nginx` and `Content-Type` was
`text/html; charset=utf-8`. No API endpoint can be inferred from this default page.

This verifies routing, the exact inspection rule, and Safari trust of the proxy
certificate at this host/port. App-specific certificate handling, including
pinning or a separate trust store, is now the leading explanation for flow 268.
It is not proof of pinning. No app API body or authentication exchange was
decrypted, and repeated proxy/certificate setup is not justified by this result.

The Proxyman plugin's skills and bundled MCP bridge are installed. The bridge
can enumerate tools, but operational calls report that the app/MCP server is
not started. Settings > MCP confirms **Stopped**, a disabled Enable MCP Server
checkbox, and a lock icon in the trial build. Sensitive-data redaction remains
enabled. Inspection therefore used the GUI; no MCP flow details were available.

## App identity and Mac availability

App Store lookup (UA storefront, 2026-10-28):

| App                                                                  | Bundle ID                         | Version                    | Audience                              |
| -------------------------------------------------------------------- | --------------------------------- | -------------------------- | ------------------------------------- |
| [Київводоканал Цифровий](https://apps.apple.com/ua/app/id1611367709) | `com.kyivvodocanal.kvk`           | 1.1.6 (2025-11-04), ~30 MB | Households: bills, payments, readings |
| [Лічильники](https://apps.apple.com/ua/app/id6443618731)             | `com.photofixation.kyivvodocanal` | 1.0.1 (2023-10-24)         | Legal entities: photo meter readings  |

The household app reports `isIOSBinaryMacOSCompatible: true` ("Designed for
iPhone", macOS 13+, Apple M1+). It can be installed on this Mac from the Mac
App Store. The main executable stays FairPlay-encrypted, but bundle resources
(framework layout, JS bundles, Flutter assets, plists) are readable. This is a
static-analysis path that avoids defeating pinning on the iPhone.

`warreg.ssmt.com.ua:5443` presents a public Sectigo `*.ssmt.com.ua` certificate.
Pinning, if present, is app-side. `vodokanal-mob-app.web.app` belongs to Firebase
project `vodokanal-mob-app`. Whether the app uses Firebase Auth is **Unknown**.

## Next evidence to collect

1. Obtain a supported mobile API contract or a provider-controlled debug build
   that permits inspection; alternatively continue with the observed website API.
2. If mobile requests become readable, record sanitized field names for meters
   and reading history, then capture a user-driven login or renewal.
3. Determine whether mobile and website accounts, meters, and identifiers match.

The exact host inspection rule remains enabled. It may prevent the app from
connecting to that host. After capture, restore normal iPhone networking by
setting the Wi-Fi network's Configure Proxy setting to Off, or disable this
specific Proxyman inspection rule. No other domain needs inspection for this test.

Keep raw captures outside this repository: they may contain credentials,
addresses, account identifiers, and payment information. Export only the
relevant host and retain synthetic examples in documentation. Do not replay
reading submissions, payments, registration, or account changes for research.
