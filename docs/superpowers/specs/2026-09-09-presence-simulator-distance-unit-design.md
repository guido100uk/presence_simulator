# Presence simulator distance unit — design

Date: 2026-09-09  
Status: approved

This amends the 2026-09-08 auto away design. Auto away still uses one typed **Away distance** and Home Assistant `distance()` (kilometres). The menu gains a unit dropdown so that number can be entered and shown as miles or kilometres.

## Goal

On the **Presence simulator** menu, next to **Away distance**, the user can choose **Distance unit**: **Miles (mi)** or **Kilometers (km)**.

Switching the dropdown **converts** the Away distance number so the real GPS radius stays the same (1 mi becomes about 1.6 km). Auto away compare logic uses kilometres: multiply by `1.609344` when the unit is miles; use the number as-is when the unit is kilometres.

## Non-goals

- Changing Auto away on/off, ask-if-off, or Correct/Mistake behaviour.
- Per-person units or a second distance field.
- Custom Lovelace cards. Stay on the existing entities card.
- Renaming `input_number.presence_simulator_away_miles` (keeps the live house value).

## Helpers (UI)

Shown on the Presence simulator dashboard (and the extra copies of that view), in this order, after **Auto away**:

| Entity | Type | Default | Menu name |
| --- | --- | --- | --- |
| `input_number.presence_simulator_away_miles` | number | `1` (unchanged entity id) | Away distance |
| `input_select.presence_simulator_distance_unit` | dropdown | `Miles (mi)` | Distance unit |

`Away distance`: min `0.1`, max `200`, step `0.1`, mode `box`. **No** `unit_of_measurement` (the dropdown is the unit). Max is `200` so 100 miles can convert to ~161 km without clipping.

Dropdown options, exact strings: `Miles (mi)`, `Kilometers (km)`.

Holdoff, quiet off, and confirm pending stay off the menu.

## Convert on unit change

New automation `presence_simulator_distance_unit_convert`:

- Trigger: state of `input_select.presence_simulator_distance_unit`.
- Skip when `trigger.from_state` is none (Home Assistant restart must not convert).
- Skip when from and to are the same option.
- `Miles (mi)` → `Kilometers (km)`: `value * 1.609344`.
- `Kilometers (km)` → `Miles (mi)`: `value / 1.609344`.
- Round to 1 decimal (the helper step). Clamp to `0.1`–`200`.
- `input_number.set_value` on `input_number.presence_simulator_away_miles`.

## GPS compare

Home Assistant `distance('zone.home', person_id)` is kilometres. In the three existing Auto away templates (evaluate someone-home, evaluate house-empty, manual-off-while-away), replace `miles * 1.609344` with:

- Read `dist` from `input_number.presence_simulator_away_miles`.
- Read `unit` from `input_select.presence_simulator_distance_unit`.
- `km = dist * 1.609344` when unit is `Miles (mi)`; `km = dist` when unit is `Kilometers (km)`.

Add `input_select.presence_simulator_distance_unit` to the evaluate automation’s state trigger list so a convert that rounds to the same number still re-evaluates. Evaluate stays `mode: restart` so a unit change that then writes a new number re-runs with the converted value.

## Edges

| Case | Behaviour |
| --- | --- |
| Default | Miles (mi), Away distance 1 (same 1 mile radius as today). |
| HA restart | Do not convert. Keep stored number and selected unit. |
| Convert would exceed 200 | Clamp to 200. |
| Convert would go below 0.1 | Clamp to 0.1. |
| Round-trip 1.0 mi | 1.0 → 1.6 km → 1.0 mi. |

## Files

- `packages/presence_simulator.yaml` — helper, convert automation, GPS templates, evaluate trigger.
- `presence-simulator.yaml`, `dashboards/presence_simulator.yaml`, `ui-lovelace.yaml` — Away distance label and Distance unit row.
- `README.md` — Away distance + unit dropdown; Auto away smoke notes in both units.
- `tests/test_presence_simulator_package.py` — helper options, convert automation, km branch, dashboard rows, README.
- `docs/superpowers/specs/2026-09-08-presence-simulator-auto-away-design.md` — pointer to this spec.

Live deploy: backup `/config/packages/presence_simulator.yaml`, copy the package through sidebar Terminal, `ha core check`, `ha core restart`, copy `presence-simulator.yaml` the same way, then commit and push GitHub.

## Testing

Contract tests only (parse YAML). Assert Distance unit options and default, Away distance name/max/no unit suffix, convert automation id and `1.609344` plus both option strings, evaluate trigger includes the select, dashboards list Distance unit and not “(miles)”, README mentions the dropdown.

Live check: menu shows Away distance and Distance unit (Miles (mi)). Switch to Kilometers (km) → number becomes ~1.6. Switch back → ~1.0. Auto away still uses that radius.

## Decisions

- One number plus a dropdown (same pattern as Ask if off while away).
- Convert the number so the physical radius does not jump.
- Keep entity id `presence_simulator_away_miles` even when the value is kilometres.
- Option labels include both word and abbreviation: `Miles (mi)`, `Kilometers (km)`.
