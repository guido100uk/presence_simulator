# Home Assistant presence simulator

Evening light schedule plus a manual presence simulator. While **Presence simulator** is on, Home Assistant randomly turns lights in one group on and off from sunset (or a start time you set) until bedtime, then turns that group off.

**Auto away** can turn the master switch on when every `person` is farther than **Away distance** with **Distance unit** **Miles (mi)** or **Kilometers (km)** (default Miles (mi)), or GPS is unknown, and off when someone with GPS is within that distance; switching units converts the number so the GPS radius stays the same; lights stay as they are on return.

This repo is YAML helpers, a loop script, and automations. It is **not** the HACS **Presence Simulation** integration.

Heating oil (Watchman SENSiT gauge, price scrape, order cost) lives in a separate repo: [Kingspan_Heating_Oil_gauge](https://github.com/guido100uk/Kingspan_Heating_Oil_gauge). The older combined tree is archived at [home_assistant](https://github.com/guido100uk/home_assistant).

## Install on an existing Home Assistant

Do **not** replace the live `configuration.yaml`. That file is unique to the house. Copy only the package and dashboard, then merge two small blocks.

1. Create `/config/packages` and `/config/dashboards` if they do not exist.
2. Copy `packages/presence_simulator.yaml` to `/config/packages/`.
3. Copy `presence-simulator.yaml` next to the live `configuration.yaml` (the `/config` folder). Optionally also copy `dashboards/presence_simulator.yaml` into `/config/dashboards/`.
4. Merge into the live `configuration.yaml` (keep everything already there):

```yaml
homeassistant:
  packages: !include_dir_named packages

lovelace:
  dashboards:
    presence-simulator:
      mode: yaml
      filename: presence-simulator.yaml
      title: Presence simulator
      icon: mdi:home-account
      show_in_sidebar: true
```

If `homeassistant:` already exists, add only the `packages: !include_dir_named packages` line under it. If `lovelace:` already exists, add only the `dashboards.presence-simulator` block. Do **not** set `lovelace.mode: yaml` on a house that already uses the UI Overview — that would replace Overview.

5. Developer tools → YAML → **Check configuration**, then restart Home Assistant.

## Deploy a package update to the live house

The running Home Assistant is at `http://your ip address running HA/` (port 80). Copy through the sidebar **Terminal** add-on, not by replacing `configuration.yaml`.

1. Backup: `cp /config/packages/presence_simulator.yaml /config/packages/presence_simulator.yaml.bak`
2. Copy this repo’s `packages/presence_simulator.yaml` to `/config/packages/presence_simulator.yaml`
3. `ha core check`
4. `ha core restart` so the loop script reloads
5. Commit and push the same change to GitHub

**Overview / Home will not show these helpers.** That screen lists lights and other devices by area, not `input_datetime` helpers.

To open start and bedtime after restart:

1. Sidebar item **Presence simulator** (if the extra dashboard was merged in)
2. Press **e** (or tap search) and type **Presence simulator start**
3. **Settings → Devices & services → Helpers** → **Presence simulator start** / **Presence simulator bedtime**

Then create the light group in the UI if it does not already exist:

- Settings → Devices & services → Helpers → Create helper → Group → Light group
- Name: `Presence simulator lights` (entity ID must be `light.presence_simulator_lights`)
- Add the lights you want simulated. Do not add lights you do not want changed.

Open **Presence simulator use sunset** and turn it **on** (recommended). If you prefer a fixed start, leave it off and set **Presence simulator start** (default 18:00). Set **Presence simulator bedtime** (default 23:00, same calendar evening). Set min/max minutes between changes if you want (defaults 5 and 25).

This GitHub repo is private, so `raw.githubusercontent.com` will 404 without auth. Copy files from a clone, not from a raw URL.

## This folder as a standalone config

For a new Home Assistant (or `docker-compose.yml` in this repo), you can use the whole tree as a config root. The sample `configuration.yaml` here also sets `lovelace.mode: yaml` so the demo Overview includes the helpers. Do not copy that global YAML mode onto an existing house.

| File | Purpose |
| --- | --- |
| `configuration.yaml` | Sample root: packages, default includes, sidebar dashboard |
| `presence-simulator.yaml` | Sidebar item **Presence simulator** |
| `dashboards/presence_simulator.yaml` | Same dashboard, extra copy |
| `ui-lovelace.yaml` | Demo Overview when Lovelace is in YAML mode |
| `packages/presence_simulator.yaml` | Helpers, script, automations |
| `automations.yaml` | UI automations include (skip if you already have this file) |
| `scripts.yaml` | UI scripts include (skip if you already have this file) |
| `scenes.yaml` | UI scenes include (skip if you already have this file) |
| `groups.yaml` | Groups include |
| `customize.yaml` | Entity customize include |
| `secrets.yaml` | Secrets include (empty sample) |
| `docker-compose.yml` | Optional: run this folder as Home Assistant |

## Helpers

| Entity | Default | Purpose |
| --- | --- | --- |
| `input_boolean.presence_simulator` | off | Master switch |
| `input_boolean.presence_simulator_use_sunset` | off until you enable it | Start at sunset when on |
| `input_datetime.presence_simulator_start` | 18:00 after you set it | Fixed start when sunset is off |
| `input_datetime.presence_simulator_bedtime` | 23:00 after you set it | All grouped lights off |
| `input_number.presence_simulator_min_minutes` | 5 | Minimum wait |
| `input_number.presence_simulator_max_minutes` | 25 | Maximum wait |
| `input_boolean.presence_simulator_auto_away` | off | Turn master on/off from GPS distance |
| `input_number.presence_simulator_away_miles` | 1 | Away distance (unit from Distance unit) |
| `input_select.presence_simulator_distance_unit` | Miles (mi) | Miles (mi) or Kilometers (km); converts Away distance |
| `input_select.presence_simulator_ask_if_off_while_away` | Both | Ask if off while away — Phone / Home Assistant / Both |
| `light.presence_simulator_lights` | created in Helpers | Only lights this package changes |

People need the **Companion** app (or another GPS tracker linked to a `person` entity) for Auto away to see distance. Do not hard-code person names in the package.

`input_datetime` helpers do not keep a YAML default after first create — set 18:00 and 23:00 once in the UI if they are empty. Bedtime must be later the same local day than the start (no overnight windows).

## 5-minute smoke test

1. Put at least one real light in **Presence simulator lights**.
2. Set start a minute or two in the past (or wait until after sunset if Use sunset is on) and bedtime later tonight.
3. Turn **Presence simulator** **on**. A grouped light should change within the min/max window (for a quick test, set min and max to 1).
4. Switch off **Presence simulator**. Every light in the group should turn off.
5. Lights that are not in the group must stay as you left them.

If the group is empty, nothing is toggled. If a member is unavailable, it is skipped.

### Auto away smoke notes

- **Auto away off** → GPS distance does not change the master switch.
- **Auto away on**, leave beyond 1 mile (or ~1.6 km if Distance unit is Kilometers (km)) → master switch turns on after GPS updates (the loop still waits for the evening window).
- Return within that Away distance → master switch off; grouped lights stay as they are.
- Manual off while away → question on Phone / Home Assistant / Both; **Correct** stays off until someone comes home; **Mistake** turns the switch back on.
