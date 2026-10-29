# Observed data structures

Observed 2026-10-28 from successful browser requests. Examples below are
synthetic, reduced objects, not reusable account credentials or complete schemas.

## Account links

`invoice_accounts` returns an array. Each element links a consumer to an account
for one service:

```json
[
  {
    "id": 101,
    "consumerUserId": 201,
    "invoiceAccount": {
      "id": 301,
      "code": "EXAMPLE_ACCOUNT",
      "name": "Example customer",
      "legalEntityType": { "id": 1, "name": "Фізична" },
      "service": {
        "id": 10,
        "code": "2",
        "name": "Централізоване водопостачання та водовідведення",
        "serviceType": { "id": 16, "name": "Водопостачання та водовідведення" }
      },
      "address": {},
      "route": null,
      "constrictAddress": { "id": 401, "name": "Example address" }
    },
    "serviceProvider": {
      "id": 10,
      "code": "889",
      "name": "Київводоканал",
      "invoicePeriod": null
    },
    "apartmentDetail": {
      "calcArea": 0,
      "heatArea": 0,
      "personalCount": 1,
      "realPersonalCount": 0
    }
  }
]
```

The observed account number appeared in three records: water service,
subscription fee, and penalty. Each had a different `invoiceAccount.id` and
link `id`. Keep them distinct. Account selection can group by provider code and
display account code, while internal service lookup retains numeric account IDs.

`address` can contain `city`, `street`, `building`, and `flat`. Each can contain
IDs, names, full names, type, prefix/postfix, and `prefixNamePostfix`.
Redact the entire structure, not just the top-level customer name.

## Latest meter snapshot

`counters/last-factors` returns an array of these; the per-meter endpoint returns
one object:

```json
{
  "id": 501,
  "counterCode": "EXAMPLE_COUNTER_CODE",
  "counterNumber": "EXAMPLE_SERIAL",
  "service": { "id": 10, "code": "2", "name": "Water service" },
  "serviceProvider": { "id": 10, "code": "889", "name": "Київводоканал" },
  "dateFrom": "2026-10-21T09:00:00Z",
  "dateTo": null,
  "checkDate": "2023-01-01T00:00:00Z",
  "nextCheckDate": "2027-01-01T00:00:00Z",
  "model": { "name": "APATOR" },
  "counterStatus": { "id": 3, "name": "Прилад обліку наявний та працює" },
  "counterType": { "id": 2, "code": "000000002", "name": "Холодна вода" },
  "factorInputSource": { "id": 3, "name": "Оператор" },
  "installationLocation": { "id": null, "name": null },
  "invoiceAccount": { "id": 301, "code": "EXAMPLE_ACCOUNT" },
  "factorEditing": { "isEnabled": true, "startDay": 1, "endDay": 6 },
  "position": null,
  "factors": [
    {
      "invoicePeriod": "2026-10-01T00:00:00Z",
      "beginFactor": 100.0,
      "endFactor": 102.5,
      "difference": 2.5,
      "factorType": null
    }
  ],
  "contragents": null,
  "departments": null,
  "authorInfo": { "dc": "2026-10-20T20:59:01Z", "uc": 601 }
}
```

The nested `invoiceAccount` is much larger in the actual response, including
customer name and address. Service objects may include `serviceType`.

| Field                        | Interpretation / caution                                                    |
| ---------------------------- | --------------------------------------------------------------------------- |
| `id`                         | Numeric meter ID, used in the per-meter endpoint                            |
| `counterCode`                | Provider meter identifier; string, preserve leading zeros                   |
| `counterNumber`              | Physical meter serial displayed in the UI                                   |
| `factors[].endFactor`        | Latest cumulative meter register value                                      |
| `factors[].beginFactor`      | Beginning register value for that record's period                           |
| `factors[].difference`       | Period volume; UI identifies cubic metres for the observed cold-water meter |
| `factors[].invoicePeriod`    | Billing period, **not actual reading/submission time**                      |
| `checkDate`, `nextCheckDate` | Verification dates                                                          |
| `authorInfo.dc`              | Record creation timestamp; not proven physical measurement time             |
| `dateFrom`, `dateTo`         | Record validity fields; do not assume installation/removal dates            |
| `factorType`                 | Null in the observed meter; multiple factor types remain untested           |

The portal displays the billing period as the date under "Останній показ".
History showed that the record was entered later in that month. Expose a
"Billing period" date separately from "Reading recorded at".

Do not derive submission availability from `factorEditing` yet. The observed
`startDay=1`, `endDay=6`, and `isEnabled=true` do not match the visible notice
about readings being unavailable during the first ten days. Their semantics
have not been established.

The simpler `/counters` endpoint uses `code` and `number`, not `counterCode`
and `counterNumber`. It includes `installationPlace`, `checkDate`,
`nextCheckDate`, `counterType`, `counterStatus`, `beginFactor`, `endFactor`,
`address`, `contragent`, and `department`. `beginFactor` and `endFactor` were
null even when the latest-factors endpoint had readings. Do not use it as the
reading source.

## Reading history

Each history row contains:

```json
{
  "id": 701,
  "counterId": 501,
  "invoicePeriod": "2026-10-01T00:00:00Z",
  "beginFactor": 100.0,
  "endFactor": 102.5,
  "difference": 2.5,
  "factorType": null,
  "factorInputSourceId": 3,
  "factorInputSource": { "id": 3, "name": "Оператор" },
  "fileId": null,
  "authorInfo": { "dc": "2026-10-20T20:59:01Z", "uc": 601 },
  "service": { "id": 10, "code": "2", "name": "Water service" },
  "counter": {
    "id": 501,
    "code": "EXAMPLE_COUNTER_CODE",
    "counterNumber": "EXAMPLE_SERIAL",
    "checkDate": "2023-01-01T00:00:00Z",
    "nextCheckDate": "2027-01-01T00:00:00Z",
    "counterDetail": [
      {
        "id": 801,
        "diameter": 15,
        "counterType": { "id": 2, "code": "000000002", "name": "Холодна вода" },
        "counterStatus": { "id": 3, "name": "Прилад обліку наявний та працює" },
        "invoiceAccount": { "id": 301, "code": "EXAMPLE_ACCOUNT" }
      }
    ]
  },
  "position": null
}
```

The same meter/month can have both a bank row with zero difference and an
operator row with positive difference. `counterDetail[].id` also changes between
historical periods. Neither that detail ID nor a month alone identifies a meter.

Keep raw row IDs and timestamps available to a future history parser. Do not
sum every history row or invent a "latest row wins" reconciliation rule without
checking corrected and nonzero duplicate records. The latest-factors endpoint
avoids that unresolved aggregation problem for a first current-state integration.

## Financial structures

| Endpoint      | Fields observed                                                                                                                 |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Amount to pay | `debt`, `billAmount`, `amountToPay`                                                                                             |
| Tariff rows   | `invoiceId`, `billingDate`, `tariffAmount`, `invoiceAccount`, `service`, nullable `subService`, `serviceProvider`, `authorInfo` |
| Payment rows  | `id`, `bankCode`, `payment`, `financePoint`, `service`, `serviceProvider`, `invoiceAccount`                                     |
| Invoice rows  | Nullable `id`, `serviceProvider`, `service`, `invoiceAccount`, `detail`, `authorInfo`                                           |

Payment objects contain `id`, `date`, `statusId`, `amount`, `sumCommiss`,
`cardPattern`, `invoiceId`, `externalTran`, `internalTran`, `consumerUserId`,
`dc`, and `uc`. Several were null in the observed records. Avoid storing payment
processor IDs or masked card data in HA entities or diagnostics.

Invoice `detail` contains `billingDate`, `amountPaided` (actual API spelling),
`amountToPay`, `billAmount`, `volume`, `debt`, `prepaid`, `regularPayment`,
`correction`, `privileg` (actual spelling), `subsidy`, `levy`, and `charges`.
Provisional current-month rows had `id: null`; they are not finalized invoices.

### Amount to pay semantics

**Live, 2026-10-29**, one account, six months of invoice history, two services
(water and subscription fee). Each invoice `detail` row is a monthly balance:

| Field                                | Meaning                                                                                      |
| ------------------------------------ | -------------------------------------------------------------------------------------------- |
| `debt`                               | Opening balance at the start of the billing month; equals the previous month's `amountToPay` |
| `amountPaided`                       | Paid during the month                                                                        |
| `billAmount` (= `charges` in sample) | Charged for the month                                                                        |
| `amountToPay`                        | Closing balance: `debt − amountPaided + billAmount`                                          |

The formula held for every finalized row. `correction`, `prepaid`, `subsidy`,
and `privileg` were zero throughout. The current provisional row (`id: null`)
has `billAmount: 0` and `amountToPay = debt`.

**How the other fields fit in (Source/Proposal, 2026-10-29).** Not verified
numerically; no account with non-zero values has been seen.

- **Portal billing page (Абонентська книжка)** columns, in order: Борг на поч. міс.
  (`debt`), Нараховано (`billAmount`), Пільги (`privileg`), Субсидії (`subsidy`),
  Оплачено (`amountPaided`), Борг на кін. міс. (`amountToPay`). The frontend
  computes nothing; all values come from the server. `correction`, `prepaid`,
  `charges`, `levy`, and `regularPayment` are never displayed.
- **Expected general formula** (standard Ukrainian billing-book layout, consistent
  with the observed data):
  `amountToPay = debt + billAmount − privileg − subsidy − amountPaided`.
- **Subsidies and most benefits are paid in cash** by the Pension Fund to the
  consumer (CMU №373/2019, №1041/2022; [vodokanal.kyiv.ua/subsidiyi-ta-pilgi](https://vodokanal.kyiv.ua/subsidiyi-ta-pilgi)).
  The consumer pays the full bill, so the money appears in `amountPaided`, and
  `subsidy`/`privileg` are zero for most accounts.
- **Non-cash benefits still exist.** Per the [FAQ](https://vodokanal.kyiv.ua/for-home/faq),
  social-protection offices send providers monthly beneficiary lists (CMU №389/2015).
  For those accounts `privileg` can be non-zero and reduces the closing balance.
- **Corrections (перерахунок)** are posted in the bill for the month they are
  confirmed (portal notice; FAQ: after a controller's check reading). With no
  correction column in the UI, they are most likely folded into `billAmount`.
  Their sign and the `correction` field's relation to `billAmount` are **Unknown**.
- **Prepayment/overpayment**: no source found. A negative `debt`/`amountToPay`
  is plausible but unobserved; parsers must accept negative balances.

`invoice-detail?invoiceId=` returns per-sub-service charge lines (e.g. water
supply, wastewater, subscription fee), each with `volume`, `tariffAmount`,
`billAmount`, `tariffId`, and `billingDate`. No correction, benefit, or
prepayment fields. This gives billed volume and the tariff actually applied per
month, which is the input historical cost statistics (#12) need. The response
also contains the customer name and full address; redact them.

`GET invoice/amount_to_pay` returns `{debt, billAmount, amountToPay}` for the
**last closed month**, summed across all services that share the account code.
Each value equalled the sum of the corresponding fields on the last finalized
invoice rows. It omits `amountPaided`; derive it as `debt − amountToPay + billAmount`.

Consequences:

- `amountToPay ≠ debt + billAmount`.
- `debt` is non-zero for an account paid in full; do not present it as debt.
- Unpaid carry-over from earlier months is `debt − amountPaided`. Compute it from
  invoice history rows, which carry `amountPaided`. The shortcut
  `amountToPay − billAmount` from the `amount_to_pay` endpoint is wrong for
  accounts with benefits or subsidies.
- Querying any of the service-specific account links returns the same totals.

**Do not map invoice `detail.volume` to water consumption.** In observed data it
matched monetary amounts, including the subscription fee. Meter
`factors[].difference` is the water-volume source with UI support.

Tariffs include water supply, wastewater, and a flat subscription charge.
Classify each by service/subservice before assigning units. A flat fee is UAH,
whereas a volumetric tariff is UAH/m³. The payload did not include an explicit
unit field. The dashboard's displayed tariff date differed from the returned
`billingDate`; do not label that field "effective from" without checking logic.

## Parser requirements

- Preserve identifier strings, nullable fields, and decimal precision. Never
  turn missing values into zero or assume `factors[0]` exists.
- Keep billing dates, record timestamps, and observation time distinct. Parse
  timestamps as timezone-aware; preserve month labels across timezone conversion.
- Separate the API shapes from HA entities with small plain Python data classes.
- Redact tokens, cookies, profile data, full nested addresses, consumer IDs,
  account/meter identifiers, author user IDs, and payment references in diagnostics.
- Test empty meters, multiple accounts/services, unordered factors, duplicate
  history rows, nullable type/model/source, corrections, and replacement meters.
