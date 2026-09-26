# Handover

## Changelog

### 2026-09-26 19:44 — README screenshot and coffee button
- Added the live Presence simulator dashboard image at the top of `README.md` (`presence-simulator.png`).
- Added a Buy Me a Coffee button at the bottom using the GitHub-safe yellow image (the button-api query URL does not render on GitHub).

### 2026-09-13 18:58 — Placeholder HA address
- Docs and deploy notes use `your ip address running HA` instead of a house-specific IP. Did not change the running Home Assistant instance.

### 2026-09-13 15:10 — Split out of home_assistant
- This repo is Presence simulator only (package, sidebar dashboard, Auto away docs and tests).
- Heating oil is now [Kingspan_Heating_Oil_gauge](https://github.com/guido100uk/Kingspan_Heating_Oil_gauge). Combined history stays in [home_assistant](https://github.com/guido100uk/home_assistant).
- Live house is unchanged: still copy `packages/presence_simulator.yaml` through the HA Terminal.

### Earlier work
- See the archive repo `home_assistant` changelog for Auto away, Distance unit, and live deploys before this split.
