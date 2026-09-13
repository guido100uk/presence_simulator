# Presence simulator auto away — design

Date: 2026-09-08  
Status: approved

This amends the 2026-09-06 presence simulator design. Activation is no longer manual-only: an optional **Auto away** path may turn the existing master switch on and off from GPS distance. The evening window, sunset/start, bedtime, light group, and loop script stay as they are.

## Goal

On the **Presence simulator** menu, the user can:

1. Turn **Auto away** on or off (same kind of toggle as **Presence simulator** and **Use sunset**).
2. Set **Away distance** (typed number, default 1). **Amended 2026-09-09:** unit is **Miles (mi)** or **Kilometers (km)** from a menu dropdown. See `docs/superpowers/specs/2026-09-09-presence-simulator-distance-unit-design.md`.
3. Choose **Ask if off while away**: **Phone**, **Home Assistant**, or **Both** (default **Both**).

When Auto away is on and every tracked person is farther than **Away distance** from Home (or has unknown GPS), turn **Presence simulator** on. When anyone with a known location is within that distance, turn **Presence simulator** off and **leave lights as they are**.

## Non-goals

- Changing bedtime (still stops the loop and turns the grouped lights off).
- Hard-coded `person.*`, `device_tracker.*`, or `notify.mobile_app_*` entity IDs.
- Installing the Proximity integration or extra zones.
- Per-person distance settings or weekday calendars.

## Helpers (UI)

Shown on the Presence simulator dashboard (and the extra copies of that view):

| Entity | Type | Default | Menu name |
| --- | --- | --- | --- |
| `input_boolean.presence_simulator_auto_away` | toggle | off | Auto away |
| `input_number.presence_simulator_away_miles` | number | `1` | Away distance (unit from Distance unit dropdown; see 2026-09-09 spec) |
| `input_select.presence_simulator_ask_if_off_while_away` | dropdown | `Both` | Ask if off while away |

`Away distance`: min `0.1`, max `200`, step `0.1`. Unit is the Distance unit dropdown (`Miles (mi)` / `Kilometers (km)`), not a fixed `mi` suffix. See the 2026-09-09 spec.

Dropdown options, exact strings: `Phone`, `Home Assistant`, `Both`.

Also defined by the package (used by the question, not extra schedule settings):

| Entity | Type | Role |
| --- | --- | --- |
| `input_boolean.presence_simulator_auto_holdoff` | toggle | Set when the user confirms a manual off while away was **correct**. Blocks auto-on until someone is home (within distance, known GPS), then clears. |
| `input_boolean.presence_simulator_quiet_off` | toggle | Internal. Auto-off on return home sets this so stop-on-switch does **not** turn grouped lights off. |
| `input_boolean.presence_simulator_confirm_off_pending` | toggle | A correct/mistake question is waiting. |
| `input_button.presence_simulator_off_correct` | button | Menu: off while away was **correct**. |
| `input_button.presence_simulator_off_mistake` | button | Menu: off while away was a **mistake**. |

The two buttons appear on the Presence simulator menu. They do nothing unless a question is pending. Do **not** put holdoff, quiet off, or confirm pending on the menu as toggles.

## Who is “everyone”

All `person.*` entities. None are hard-coded.

- **Known location:** the person has both `latitude` and `longitude` attributes (not none).
- **Unknown GPS:** missing latitude or longitude → count as **away**.
- **Distance:** Home Assistant `distance('zone.home', person_id)` (kilometres) compared to Away distance in km (`× 1.609344` when Distance unit is miles; as-is when kilometres). See the 2026-09-09 spec.
- **House empty:** `zone.home` exists, there is at least one `person.*`, and every person is unknown or farther than Away distance.
- **Someone home:** at least one person has known GPS within Away distance.

**Auto-on** (turn `input_boolean.presence_simulator` on) only when all of these are true: Auto away is on, house empty, holdoff is off, confirm pending is off.

**Auto-off of the master switch** only when Auto away is on, someone is home, and the master switch is on.

If there are no `person.*` entities, or `zone.home` is missing, Auto away does not change the master switch.

People need the Companion app (or another GPS `device_tracker` linked to a person).

## Runtime behaviour

The loop still runs only when **Presence simulator** is on **and** local time is inside the evening window. Auto away only flips that switch.

### Auto on

When auto-on conditions become true: `input_boolean.turn_on` on `input_boolean.presence_simulator`. Existing start-on-switch / window automations start the loop if it is evening.

### Someone home

Whenever someone is home (known GPS within Away distance), even if Auto away is off or the master switch is already off:

1. Clear **holdoff**.
2. Clear **confirm pending** and dismiss the persistent notification (`notification_id`: `presence_simulator_off_while_away`).

If Auto away is on **and** the master switch is on, also:

1. Set **quiet off**.
2. Turn **Presence simulator** off (stops the loop).
3. Do **not** `light.turn_off` the group.

### Bedtime

Unchanged: stop the loop and turn grouped lights off, even if Auto away is on.

### Manual off of Presence simulator

`presence_simulator_stop_on_switch` still runs.

- If **quiet off** is set: stop the loop, skip `light.turn_off`, clear quiet off.
- Otherwise: stop the loop and `light.turn_off` the group (today’s behaviour).

If Auto away is on, quiet off is not set, and the house is still empty: this is “off while away”. Set **confirm pending** on the same off event (before any re-evaluate can auto-on) and ask correct vs mistake using **Ask if off while away**.

Until the user answers, Auto away must **not** turn the master switch back on (confirm pending blocks auto-on).

### Correct vs mistake

Question text: they turned Presence simulator off while still farther than Away distance (or unknown GPS). Was that **correct** or a **mistake**?

- **Correct:** leave the switch off. Set **holdoff**. Clear pending. Auto away will not turn the switch on until someone is home (within distance, known GPS), which clears holdoff; the next time the house is empty, auto-on may run.
- **Mistake:** turn **Presence simulator** on. Clear pending. Do not set holdoff.

### Where the question is sent

Read `input_select.presence_simulator_ask_if_off_while_away`:

| Choice | Phone (actionable `notify.notify`) | Home Assistant bell (`persistent_notification`) and menu Yes/No |
| --- | --- | --- |
| Phone | yes | no (buttons still on the menu so they can answer there) |
| Home Assistant | no | yes |
| Both | yes | yes |

Phone actions use a fixed action id (`PRESENCE_SIMULATOR_OFF_CORRECT` / `PRESENCE_SIMULATOR_OFF_MISTAKE`) so any Companion app that receives `notify.notify` can answer. Do not hard-code a `notify.mobile_app_*` entity.

Menu buttons always exist; they only apply when confirm pending is on.

## Automations (new)

Stable ids:

- `presence_simulator_auto_away_evaluate` — person state / GPS / Auto away / miles / Home Assistant start: evaluate house empty vs someone home and turn the master switch on or off as above.
- `presence_simulator_manual_off_while_away` — master switch to `off`, not quiet off, Auto away on, house still empty: start the correct/mistake question.
- `presence_simulator_confirm_off_correct` — button or mobile action Correct.
- `presence_simulator_confirm_off_mistake` — button or mobile action Mistake.

Change `presence_simulator_stop_on_switch` so grouped lights turn off only when quiet off is **not** set.

## Error handling

| Case | Behaviour |
| --- | --- |
| Auto away off | Do not turn the master switch on or off. Still clear holdoff and pending when someone is home. |
| No persons or no `zone.home` | Do not auto-on or auto-off. |
| GPS unknown | Count as away. |
| Miles below min | Helper min `0.1`. |
| Notify target missing | Persistent notification and menu buttons still work; phone notify may no-op. |
| User ignores the question | Hold auto-on until they answer or someone comes home (home clears pending). |

## Files

- `packages/presence_simulator.yaml` — helpers and automations.
- `presence-simulator.yaml`, `dashboards/presence_simulator.yaml`, `ui-lovelace.yaml` — new menu rows and the two buttons.
- `README.md` — Auto away, miles, dropdown, Companion GPS, smoke note.
- `tests/test_presence_simulator_package.py` — new entity ids, automation ids, dashboard names, stop-on-switch quiet-off, no hard-coded person ids.

Live deploy: backup `/config/packages/presence_simulator.yaml`, copy the package through sidebar Terminal, `ha core check`, `ha core restart`, then commit and push GitHub. Copy the dashboard YAML the same way if the menu should update.

## Testing

Contract tests only (parse YAML). Assert the new helpers, select options, automation ids, `quiet_off` / holdoff / pending, `distance` + `zone.home` + `person`, miles-to-km, and that `notify.mobile_app_` and `person.` household ids are not hard-coded. README mentions Auto away and Away distance.

Live check: Auto away off → no change. Auto away on, leave beyond 1 mile → master switch on after GPS updates. Return within 1 mile → switch off, lights stay. Manual off while away → question on the chosen channel(s); Correct vs Mistake behave as above.

## Decisions

- Measure with `distance()` vs `zone.home` and all `person.*` entities.
- Unknown GPS counts as away.
- Return home: switch off, lights stay on.
- Manual off while away: ask correct vs mistake; destinations from a dropdown (default Both).
- No extra Proximity integration or large zone.
