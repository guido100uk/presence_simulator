# Handover

## Changelog

### 2026-11-06 18:40 — Lights work normally when home
- Loop no longer starts or continues when anyone is within Away distance of home.
- Sunset still turns the group on while you are home.

### 2026-10-31 17:40 — Sunset turns evening lights on while home
- Use sunset turns the group on at sunset / HA start after sunset, even when home and the master switch is off.
- Random loop still needs **Presence simulator** on.

### 2026-10-31 16:12 — Deploy sunset fix and push
- Pushed the sunset-loop + helpers-link commit after rebasing onto remote README updates (`b3d4bca`).
- Live HA: package patched, dashboard copied, `ha core check` passed, restart submitted.

### 2026-10-31 16:00 — Sunset loop race and helpers shortcut
- Evening window no longer uses `below_horizon` (that raced the sunset trigger and aborted the loop).
- Keep-alive restarts an idle loop every 5 minutes in the evening window.
- Setup page: **Add or remove lights** → `/config/helpers`.

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
