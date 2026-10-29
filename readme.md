[![SWUbanner](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua/)

<p align="center">
  <img src="./custom_components/kyiv_vodokanal/brand/logo.png" alt="Kyivvodokanal" width="100%" />
</p>

# 💧 Kyiv Vodokanal for Home Assistant

[![GitHub Release][gh-release-image]][gh-release-url]
[![GitHub Downloads][gh-downloads-image]][gh-downloads-url]
[![hacs][hacs-image]][hacs-url]
[![GitHub Sponsors][gh-sponsors-image]][gh-sponsors-url]
[![Buy Me A Coffee][buymeacoffee-image]][buymeacoffee-url]
[![Twitter][twitter-image]][twitter-url]

[**English**](./readme.md) | [Українською](./readme.uk.md)

Water meter readings, bills, payments, and tariffs from [Kyivvodokanal][kyivvodokanal] in [Home Assistant][home-assistant]. Water usage can be added to the Energy dashboard. Connect with the email and password of your [personal account][personal-account].

> [!NOTE]
> This integration is not affiliated with [Kyivvodokanal][kyivvodokanal]. It is developed by an individual. Data may differ from the official website.

## Sponsorship

Your generosity will help me maintain and develop more projects like this one.

- 💖 [Sponsor on GitHub][gh-sponsors-url]
- ☕️ [Buy Me A Coffee][buymeacoffee-url]
- Bitcoin: `bc1q7lfx6de8jrqt8mcds974l6nrsguhd6u30c6sg8`
- Ethereum: `0x6aF39C917359897ae6969Ad682C14110afe1a0a1`

## Installation

Add the custom repository to HACS, install the integration, and restart Home Assistant.

[![Add to HACS][hacs-install-image]][hacs-install-url]

<details>
<summary>Add the repository to HACS manually</summary>

1. Open **HACS → ⋮ → Custom repositories**.
2. Enter `https://github.com/denysdovhan/ha-kyiv-vodokanal` and select **Integration**.
3. Download **Kyiv Vodokanal** and restart Home Assistant.

</details>

<details>
<summary>Install without HACS</summary>

1. Copy `custom_components/kyiv_vodokanal` from this repository into your Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.

</details>

## Usage

Click the button and enter the email and password of your [personal account][personal-account]. Google sign-in is not supported.

[![Add Kyiv Vodokanal][install-image]][install-url]

<details>
<summary>Add the integration manually</summary>

1. Open **Settings → Devices & services → Add integration**.
2. Search for **Kyiv Vodokanal** and enter your email and password.

</details>

Each water meter and each personal account gets a separate device. Repeat setup to add another login.

![Kyiv Vodokanal integration page](./assets/integration.webp)

### Sensors

Ukrainian sensor names match the labels in the personal account.

#### Water meter №…

| Sensor              | Value                                                 |
| ------------------- | ----------------------------------------------------- |
| Latest reading      | m³; meter register, the Energy dashboard water source |
| Volume              | m³; usage in the latest billing period                |
| Latest reading date | Billing month the reading belongs to                  |

#### Personal account …

| Sensor                              | Value                                             |
| ----------------------------------- | ------------------------------------------------- |
| Amount to pay                       | UAH; balance at the end of the last closed month  |
| Debt from previous periods          | UAH; unpaid balance of earlier months             |
| Charged                             | UAH; charges of the last closed month             |
| Last payment, last payment date     | UAH and date; payments made on one day are summed |
| Water supply and wastewater tariffs | UAH/m³; current tariffs                           |
| Service price                       | UAH/m³; water supply and wastewater combined      |
| Subscription fee                    | UAH per month                                     |

The **Diagnostic** section has the time of the last successful sync.

### Energy dashboard

Open the Energy dashboard settings and add a source under water consumption:

[![Open energy configuration][energy-image]][energy-url]

1. Select **Water meter №… Latest reading** as the source.
2. For cost, use an entity with the current price: **Personal account … Service price**.

The cost is an estimate based on current tariffs. It excludes the subscription fee, wastewater for hot water, and recalculations. The **Charged** sensor shows the actual bill.

### Data updates

- Polling runs every 6 hours. A reading usually appears once a month, when you, your bank, or Kyivvodokanal submit it.
- Monthly usage lands in the Energy dashboard as one step when a new reading arrives. Daily and weekly charts are not accurate.
- The password is stored in Home Assistant. The integration signs in again when the session expires. If the password changes, Home Assistant asks for the new one.
- A new meter or personal account appears automatically after the next update.
- The integration only reads data. Submitting readings, payments, and meter verification are not supported.

### Removal

Open **Settings → Devices & services → Kyiv Vodokanal** and delete the entry from its menu. Then remove the integration in HACS or delete `config/custom_components/kyiv_vodokanal`.

## Development

Setup and checks are described in [contributing.md](./contributing.md).

## Other integrations

- 💥 [Aerial Danger](https://github.com/denysdovhan/ha-aerial-danger) — detects aerial-threat messages for selected Ukrainian regions and localities.
- ☁️ [Check Weather](https://github.com/denysdovhan/ha-check-weather) — creates a binary sensor based on forecast conditions for the next few hours.
- ☀️ [Fayna SES](https://github.com/denysdovhan/ha-fayna-ses) — provides battery levels, power flows, and energy data from Fayna SES stations.
- 💨 [LUN Misto Air](https://github.com/denysdovhan/ha-lun-misto-air) — provides air quality and environmental data from LUN Misto monitoring stations.
- 🌦️ [Ukrainian Hydrometeorological Center](https://github.com/denysdovhan/ha-ukr-hmc) — provides weather, radiation, and hydrology data from meteo.gov.ua.
- ⚡️ [Yasno Outages](https://github.com/denysdovhan/ha-yasno-outages) — provides planned electricity outage schedules, sensors, and calendars from Yasno.

## License

MIT © [Denys Dovhan][denysdovhan]

<!-- Badges -->

[gh-release-url]: https://github.com/denysdovhan/ha-kyiv-vodokanal/releases/latest
[gh-release-image]: https://img.shields.io/github/v/release/denysdovhan/ha-kyiv-vodokanal?style=flat-square
[gh-downloads-url]: https://github.com/denysdovhan/ha-kyiv-vodokanal/releases
[gh-downloads-image]: https://img.shields.io/github/downloads/denysdovhan/ha-kyiv-vodokanal/total?style=flat-square
[hacs-url]: https://github.com/hacs/integration
[hacs-image]: https://img.shields.io/badge/hacs-custom-orange.svg?style=flat-square
[gh-sponsors-url]: https://github.com/sponsors/denysdovhan
[gh-sponsors-image]: https://img.shields.io/github/sponsors/denysdovhan?style=flat-square
[buymeacoffee-url]: https://buymeacoffee.com/denysdovhan
[buymeacoffee-image]: https://img.shields.io/badge/support-buymeacoffee-222222.svg?style=flat-square
[twitter-url]: https://x.com/denysdovhan
[twitter-image]: https://img.shields.io/badge/follow-%40denysdovhan-000000.svg?style=flat-square

<!-- References -->

[home-assistant]: https://www.home-assistant.io/
[denysdovhan]: https://github.com/denysdovhan
[hacs-install-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=denysdovhan&repository=ha-kyiv-vodokanal&category=integration
[hacs-install-image]: https://my.home-assistant.io/badges/hacs_repository.svg
[install-image]: https://my.home-assistant.io/badges/config_flow_start.svg
[install-url]: https://my.home-assistant.io/redirect/config_flow_start/?domain=kyiv_vodokanal
[energy-image]: https://my.home-assistant.io/badges/config_energy.svg
[energy-url]: https://my.home-assistant.io/redirect/config_energy/
[kyivvodokanal]: https://vodokanal.kyiv.ua/
[personal-account]: https://my.vodokanal.kiev.ua/
