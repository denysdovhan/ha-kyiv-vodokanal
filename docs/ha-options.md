# What can be exposed to Home Assistant

Menu of candidate features, 2026-10-28. Pick by number. Sources and caveats are in
[data-model.md](data-model.md) and [api.md](api.md); design rules are in
[home-assistant.md](home-assistant.md).

**Key limitation:** readings are monthly billing records entered by an operator,
bank, or the consumer. There is no live flow data, leak detection, or hourly
usage. Everything below updates at most once a month, apart from payments.

Rec column: **v1** = recommend for the first release, **later** = useful but needs
more investigation, **skip** = low value or risky.

## Per water meter (one device per meter)

| #   | Feature                              | API source                                            | HA representation                                            | Useful for                                                                                   | Rec                                          |
| --- | ------------------------------------ | ----------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------- | -------------------------------------------- |
| 1   | Meter reading                        | `factors[].endFactor`                                 | Sensor, `water`, m³, `total`                                 | Energy dashboard water source; dashboards                                                    | **v1**                                       |
| 2   | Latest reported period usage         | `factors[].difference`                                | Sensor, `water`, m³, no state class                          | Usage cards, high-usage alerts. The latest record can be older than last month; pair with #3 | **v1**                                       |
| 3   | Billing period of last reading       | `factors[].invoicePeriod`                             | Sensor, `date`                                               | Show which month the reading belongs to                                                      | **v1**                                       |
| 4   | Reading recorded at                  | `authorInfo.dc`                                       | Sensor, `timestamp`, diagnostic (like opower `last_changed`) | Alert "no reading this month yet"                                                            | later                                        |
| 5   | Reading source                       | `factorInputSource.name` (operator / bank / consumer) | Diagnostic sensor, disabled by default                       | Know whether the reading is estimated by the operator                                        | later                                        |
| 6   | Next verification date               | `nextCheckDate`                                       | Sensor, `date`                                               | Reminder automation weeks before the deadline                                                | later (dropped from v1 by user)              |
| 7   | Last verification date               | `checkDate`                                           | Sensor, `date`, diagnostic, disabled                         | Reference only                                                                               | skip                                         |
| 8   | Meter status                         | `counterStatus.name`                                  | Diagnostic sensor                                            | Alert if a meter stops being "working"                                                       | later (only one status value seen)           |
| 9   | Reading submission window open       | `factorEditing`                                       | Binary sensor                                                | Reminder "submit your reading now"                                                           | later (semantics unclear, see data-model.md) |
| 10  | Meter model, serial, type (cold/hot) | `model`, `counterNumber`, `counterType`               | Device info, not entities                                    | Identify meters                                                                              | **v1**                                       |

## Energy dashboard history

| #   | Feature                  | API source                                   | HA representation                                                                                               | Useful for                                                                  | Rec                            |
| --- | ------------------------ | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------ |
| 11  | Backfilled monthly usage | `counter/factors/history`                    | External statistics via `async_add_external_statistics` (opower/tibber pattern), backdated to the billing month | Correct monthly bars in the Energy dashboard, plus past months from day one | v2 (reconciliation unverified) |
| 12  | Backfilled monthly cost  | Actual billed amounts, or historical tariffs | External cost statistics                                                                                        | Water cost history in the Energy dashboard                                  | later                          |

Without #11, the Energy dashboard uses #1, and each month's usage shows up as one
spike in the hour HA fetched the new reading. Monthly totals stay roughly right;
daily and weekly views are wrong. #11 moves usage to the right **month** only:
monthly records cannot show when within the month water was used.

#11 is blocked on history reconciliation: bank and operator rows can share a
month, and corrections are unverified. Imported history uses its own statistic
ID (`kyiv_vodokanal:<meter>_consumption`, as opower does), separate from #1. The
user picks one of them as the Energy dashboard water source; adding both counts
the same water twice. The docs and UI must say so.

#12 cannot use current tariffs for past months, since tariffs change. It needs
billed amounts (#26) or historical tariffs. The `tariff` endpoint accepts
`dateFrom`/`dateTo` in frontend source; that variant is untested.

## Per personal account (one device per account)

| #   | Feature                     | API source                                                                                          | HA representation       | Useful for                                                                                              | Rec    |
| --- | --------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------- | ------ |
| 13  | Amount to pay               | `amount_to_pay.amountToPay` (closing balance of the last closed month, all services)                | Sensor, `monetary`, UAH | "Bill due" notification, dashboard card                                                                 | **v1** |
| 14  | Unpaid from previous months | Derived from the last finalized invoice history rows: `debt − amountPaided`, summed across services | Sensor, `monetary`, UAH | Alert when an older balance is still unpaid. **No due date** exists in the API; do not label it overdue | **v1** |
| 15  | Last monthly bill           | `amount_to_pay.billAmount` (charges of the last closed month)                                       | Sensor, `monetary`, UAH | Household budgeting: the actual bill, including fixed fees and corrections                              | **v1** |

Do **not** expose the raw `debt` field as "Debt". It is the **opening balance** of
the last closed month and is usually already paid. A user who paid in full still
sees a non-zero `debt`. See [data-model.md](data-model.md#amount-to-pay-semantics).
| 16 | Last payment amount and date | `payments/history` | Sensors, `monetary` + `date` | "Payment received" notification; check a payment reached Vodokanal. The request filters by provider only, so filter rows by account in code | **v1** |
| 17 | Tariffs: water, wastewater (UAH/m³), subscription fee (UAH/month) | `tariff` | Sensors, unit `UAH/m³` / `UAH` | Energy dashboard "entity with current price". This is an **estimate**: it excludes the subscription fee, corrections, and other charges, and applies today's price going forward only | **v1** |
| 18 | Invoice breakdown (subsidy, privilege, correction, prepaid, charges) | `invoices/history-with-dynamic-invoices` | Sensors or attributes | Detailed bill cards | skip |
| 26 | Monthly bill per service (water vs subscription fee vs penalty) | `invoices/history-with-dynamic-invoices`, one row per service | Sensors, `monetary`, UAH | See what the fixed fee costs separately. Current-month rows are provisional (`id: null`) | later (optional detail) |

Billed amounts (#15, #26) and estimated cost (#17) stay separate sensors. Never
present the estimate as the bill.
| 19 | Residents count | `apartmentDetail.personalCount` | Diagnostic sensor | Rarely useful | skip |

## Other platforms and actions

| #   | Feature                                                   | HA representation                                                                                              | Useful for                                                                                              | Rec                                                                                                                                                                                           |
| --- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 20  | Submit meter reading                                      | Action `kyiv_vodokanal.submit_reading` (`POST counter/factor`)                                                 | Auto-submit from a smart water meter (Zigbee/ESPHome) every month                                       | later, **write API, never tested**                                                                                                                                                            |
| 21  | Calendar: verification due, submission window, bill dates | `calendar` entity                                                                                              | Calendar cards, calendar-triggered automations                                                          | later                                                                                                                                                                                         |
| 22  | Repair issue when verification is overdue                 | Repairs                                                                                                        | Visible warning in Settings                                                                             | later                                                                                                                                                                                         |
| 23  | Download receipt PDF                                      | Action                                                                                                         | Archive bills                                                                                           | skip                                                                                                                                                                                          |
| 24  | Diagnostics download (redacted)                           | `diagnostics.py`                                                                                               | Support and debugging                                                                                   | **v1** (quality scale)                                                                                                                                                                        |
| 25  | Last successful sync                                      | `timestamp` diagnostic sensor, set by the integration on each successful fetch (opower `last_updated` pattern) | Tell "Vodokanal reports the same reading" apart from "HA has not connected for days"; stale-data alerts | **v1**                                                                                                                                                                                        |
| 27  | Service price per m³                                      | Derived: water supply + wastewater tariff                                                                      | Sensor, `UAH/m³`, no device class                                                                       | Energy dashboard "entity with current price": every m³ is billed for both services, and the dashboard takes one price entity. Excludes the flat subscription fee and wastewater for hot water | **v1** (added after testing) |

## Not available from this API

- Live water flow, leak detection, hourly or daily usage.
- Planned or emergency water outages: not in the portal API. The public site has a
  [planned and emergency outages page](https://vodokanal.kyiv.ua/shutoffs);
  its format and data source are not investigated yet.
- Hot water from other providers: the platform supports several providers, but only
  Kyivvodokanal accounts were observed.

## Ukrainian names: match the portal

Ukrainian entity and device names reuse the portal's own labels, so users
recognize the values from [my.vodokanal.kiev.ua](https://my.vodokanal.kiev.ua).
Labels collected 2026-10-29 from the dashboard, Лічильники, Абон книжка, and
Здійснені платежі pages; field mapping verified against API values.

| #   | Portal label (uk.json)                                                                                             | Where in portal                   | API field                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------- | ------------------------------------------------------------------- |
| 1   | Останній показ                                                                                                     | Лічильники card                   | `factors[].endFactor`                                               |
| 2   | Об'єм                                                                                                              | Лічильники card                   | `factors[].difference`                                              |
| 3   | _no own label_; approved "Дата останнього показу"                                                                  | Date shown under "Останній показ" | `factors[].invoicePeriod`                                           |
| 6   | Повірка (caption: "Термін повірки закінчується")                                                                   | Лічильники card                   | `nextCheckDate`                                                     |
| 10  | Device: "Лічильник №{counterNumber}"; approved "Лічильник води №{number}"                                          | Dashboard meter card              | `counterNumber`                                                     |
| 13  | До оплати                                                                                                          | Dashboard                         | `amount_to_pay.amountToPay`                                         |
| 14  | _no own label_; approved "Борг за попередні періоди"                                                               | (derived)                         | `debt − amountPaided`                                               |
| 15  | Нараховано                                                                                                         | Абон книжка column                | `billAmount`                                                        |
| 16  | _section_ "Останні платежі"; columns "Сума", "Дата". Approved: "Останній платіж" / "Дата останнього платежу"       | Dashboard, Здійснені платежі      | `payments/history`                                                  |
| 17  | Централізоване водопостачання (ХВ) · Централізоване водовідведення (ГВ) (ХВ) · Плата за абонентське обслуговування | Dashboard "Діючі тарифи"          | tariff rows by code: subService `12`, subService `11`, service `35` |
| —   | Account device: "Особовий рахунок {code}"                                                                          | Здійснені платежі column          | `invoiceAccount.code`                                               |
| 25  | _HA-only_; approved "Остання синхронізація"                                                                        | —                                 | integration clock                                                   |
| 27  | _no own label_; approved "Вартість послуг"                                                                         | —                                 | water supply + wastewater tariff                                    |

Other portal labels for later features: Борг на поч. міс. (`debt`), Пільги
(`privileg`), Субсидії (`subsidy`), Оплачено (`amountPaided`), Борг на кін. міс.
(`amountToPay` per month), Середній річний (annual average usage, meter card).

Classify tariffs by these codes, not by name text. Names come from translations,
not from API strings, so a provider renaming a service does not rename entities.

## Recommended v1

1, 2, 3, 10 (meter) · 13, 14, 15, 16, 17 (account) · 24, 25 (support).
History backfill (#11) moves to v2 until reconciliation is verified.

**Main goal (user, 2026-10-29):** water usage in the Energy dashboard and in custom
dashboards. #1 is the Energy dashboard source in v1; #11 is the follow-up that
places each month's usage correctly.

## Open questions before building

1. How far back does `counter/factors/history` go? (Needed for #11.)
2. Which history row wins when bank and operator rows share a month? (Needed for #11.)
3. What `factorEditing` fields mean in practice? (Needed for #9 and #21.)
4. ~~Does `amountToPay` equal `debt + billAmount`?~~ **Answered 2026-10-29: no.**
   `amountToPay = debt − amountPaided + billAmount`; see data-model.md.
5. ~~How do `correction`, `prepaid`, `subsidy`, and `privileg` enter that formula?~~
   **Mostly answered 2026-10-29** from the portal UI and vodokanal.kyiv.ua:
   `amountToPay = debt + billAmount − privileg − subsidy − amountPaided`. Subsidies
   and most benefits are paid in cash, so these fields are usually zero.
   Corrections are probably inside `billAmount`. #14 now avoids the issue by using
   `debt − amountPaided`. Still unverified on a real account with non-zero values;
   prepayment remains unknown, so allow negative balances.
