# Presence simulator light schedule — design

Date: 2026-09-06  
Status: approved

## Goal

Ship a reusable Home Assistant **package** that:

1. Provides an evening **light schedule window** (start time or sunset → bedtime).
2. While a manual **Presence simulator** switch is on, randomly turns grouped lights on and off to look like someone is home.
3. Turns every grouped light **off** at bedtime or when the switch is turned off.

The package must not hard-code household light entity IDs. The user picks lights by adding them to a light group in the Home Assistant UI.

## Non-goals

- Automatic away detection (person/zone/alarm). Activation is manual only. **Amended 2026-09-08:** optional Auto away may flip the master switch from GPS distance. See `docs/superpowers/specs/2026-09-08-presence-simulator-auto-away-design.md`. The loop still only runs when the master switch is on and it is inside the evening window.
- Per-light independent schedules or weekday/weekend calendars.
- Brightness, colour, or scene playback.
- Controlling lights that are not members of the simulator group.

## Architecture

One YAML package, installed by enabling Home Assistant packages and copying this repo’s package file into `config/packages/`.

```
input helpers + light group
        ↓
start / stop automations
        ↓
loop script (pick random member → on/off → wait → repeat)
```

The package is the only runtime unit. A short README explains the `packages:` include, how to add lights, and a 5-minute smoke test.

## Helpers (UI)

| Helper | Type | Default | Role |
| --- | --- | --- | --- |
| `input_boolean.presence_simulator` | toggle | off | Master switch. Nothing runs unless this is on. |
| `input_boolean.presence_simulator_use_sunset` | toggle | on | If on, evening window starts at sunset. If off, uses start time. |
| `input_datetime.presence_simulator_start` | time | `18:00` | Fixed start when sunset is not used. |
| `input_datetime.presence_simulator_bedtime` | time | `23:00` | End of window. All grouped lights off; loop stops. |
| `input_number.presence_simulator_min_minutes` | number | `5` | Minimum wait after each toggle. |
| `input_number.presence_simulator_max_minutes` | number | `25` | Maximum wait after each toggle. |
| `light.presence_simulator_lights` | light group | no members | Only lights the package may change. User adds members in Settings → Devices & Services → Helpers. |

Entity IDs are stable so dashboards and automations can reference them.

## Runtime behaviour

### When the loop may run

All of the following must be true:

- `input_boolean.presence_simulator` is `on`.
- Current local time is inside the evening window: at or after start, and before bedtime.
- The light group has at least one usable member (`on` or `off`).

Start of window:

- If **Use sunset** is on: `sun.sun` sunset (Home Assistant `sun` integration).
- If **Use sunset** is off: `input_datetime.presence_simulator_start`.

End of window: `input_datetime.presence_simulator_bedtime`.

The window is **same local calendar day**. Bedtime must be after the effective start (sunset or start time). Overnight windows (for example start 18:00, bedtime 01:00) are out of scope; if bedtime is not after start, the loop does not run that day. The Sun integration (`sun.sun`) is required when **Use sunset** is on (it is enabled by default in Home Assistant).

### Event flow

1. User adds lights to **Presence simulator lights**.
2. User turns **Presence simulator** on (any time of day).
3. If before the start, idle until start; then the loop script starts.
4. If the switch is turned on during the window, the loop starts immediately.
5. Each cycle: pick one random usable group member → randomly turn it `on` or `off` → wait a random duration between min and max minutes → repeat while conditions still hold.
6. At bedtime, or when the switch turns off: stop the script and turn **off** every light in the group.
7. After bedtime, turning the switch on does nothing until the next evening’s start.

Lights not in the group are never changed.

### Restart

On Home Assistant start / package reload:

- If the switch is on **and** the current time is inside the window, start the loop.
- If after bedtime, do not start; do not turn lights on.

## Automations and script

- **Start at window** — fires at sunset or at the configured start time (whichever is selected). If the switch is on, start the loop.
- **Start on switch** — when the master switch turns on, start the loop only if currently inside the window.
- **Resume after restart** — on Home Assistant start, same gate as “start on switch”.
- **Stop at bedtime** — at bedtime, stop the loop and `light.turn_off` the group.
- **Stop on switch off** — when the master switch turns off, stop the loop and `light.turn_off` the group.
- **Loop script** — `while` the switch is on and time is inside the window: select a random usable member, set a random `on`/`off`, then `delay` a random interval.

The script must be abortable (`script.turn_off`) so bedtime and switch-off stop it immediately.

## Error handling

| Case | Behaviour |
| --- | --- |
| Empty group | Script no-ops. No errors, no other lights touched. |
| Single member | Allowed. That light still toggles at random intervals. |
| Min ≥ max | Effective max is `min + 1` minute so the wait range is always valid. |
| Unavailable / unknown members | Skip those entities. If none are usable, skip the cycle (wait, then try again). |
| Manual use of a grouped light | Next cycle may still change that light. Remove it from the group to exclude it. |
| Switch on after bedtime | Idle until the next start. |

## Files to add (implementation)

- `configuration.yaml` — enable `homeassistant.packages` if this repo is used as a full config root; otherwise README shows the one-line include.
- `packages/presence_simulator.yaml` — helpers, group, script, automations.
- `README.md` — install, add lights, defaults, smoke test.
- Tests as agreed below (parse + contract), not a live Home Assistant instance.

## Testing / verification

There is no application compile step. Verification is:

1. **YAML validity** — parse `packages/presence_simulator.yaml` (and `configuration.yaml` if present) so the files are well-formed.
2. **Entity contract** — the package defines the switch, sunset toggle, start/bedtime datetimes, min/max numbers, light group, loop script, and start/stop automations with the IDs in this spec.
3. **Template sanity** — empty group, min ≥ max, and skip-unavailable are implemented in the script, not comments only.
4. **Install notes** — README covers packages include, adding lights, and a 5-minute test: switch on inside the window → a grouped light changes → switch off → all grouped lights off.

Live bulb checks happen on the user’s Home Assistant instance after copy/install.

## Decisions already made

- Activation: **manual switch only** (not away detection).
- Light selection: **user-configurable light group**.
- Schedule: **evening window only** (start or sunset → bedtime, then all off).
- Delivery: **Home Assistant package** (not a blueprint, not UI-only click paths).
