# Presence Simulator Distance Unit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Presence simulator menu dropdown **Miles (mi)** / **Kilometers (km)** that converts Away distance so the GPS radius stays the same, and compare Auto away in kilometres.

**Architecture:** Keep one YAML package. Add `input_select.presence_simulator_distance_unit` and automation `presence_simulator_distance_unit_convert`. Keep entity id `input_number.presence_simulator_away_miles` (it may hold miles or kilometres). The three Auto away templates convert to km only when the dropdown is `Miles (mi)`. Dashboards get the new row; holdoff / quiet off / confirm pending stay off the menu.

**Tech Stack:** Home Assistant YAML packages, Jinja (`distance()`, `round`, `trigger.from_state`), Python 3 + pytest + PyYAML.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-09-presence-simulator-distance-unit-design.md`
- Dropdown options, exact strings: `Miles (mi)`, `Kilometers (km)`. Default: `Miles (mi)`.
- Keep entity id `input_number.presence_simulator_away_miles`. Menu name: `Away distance`. Min `0.1`, max `200`, step `0.1`, no `unit_of_measurement`.
- Convert factor `1.609344`. Round to 1 decimal. Clamp `0.1`–`200`.
- Skip convert when `trigger.from_state` is none (Home Assistant restart).
- `distance('zone.home', person_id)` is km: `dist * 1.609344` if unit is `Miles (mi)`, else `dist`.
- Do **not** hard-code `person.*`, `device_tracker.*`, or `notify.mobile_app_*` entity IDs.
- Do not change the loop member-expand fix. Do not replace live `configuration.yaml`. Do not read `hassTokens`.
- Tests: `py -3 -m pytest tests/test_presence_simulator_package.py -v` (Windows; not `python`).
- Live HA: `http://your ip address running HA/` port 80. Deploy via sidebar Terminal only.

---

## File structure

| File | Responsibility |
| --- | --- |
| `tests/test_presence_simulator_package.py` | Contract tests for unit helper, convert automation, GPS km branch, dashboards, README |
| `packages/presence_simulator.yaml` | Distance unit select, convert automation, GPS templates, evaluate trigger |
| `presence-simulator.yaml` | Live sidebar menu rows |
| `dashboards/presence_simulator.yaml` | Extra copy of the same menu |
| `ui-lovelace.yaml` | Demo Overview copy of the same menu |
| `README.md` | Away distance + Distance unit; smoke notes |
| `handover.md` | Changelog for each commit |

## Shared Jinja (paste verbatim)

**Away distance in km** (`away_km`) — first two lines of every GPS distance template:

```jinja
{% set dist = states('input_number.presence_simulator_away_miles') | float(1) %}
{% set km = dist * 1.609344 if states('input_select.presence_simulator_distance_unit') == 'Miles (mi)' else dist %}
```

**Someone home** (evaluate first branch):

```jinja
{% set dist = states('input_number.presence_simulator_away_miles') | float(1) %}
{% set km = dist * 1.609344 if states('input_select.presence_simulator_distance_unit') == 'Miles (mi)' else dist %}
{% set ns = namespace(home=false) %}
{% if states.zone.home is not none %}
  {% for p in states.person %}
    {% set lat = state_attr(p.entity_id, 'latitude') %}
    {% set lon = state_attr(p.entity_id, 'longitude') %}
    {% if lat is not none and lon is not none and distance('zone.home', p.entity_id) <= km %}
      {% set ns.home = true %}
    {% endif %}
  {% endfor %}
{% endif %}
{{ ns.home }}
```

**House empty** (evaluate second branch and manual-off-while-away):

```jinja
{% set dist = states('input_number.presence_simulator_away_miles') | float(1) %}
{% set km = dist * 1.609344 if states('input_select.presence_simulator_distance_unit') == 'Miles (mi)' else dist %}
{% set people = states.person %}
{% if states.zone.home is none or people | count == 0 %}
  false
{% else %}
  {% set ns = namespace(all_away=true) %}
  {% for p in people %}
    {% set lat = state_attr(p.entity_id, 'latitude') %}
    {% set lon = state_attr(p.entity_id, 'longitude') %}
    {% if lat is not none and lon is not none and distance('zone.home', p.entity_id) <= km %}
      {% set ns.all_away = false %}
    {% endif %}
  {% endfor %}
  {{ ns.all_away }}
{% endif %}
```

**Convert value** (set_value data.value):

```jinja
{% set dist = states('input_number.presence_simulator_away_miles') | float(1) %}
{% set raw = dist * 1.609344 if trigger.to_state.state == 'Kilometers (km)' else dist / 1.609344 %}
{{ [[raw | round(1), 0.1] | max, 200] | min }}
```

---

### Task 1: Distance unit helper and Away distance range

**Files:**
- Modify: `tests/test_presence_simulator_package.py` (`test_package_defines_auto_away_helpers`)
- Modify: `packages/presence_simulator.yaml` (`input_number.presence_simulator_away_miles`, `input_select`)
- Modify: `handover.md`

**Interfaces:**
- Consumes: existing `input_number.presence_simulator_away_miles` entity id.
- Produces: `input_select.presence_simulator_distance_unit` with options `["Miles (mi)", "Kilometers (km)"]`, initial `Miles (mi)`; Away distance name `Away distance`, max `200`, no `unit_of_measurement`.

- [ ] **Step 1: Write the failing test**

In `test_package_defines_auto_away_helpers`, replace the miles assertions and add the select:

```python
    miles = package["input_number"]["presence_simulator_away_miles"]
    assert miles["name"] == "Away distance"
    assert miles["min"] == 0.1
    assert miles["max"] == 200
    assert miles["step"] == 0.1
    assert miles["initial"] == 1
    assert "unit_of_measurement" not in miles
    unit = package["input_select"]["presence_simulator_distance_unit"]
    assert unit["name"] == "Distance unit"
    assert unit["options"] == ["Miles (mi)", "Kilometers (km)"]
    assert unit["initial"] == "Miles (mi)"
```

Leave the ask-if-off and button assertions as they are.

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_presence_simulator_package.py::test_package_defines_auto_away_helpers -v`

Expected: FAIL (`name` still `Away distance (miles)`, max still `100`, `unit_of_measurement` still `mi`, and/or missing `presence_simulator_distance_unit`).

- [ ] **Step 3: Write minimal implementation**

In `packages/presence_simulator.yaml`, change the number helper to:

```yaml
  presence_simulator_away_miles:
    name: Away distance
    min: 0.1
    max: 200
    step: 0.1
    mode: box
    initial: 1
    icon: mdi:map-marker-distance
```

Add this select **above** `presence_simulator_ask_if_off_while_away`:

```yaml
  presence_simulator_distance_unit:
    name: Distance unit
    options:
      - Miles (mi)
      - Kilometers (km)
    initial: Miles (mi)
    icon: mdi:ruler
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 -m pytest tests/test_presence_simulator_package.py::test_package_defines_auto_away_helpers -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py packages/presence_simulator.yaml handover.md
git commit -m "Add Distance unit helper and raise Away distance max to 200."
```

Prepend `handover.md`:

```markdown
### 2026-09-09 HH:MM — Distance unit helper
- Added `input_select.presence_simulator_distance_unit` (Miles (mi) / Kilometers (km), default Miles (mi)).
- Renamed Away distance (dropped miles suffix and `mi` unit); max 200 so a 100 mi convert fits.
```

---

### Task 2: Convert Away distance when the unit changes

**Files:**
- Modify: `tests/test_presence_simulator_package.py` (`AUTO_AWAY_AUTOMATION_IDS`, new `test_distance_unit_convert`)
- Modify: `packages/presence_simulator.yaml` (new automation after `presence_simulator_confirm_off_mistake`)
- Modify: `handover.md`

**Interfaces:**
- Consumes: `input_select.presence_simulator_distance_unit`, `input_number.presence_simulator_away_miles`.
- Produces: automation id `presence_simulator_distance_unit_convert`; `input_number.set_value` using factor `1.609344`; skip when `from_state` is none.

- [ ] **Step 1: Write the failing test**

Add `"presence_simulator_distance_unit_convert"` to `AUTO_AWAY_AUTOMATION_IDS`.

Add:

```python
def test_distance_unit_convert(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_distance_unit_convert"])
    assert "input_select.presence_simulator_distance_unit" in blob
    assert "input_number.presence_simulator_away_miles" in blob
    assert "input_number.set_value" in blob
    assert "1.609344" in blob
    assert "Miles (mi)" in blob
    assert "Kilometers (km)" in blob
    assert "from_state" in blob
    assert "round(1)" in blob
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_presence_simulator_package.py::test_required_automations_exist tests/test_presence_simulator_package.py::test_distance_unit_convert -v`

Expected: FAIL (missing automation id).

- [ ] **Step 3: Write minimal implementation**

Append this automation to the `automation:` list in `packages/presence_simulator.yaml`:

```yaml
  - id: presence_simulator_distance_unit_convert
    alias: Presence simulator distance unit convert
    mode: single
    trigger:
      - trigger: state
        entity_id: input_select.presence_simulator_distance_unit
    condition:
      - condition: template
        value_template: >
          {{ trigger.from_state is not none
             and trigger.from_state.state != trigger.to_state.state
             and trigger.from_state.state not in ['unknown', 'unavailable'] }}
    action:
      - action: input_number.set_value
        target:
          entity_id: input_number.presence_simulator_away_miles
        data:
          value: >
            {% set dist = states('input_number.presence_simulator_away_miles') | float(1) %}
            {% set raw = dist * 1.609344 if trigger.to_state.state == 'Kilometers (km)' else dist / 1.609344 %}
            {{ [[raw | round(1), 0.1] | max, 200] | min }}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 -m pytest tests/test_presence_simulator_package.py::test_required_automations_exist tests/test_presence_simulator_package.py::test_distance_unit_convert tests/test_presence_simulator_package.py::test_package_defines_auto_away_helpers -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py packages/presence_simulator.yaml handover.md
git commit -m "Convert Away distance when Distance unit changes."
```

---

### Task 3: GPS templates honour miles vs kilometres

**Files:**
- Modify: `tests/test_presence_simulator_package.py` (`test_auto_away_evaluate_uses_distance_and_all_persons`, `test_manual_off_while_away_asks_correct_or_mistake`)
- Modify: `packages/presence_simulator.yaml` (three `away_km` templates; evaluate state trigger)
- Modify: `handover.md`

**Interfaces:**
- Consumes: `away_km` Jinja from Shared Jinja; `input_select.presence_simulator_distance_unit`.
- Produces: evaluate state trigger includes `input_select.presence_simulator_distance_unit`; all three GPS templates use `Miles (mi)` instead of always `miles * 1.609344`.

- [ ] **Step 1: Write the failing test**

In `test_auto_away_evaluate_uses_distance_and_all_persons`, add:

```python
    assert "presence_simulator_distance_unit" in blob
    assert "Miles (mi)" in blob
```

In `test_manual_off_while_away_asks_correct_or_mistake`, add:

```python
    assert "presence_simulator_distance_unit" in blob
    assert "Miles (mi)" in blob
```

Keep the existing `1.609344` asserts.

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_presence_simulator_package.py::test_auto_away_evaluate_uses_distance_and_all_persons tests/test_presence_simulator_package.py::test_manual_off_while_away_asks_correct_or_mistake -v`

Expected: FAIL (`presence_simulator_distance_unit` / `Miles (mi)` missing from those automations).

- [ ] **Step 3: Write minimal implementation**

In `presence_simulator_auto_away_evaluate` state trigger `entity_id` list, add:

```yaml
          - input_select.presence_simulator_distance_unit
```

Replace the two evaluate distance templates and the manual-off-while-away distance template with the Shared Jinja **Someone home** and **House empty** blocks (someone-home for the first evaluate branch; house-empty for the second evaluate branch and for manual-off-while-away). Do not change any actions.

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 -m pytest tests/test_presence_simulator_package.py -v`

Expected: PASS except dashboard/README tests that still look for `Away distance (miles)` (those fail only after Task 4 updates them; if they still pass here, continue). If the full file still PASSes, that is OK — dashboard tests have not been tightened yet.

Also run: `py -3 -m pytest tests/test_presence_simulator_package.py::test_auto_away_evaluate_uses_distance_and_all_persons tests/test_presence_simulator_package.py::test_manual_off_while_away_asks_correct_or_mistake -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py packages/presence_simulator.yaml handover.md
git commit -m "Compare Auto away in km using the Distance unit dropdown."
```

---

### Task 4: Menu and README

**Files:**
- Modify: `tests/test_presence_simulator_package.py` (`test_dashboard_shows_auto_away_controls_not_internals`, `test_readme_covers_auto_away`)
- Modify: `presence-simulator.yaml`
- Modify: `dashboards/presence_simulator.yaml`
- Modify: `ui-lovelace.yaml`
- Modify: `README.md`
- Modify: `handover.md`

**Interfaces:**
- Consumes: helper entity ids from Task 1.
- Produces: all three dashboards list Away distance then Distance unit (not `(miles)`); README documents the dropdown and conversion.

- [ ] **Step 1: Write the failing test**

In `test_dashboard_shows_auto_away_controls_not_internals`, replace the Away distance asserts with:

```python
        assert "input_number.presence_simulator_away_miles" in blob
        assert "Away distance" in blob
        assert "Away distance (miles)" not in blob
        assert "input_select.presence_simulator_distance_unit" in blob
        assert "Distance unit" in blob
```

In `test_readme_covers_auto_away`, add:

```python
    assert "distance unit" in text
    assert "kilometers (km)" in text or "kilometres (km)" in text
    assert "miles (mi)" in text
```

Keep `assert "miles" in text`.

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_presence_simulator_package.py::test_dashboard_shows_auto_away_controls_not_internals tests/test_presence_simulator_package.py::test_readme_covers_auto_away -v`

Expected: FAIL (dashboards still say `Away distance (miles)`; README missing Distance unit).

- [ ] **Step 3: Write minimal implementation**

In all three dashboard files, replace the Away distance row and insert Distance unit immediately after it:

```yaml
          - entity: input_number.presence_simulator_away_miles
            name: Away distance
          - entity: input_select.presence_simulator_distance_unit
            name: Distance unit
          - entity: input_select.presence_simulator_ask_if_off_while_away
            name: Ask if off while away
```

In `README.md`:

- Opening Auto away sentence: **Away distance** with **Distance unit** **Miles (mi)** or **Kilometers (km)** (default Miles (mi)); switching units converts the number so the GPS radius stays the same.
- Helper table: change `input_number.presence_simulator_away_miles` purpose to `Away distance (unit from Distance unit)`. Add row `input_select.presence_simulator_distance_unit` | `Miles (mi)` | `Miles (mi) or Kilometers (km); converts Away distance`.
- Auto away smoke notes: “leave beyond 1 mile (or ~1.6 km if Distance unit is Kilometers (km))” and “Return within that Away distance”.

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 -m pytest tests/test_presence_simulator_package.py -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py presence-simulator.yaml dashboards/presence_simulator.yaml ui-lovelace.yaml README.md handover.md
git commit -m "Put Distance unit on the Presence simulator menu and document conversion."
```

---

### Task 5: Live deploy

**Files:**
- Live: `/config/packages/presence_simulator.yaml`
- Live: `/config/presence-simulator.yaml` (sidebar menu)
- Modify: `handover.md`

**Interfaces:**
- Consumes: repo files from Tasks 1–4.
- Produces: live helpers `input_select.presence_simulator_distance_unit`; menu rows; `ha core check` success.

- [ ] **Step 1: Backup and copy package through HA Terminal**

Open `http://your ip address running HA/` (port 80). Sidebar **Terminal** (`/a0d7b954_ssh`).

```bash
cp /config/packages/presence_simulator.yaml /config/packages/presence_simulator.yaml.bak
```

Copy this repo’s `packages/presence_simulator.yaml` onto `/config/packages/presence_simulator.yaml` (short `echo` lines; zsh needs Enter after a multi-line paste). Copy `presence-simulator.yaml` onto `/config/presence-simulator.yaml` as UTF-8.

- [ ] **Step 2: Check and restart**

```bash
ha core check
ha core restart
```

Expected: check succeeds; Overview comes back.

- [ ] **Step 3: Confirm the menu**

Wait until Overview comes back. On the Presence simulator menu, confirm **Away distance** (no miles suffix) and **Distance unit** default **Miles (mi)**. Switch to **Kilometers (km)** → number becomes ~1.6 if it was 1. Switch back → ~1.0. Leave Auto away as the user had it.

- [ ] **Step 4: Push GitHub and handover**

```bash
git push
```

Prepend `handover.md` with the live copy sizes and that Distance unit is on the menu, then commit if that file is still dirty:

```bash
git add handover.md
git commit -m "Note live Distance unit deploy on your ip address running HA."
git push
```

---

## Self-review (spec coverage)

| Spec requirement | Task |
| --- | --- |
| Distance unit dropdown `Miles (mi)` / `Kilometers (km)`, default miles | 1, 4 |
| Keep `presence_simulator_away_miles`; name Away distance; max 200; no unit suffix | 1, 4 |
| Convert on switch; skip HA restart; round 1 decimal; clamp 0.1–200 | 2 |
| GPS km = × 1.609344 if miles else as-is; evaluate trigger includes select | 3 |
| Dashboards + README | 4 |
| Live Terminal deploy | 5 |
