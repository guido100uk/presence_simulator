# Presence Simulator Auto Away Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional Auto away so GPS distance can turn the existing Presence simulator master switch on when everyone is beyond Away distance (miles), and off on return without turning grouped lights off, with a correct/mistake question if the user turns the switch off while still away.

**Architecture:** Keep one YAML package. New input helpers plus four automations live in `packages/presence_simulator.yaml`. Auto away only flips `input_boolean.presence_simulator`; the evening loop, sunset/start, bedtime, and light group stay as they are. `presence_simulator_stop_on_switch` skips `light.turn_off` when `input_boolean.presence_simulator_quiet_off` is on. Dashboards get the three user settings and two answer buttons; internals stay off the menu.

**Tech Stack:** Home Assistant YAML packages, Jinja (`distance()`, `states.person`), Companion actionable `notify.notify`, `persistent_notification`, Python 3 + pytest + PyYAML.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-08-presence-simulator-auto-away-design.md`
- Do **not** hard-code `person.*`, `device_tracker.*`, or `notify.mobile_app_*` entity IDs.
- Distance is miles in the UI; compare with `distance('zone.home', person_id)` (km) using `away_miles * 1.609344`.
- Unknown GPS (missing `latitude` or `longitude`) counts as **away**.
- Auto-on only when Auto away is on, house empty, holdoff off, confirm pending off, `zone.home` exists, and there is at least one `person.*`.
- Return home: turn master switch off, **leave lights as they are** (quiet off). Bedtime still turns grouped lights off.
- Ask-if-off destinations: exact strings `Phone`, `Home Assistant`, `Both`; default `Both`.
- Question notification_id: `presence_simulator_off_while_away`. Mobile action ids: `PRESENCE_SIMULATOR_OFF_CORRECT`, `PRESENCE_SIMULATOR_OFF_MISTAKE`.
- Do not install Proximity or extra zones. Do not change the loop member-expand fix (`state_attr` of the light group, never `expand('light.presence_simulator_lights')`).
- Tests: `py -3 -m pytest tests/test_presence_simulator_package.py -v` (Windows; not `python`).
- Live HA: `http://your ip address running HA/` port 80. Deploy via sidebar Terminal only. Do not replace live `configuration.yaml`. Do not read `hassTokens`.

---

## File structure

| File | Responsibility |
| --- | --- |
| `tests/test_presence_simulator_package.py` | Contract tests for new helpers, automations, dashboards, README, no hard-coded people/notify ids |
| `packages/presence_simulator.yaml` | Helpers + quiet-off stop + evaluate + question automations |
| `presence-simulator.yaml` | Live sidebar menu rows |
| `dashboards/presence_simulator.yaml` | Extra copy of the same menu |
| `ui-lovelace.yaml` | Demo Overview copy of the same menu |
| `README.md` | Auto away, miles, dropdown, Companion GPS, smoke notes |
| `handover.md` | Changelog for each commit |

## Shared Jinja (paste verbatim wherever a task needs it)

**Someone home** (`someone_home`):

```jinja
{% set miles = states('input_number.presence_simulator_away_miles') | float(1) %}
{% set km = miles * 1.609344 %}
{% set ns = namespace(home=false) %}
{% if states.zone.home is defined %}
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

**House empty** (`house_empty`):

```jinja
{% set miles = states('input_number.presence_simulator_away_miles') | float(1) %}
{% set km = miles * 1.609344 %}
{% set people = states.person %}
{% if states.zone.home is not defined or people | count == 0 %}
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

**Question message** (exact):

```text
You turned Presence simulator off while still farther than Away distance (or GPS is unknown). Was that correct, or a mistake?
```

---

### Task 1: Auto away helpers

**Files:**
- Modify: `tests/test_presence_simulator_package.py`
- Modify: `packages/presence_simulator.yaml` (helpers only)
- Modify: `handover.md`

**Interfaces:**
- Consumes: existing `input_boolean` / `input_number` blocks in the package.
- Produces: `input_boolean.presence_simulator_auto_away`, `input_boolean.presence_simulator_auto_holdoff`, `input_boolean.presence_simulator_quiet_off`, `input_boolean.presence_simulator_confirm_off_pending`, `input_number.presence_simulator_away_miles` (min `0.1`, max `100`, step `0.1`, initial `1`, unit `mi`), `input_select.presence_simulator_ask_if_off_while_away` (options `Phone`, `Home Assistant`, `Both`, initial `Both`), `input_button.presence_simulator_off_correct`, `input_button.presence_simulator_off_mistake`.

- [ ] **Step 1: Write the failing helper tests**

Append to `tests/test_presence_simulator_package.py`:

```python
def test_package_defines_auto_away_helpers(package):
    booleans = package["input_boolean"]
    assert "presence_simulator_auto_away" in booleans
    assert booleans["presence_simulator_auto_away"]["name"] == "Auto away"
    assert "presence_simulator_auto_holdoff" in booleans
    assert "presence_simulator_quiet_off" in booleans
    assert "presence_simulator_confirm_off_pending" in booleans
    miles = package["input_number"]["presence_simulator_away_miles"]
    assert miles["name"] == "Away distance (miles)"
    assert miles["min"] == 0.1
    assert miles["max"] == 100
    assert miles["step"] == 0.1
    assert miles["initial"] == 1
    assert miles["unit_of_measurement"] == "mi"
    ask = package["input_select"]["presence_simulator_ask_if_off_while_away"]
    assert ask["name"] == "Ask if off while away"
    assert ask["options"] == ["Phone", "Home Assistant", "Both"]
    assert ask["initial"] == "Both"
    buttons = package["input_button"]
    assert "presence_simulator_off_correct" in buttons
    assert "presence_simulator_off_mistake" in buttons
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py::test_package_defines_auto_away_helpers -v
```

Expected: FAIL (`KeyError` or assertion) because the helpers are missing.

- [ ] **Step 3: Add helpers to the package**

In `packages/presence_simulator.yaml`, add under `input_boolean` (after `presence_simulator_use_sunset`):

```yaml
  presence_simulator_auto_away:
    name: Auto away
    icon: mdi:map-marker-radius
  presence_simulator_auto_holdoff:
    name: Presence simulator auto holdoff
    icon: mdi:pause-circle
  presence_simulator_quiet_off:
    name: Presence simulator quiet off
    icon: mdi:volume-off
  presence_simulator_confirm_off_pending:
    name: Presence simulator confirm off pending
    icon: mdi:help-circle
```

Add under `input_number` (after `presence_simulator_max_minutes`):

```yaml
  presence_simulator_away_miles:
    name: Away distance (miles)
    min: 0.1
    max: 100
    step: 0.1
    mode: box
    unit_of_measurement: mi
    initial: 1
    icon: mdi:map-marker-distance
```

Add new top-level keys (after `input_number`, before `script`):

```yaml
input_select:
  presence_simulator_ask_if_off_while_away:
    name: Ask if off while away
    options:
      - Phone
      - Home Assistant
      - Both
    initial: Both
    icon: mdi:message-question

input_button:
  presence_simulator_off_correct:
    name: Off while away was correct
    icon: mdi:check
  presence_simulator_off_mistake:
    name: Off while away was a mistake
    icon: mdi:undo
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py -v
```

Expected: all tests PASS (including the new helper test). Existing automation-id equality still matches the original six ids.

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py packages/presence_simulator.yaml handover.md
git commit -m "Add Auto away helpers so distance and ask-if-off can be set from the menu."
```

Prepend `handover.md` with the commit title and files.

---

### Task 2: Quiet off on stop-on-switch

**Files:**
- Modify: `tests/test_presence_simulator_package.py`
- Modify: `packages/presence_simulator.yaml` (`id: presence_simulator_stop_on_switch` only)
- Modify: `handover.md`

**Interfaces:**
- Consumes: `input_boolean.presence_simulator_quiet_off` from Task 1.
- Produces: stop-on-switch still aborts `script.presence_simulator_loop`; `light.turn_off` on `light.presence_simulator_lights` only in the branch where quiet off is **not** `on`; quiet off is turned off after that skip.

- [ ] **Step 1: Write the failing quiet-off test**

Keep `test_stop_automations_abort_script_and_turn_group_off` as it is (`light.turn_off` still appears in the else branch). Append:

```python
def test_stop_on_switch_skips_group_off_when_quiet_off(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_stop_on_switch"])
    assert "input_boolean.presence_simulator_quiet_off" in blob
    assert "script.turn_off" in blob
    assert "light.turn_off" in blob
    assert "light.presence_simulator_lights" in blob
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py::test_stop_on_switch_skips_group_off_when_quiet_off -v
```

Expected: FAIL because `presence_simulator_quiet_off` is not in the automation yet.

- [ ] **Step 3: Change stop-on-switch actions**

Replace the `action:` list of `presence_simulator_stop_on_switch` with:

```yaml
    action:
      - action: script.turn_off
        target:
          entity_id: script.presence_simulator_loop
      - if:
          - condition: state
            entity_id: input_boolean.presence_simulator_quiet_off
            state: "on"
        then:
          - action: input_boolean.turn_off
            target:
              entity_id: input_boolean.presence_simulator_quiet_off
        else:
          - action: light.turn_off
            target:
              entity_id: light.presence_simulator_lights
```

Do **not** change `presence_simulator_stop_bedtime`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py packages/presence_simulator.yaml handover.md
git commit -m "Skip turning grouped lights off when Auto away quietly stops the simulator."
```

---

### Task 3: Evaluate house empty vs someone home

**Files:**
- Modify: `tests/test_presence_simulator_package.py` (`REQUIRED_AUTOMATION_IDS` usage)
- Modify: `packages/presence_simulator.yaml` (append automation `presence_simulator_auto_away_evaluate`)
- Modify: `handover.md`

**Interfaces:**
- Consumes: helpers from Task 1; `someone_home` and `house_empty` Jinja from Shared Jinja; quiet off from Task 2.
- Produces: automation id `presence_simulator_auto_away_evaluate`. Someone home always clears holdoff and pending and dismisses `presence_simulator_off_while_away`. If Auto away is on and the master switch is on, also turn quiet off on then turn the master switch off. Auto-on turns the master switch on only when Auto away is on, house empty, holdoff off, and pending off.

- [ ] **Step 1: Write the failing evaluate tests**

Change `test_required_automations_exist` so the original six plus auto-away ids must all exist. Add this set next to `REQUIRED_AUTOMATION_IDS`:

```python
AUTO_AWAY_AUTOMATION_IDS = {
    "presence_simulator_auto_away_evaluate",
}
```

Change `test_required_automations_exist` to:

```python
def test_required_automations_exist(package):
    assert REQUIRED_AUTOMATION_IDS | AUTO_AWAY_AUTOMATION_IDS == set(_automations(package))
```

Append:

```python
def test_auto_away_evaluate_uses_distance_and_all_persons(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_auto_away_evaluate"])
    assert "states.person" in blob
    assert "zone.home" in blob
    assert "distance(" in blob
    assert "1.609344" in blob
    assert "presence_simulator_away_miles" in blob
    assert "presence_simulator_auto_away" in blob
    assert "presence_simulator_auto_holdoff" in blob
    assert "presence_simulator_confirm_off_pending" in blob
    assert "presence_simulator_quiet_off" in blob
    assert "input_boolean.presence_simulator" in blob
    assert "presence_simulator_off_while_away" in blob
    assert "notify.mobile_app_" not in blob


def test_package_does_not_hardcode_people_or_mobile_notify(package):
    import re

    blob = yaml_dump_section(package)
    assert "notify.mobile_app_" not in blob
    assert re.search(r"person\.[a-z][a-z0-9_]+", blob) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py::test_required_automations_exist tests/test_presence_simulator_package.py::test_auto_away_evaluate_uses_distance_and_all_persons -v
```

Expected: FAIL (`KeyError` for the new id, or set inequality).

- [ ] **Step 3: Add the evaluate automation**

Append to the `automation:` list in `packages/presence_simulator.yaml`:

```yaml
  - id: presence_simulator_auto_away_evaluate
    alias: Presence simulator auto away evaluate
    mode: restart
    trigger:
      - trigger: event
        event_type: state_changed
      - trigger: time_pattern
        minutes: "/1"
      - trigger: homeassistant
        event: start
      - trigger: state
        entity_id:
          - input_boolean.presence_simulator_auto_away
          - input_number.presence_simulator_away_miles
          - input_boolean.presence_simulator_auto_holdoff
          - input_boolean.presence_simulator_confirm_off_pending
    condition:
      - condition: template
        value_template: >
          {% if trigger.platform == 'event' %}
            {{ trigger.event.data.entity_id is match('^person\\.') }}
          {% else %}
            true
          {% endif %}
    action:
      - choose:
          - conditions:
              - condition: template
                value_template: >
                  {% set miles = states('input_number.presence_simulator_away_miles') | float(1) %}
                  {% set km = miles * 1.609344 %}
                  {% set ns = namespace(home=false) %}
                  {% if states.zone.home is defined %}
                    {% for p in states.person %}
                      {% set lat = state_attr(p.entity_id, 'latitude') %}
                      {% set lon = state_attr(p.entity_id, 'longitude') %}
                      {% if lat is not none and lon is not none and distance('zone.home', p.entity_id) <= km %}
                        {% set ns.home = true %}
                      {% endif %}
                    {% endfor %}
                  {% endif %}
                  {{ ns.home }}
            sequence:
              - action: input_boolean.turn_off
                target:
                  entity_id: input_boolean.presence_simulator_auto_holdoff
              - action: input_boolean.turn_off
                target:
                  entity_id: input_boolean.presence_simulator_confirm_off_pending
              - action: persistent_notification.dismiss
                data:
                  notification_id: presence_simulator_off_while_away
              - if:
                  - condition: state
                    entity_id: input_boolean.presence_simulator_auto_away
                    state: "on"
                  - condition: state
                    entity_id: input_boolean.presence_simulator
                    state: "on"
                then:
                  - action: input_boolean.turn_on
                    target:
                      entity_id: input_boolean.presence_simulator_quiet_off
                  - action: input_boolean.turn_off
                    target:
                      entity_id: input_boolean.presence_simulator
          - conditions:
              - condition: state
                entity_id: input_boolean.presence_simulator_auto_away
                state: "on"
              - condition: state
                entity_id: input_boolean.presence_simulator_auto_holdoff
                state: "off"
              - condition: state
                entity_id: input_boolean.presence_simulator_confirm_off_pending
                state: "off"
              - condition: template
                value_template: >
                  {% set miles = states('input_number.presence_simulator_away_miles') | float(1) %}
                  {% set km = miles * 1.609344 %}
                  {% set people = states.person %}
                  {% if states.zone.home is not defined or people | count == 0 %}
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
            sequence:
              - action: input_boolean.turn_on
                target:
                  entity_id: input_boolean.presence_simulator
```

Do not trigger this automation on the master switch. Pending is set by Task 4 on the same off event; evaluate must not auto-on while pending is on.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py packages/presence_simulator.yaml handover.md
git commit -m "Turn Presence simulator on and off from GPS distance without hard-coded people."
```

---

### Task 4: Off-while-away question

**Files:**
- Modify: `tests/test_presence_simulator_package.py`
- Modify: `packages/presence_simulator.yaml` (three automations)
- Modify: `handover.md`

**Interfaces:**
- Consumes: `house_empty` Jinja; `input_select.presence_simulator_ask_if_off_while_away`; buttons; pending; holdoff; `notify.notify`; `persistent_notification`.
- Produces: ids `presence_simulator_manual_off_while_away`, `presence_simulator_confirm_off_correct`, `presence_simulator_confirm_off_mistake`. Manual off while Auto away is on, quiet off is off, and house empty sets pending then notifies. Phone if select is not `Home Assistant`. Persistent notification if select is not `Phone`. Correct sets holdoff and clears pending. Mistake turns the master switch on and clears pending. Both no-op unless pending is on.

- [ ] **Step 1: Write the failing question tests**

Expand `AUTO_AWAY_AUTOMATION_IDS` to:

```python
AUTO_AWAY_AUTOMATION_IDS = {
    "presence_simulator_auto_away_evaluate",
    "presence_simulator_manual_off_while_away",
    "presence_simulator_confirm_off_correct",
    "presence_simulator_confirm_off_mistake",
}
```

Append:

```python
def test_manual_off_while_away_asks_correct_or_mistake(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_manual_off_while_away"])
    assert "presence_simulator_confirm_off_pending" in blob
    assert "presence_simulator_ask_if_off_while_away" in blob
    assert "notify.notify" in blob
    assert "persistent_notification.create" in blob
    assert "presence_simulator_off_while_away" in blob
    assert "PRESENCE_SIMULATOR_OFF_CORRECT" in blob
    assert "PRESENCE_SIMULATOR_OFF_MISTAKE" in blob
    assert "Phone" in blob
    assert "Home Assistant" in blob
    assert "notify.mobile_app_" not in blob
    assert "states.person" in blob
    assert "1.609344" in blob


def test_confirm_off_correct_sets_holdoff(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_confirm_off_correct"])
    assert "PRESENCE_SIMULATOR_OFF_CORRECT" in blob
    assert "presence_simulator_off_correct" in blob
    assert "presence_simulator_auto_holdoff" in blob
    assert "presence_simulator_confirm_off_pending" in blob
    assert "presence_simulator_off_while_away" in blob


def test_confirm_off_mistake_turns_simulator_back_on(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_confirm_off_mistake"])
    assert "PRESENCE_SIMULATOR_OFF_MISTAKE" in blob
    assert "presence_simulator_off_mistake" in blob
    assert "input_boolean.presence_simulator" in blob
    assert "presence_simulator_confirm_off_pending" in blob
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py::test_required_automations_exist tests/test_presence_simulator_package.py::test_manual_off_while_away_asks_correct_or_mistake -v
```

Expected: FAIL (missing automation ids).

- [ ] **Step 3: Add the three automations**

Append after `presence_simulator_auto_away_evaluate`:

```yaml
  - id: presence_simulator_manual_off_while_away
    alias: Presence simulator manual off while away
    mode: single
    trigger:
      - trigger: state
        entity_id: input_boolean.presence_simulator
        to: "off"
    condition:
      - condition: state
        entity_id: input_boolean.presence_simulator_auto_away
        state: "on"
      - condition: state
        entity_id: input_boolean.presence_simulator_quiet_off
        state: "off"
      - condition: template
        value_template: >
          {% set miles = states('input_number.presence_simulator_away_miles') | float(1) %}
          {% set km = miles * 1.609344 %}
          {% set people = states.person %}
          {% if states.zone.home is not defined or people | count == 0 %}
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
    action:
      - action: input_boolean.turn_on
        target:
          entity_id: input_boolean.presence_simulator_confirm_off_pending
      - if:
          - condition: template
            value_template: >
              {{ states('input_select.presence_simulator_ask_if_off_while_away') != 'Home Assistant' }}
        then:
          - action: notify.notify
            data:
              title: Presence simulator
              message: You turned Presence simulator off while still farther than Away distance (or GPS is unknown). Was that correct, or a mistake?
              data:
                actions:
                  - action: PRESENCE_SIMULATOR_OFF_CORRECT
                    title: Correct
                  - action: PRESENCE_SIMULATOR_OFF_MISTAKE
                    title: Mistake
      - if:
          - condition: template
            value_template: >
              {{ states('input_select.presence_simulator_ask_if_off_while_away') != 'Phone' }}
        then:
          - action: persistent_notification.create
            data:
              notification_id: presence_simulator_off_while_away
              title: Presence simulator
              message: You turned Presence simulator off while still farther than Away distance (or GPS is unknown). Was that correct, or a mistake? Use Off while away was correct / Off while away was a mistake on the Presence simulator menu.

  - id: presence_simulator_confirm_off_correct
    alias: Presence simulator confirm off correct
    mode: single
    trigger:
      - trigger: state
        entity_id: input_button.presence_simulator_off_correct
      - trigger: event
        event_type: mobile_app_notification_action
        event_data:
          action: PRESENCE_SIMULATOR_OFF_CORRECT
    condition:
      - condition: state
        entity_id: input_boolean.presence_simulator_confirm_off_pending
        state: "on"
    action:
      - action: input_boolean.turn_on
        target:
          entity_id: input_boolean.presence_simulator_auto_holdoff
      - action: input_boolean.turn_off
        target:
          entity_id: input_boolean.presence_simulator_confirm_off_pending
      - action: persistent_notification.dismiss
        data:
          notification_id: presence_simulator_off_while_away

  - id: presence_simulator_confirm_off_mistake
    alias: Presence simulator confirm off mistake
    mode: single
    trigger:
      - trigger: state
        entity_id: input_button.presence_simulator_off_mistake
      - trigger: event
        event_type: mobile_app_notification_action
        event_data:
          action: PRESENCE_SIMULATOR_OFF_MISTAKE
    condition:
      - condition: state
        entity_id: input_boolean.presence_simulator_confirm_off_pending
        state: "on"
    action:
      - action: input_boolean.turn_off
        target:
          entity_id: input_boolean.presence_simulator_confirm_off_pending
      - action: input_boolean.turn_on
        target:
          entity_id: input_boolean.presence_simulator
      - action: persistent_notification.dismiss
        data:
          notification_id: presence_simulator_off_while_away
```

Set pending **first** in the manual-off action list so evaluate cannot auto-on before pending is on.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py -v
```

Expected: PASS (19 previous tests plus the new ones).

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py packages/presence_simulator.yaml handover.md
git commit -m "Ask whether a manual off while away was correct before Auto away turns the simulator back on."
```

---

### Task 5: Menu and README

**Files:**
- Modify: `tests/test_presence_simulator_package.py`
- Modify: `presence-simulator.yaml`
- Modify: `dashboards/presence_simulator.yaml`
- Modify: `ui-lovelace.yaml`
- Modify: `README.md`
- Modify: `handover.md`

**Interfaces:**
- Consumes: helper entity ids and menu names from Task 1.
- Produces: all three dashboard files list Auto away, Away distance (miles), Ask if off while away, and the two buttons; they must **not** list holdoff, quiet off, or confirm pending. README documents Auto away, miles, dropdown, Companion GPS, and smoke notes.

- [ ] **Step 1: Write the failing dashboard and README tests**

Append:

```python
def test_dashboard_shows_auto_away_controls_not_internals():
    import yaml

    for path in (DASHBOARD_PATH, UI_LOVELACE_PATH, ROOT / "dashboards" / "presence_simulator.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        blob = yaml.safe_dump(data, sort_keys=False)
        assert "input_boolean.presence_simulator_auto_away" in blob
        assert "Auto away" in blob
        assert "input_number.presence_simulator_away_miles" in blob
        assert "Away distance (miles)" in blob
        assert "input_select.presence_simulator_ask_if_off_while_away" in blob
        assert "Ask if off while away" in blob
        assert "input_button.presence_simulator_off_correct" in blob
        assert "input_button.presence_simulator_off_mistake" in blob
        assert "input_boolean.presence_simulator_auto_holdoff" not in blob
        assert "input_boolean.presence_simulator_quiet_off" not in blob
        assert "input_boolean.presence_simulator_confirm_off_pending" not in blob


def test_readme_covers_auto_away():
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "auto away" in text
    assert "away distance" in text
    assert "ask if off while away" in text
    assert "companion" in text
    assert "miles" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py::test_dashboard_shows_auto_away_controls_not_internals tests/test_presence_simulator_package.py::test_readme_covers_auto_away -v
```

Expected: FAIL (entities missing from dashboards / README).

- [ ] **Step 3: Add the same five entity rows to all three dashboards**

In `presence-simulator.yaml`, `dashboards/presence_simulator.yaml`, and `ui-lovelace.yaml`, append inside the `entities:` list after max minutes:

```yaml
          - entity: input_boolean.presence_simulator_auto_away
            name: Auto away
          - entity: input_number.presence_simulator_away_miles
            name: Away distance (miles)
          - entity: input_select.presence_simulator_ask_if_off_while_away
            name: Ask if off while away
          - entity: input_button.presence_simulator_off_correct
            name: Off while away was correct
          - entity: input_button.presence_simulator_off_mistake
            name: Off while away was a mistake
```

In `README.md`:

- Add a sentence under the opening paragraph: Auto away can turn the master switch on when every `person` is farther than **Away distance (miles)** (or GPS is unknown), and off when someone with GPS is within that distance; lights stay as they are on return.
- Add helper table rows for `input_boolean.presence_simulator_auto_away` (off), `input_number.presence_simulator_away_miles` (1), `input_select.presence_simulator_ask_if_off_while_away` (Both).
- Note that people need the Companion app (or another GPS tracker linked to a person). Do not hard-code person names.
- Smoke notes: Auto away off → no GPS change. Auto away on, leave beyond 1 mile → switch on after GPS updates (loop still waits for the evening window). Return within 1 mile → switch off, lights stay. Manual off while away → question on Phone / Home Assistant / Both; Correct stays off until someone comes home; Mistake turns the switch back on.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py presence-simulator.yaml dashboards/presence_simulator.yaml ui-lovelace.yaml README.md handover.md
git commit -m "Put Auto away controls on the Presence simulator menu and document Companion GPS."
```

---

### Task 6: Live deploy

**Files:**
- Live: `/config/packages/presence_simulator.yaml`
- Live: `/config/presence-simulator.yaml` (sidebar menu)
- Repo: `handover.md` (after deploy)

**Interfaces:**
- Consumes: completed package and `presence-simulator.yaml` from Tasks 1–5.
- Produces: live HA loads Auto away after `ha core check` and `ha core restart`. GitHub `master` includes the same files.

- [ ] **Step 1: Confirm tests still pass on this machine**

Run:

```bash
py -3 -m pytest tests/test_presence_simulator_package.py -v
```

Expected: PASS. Do not deploy if tests fail.

- [ ] **Step 2: Open live Terminal**

Open `http://your ip address running HA/` (port 80). Sidebar **Terminal** (`/a0d7b954_ssh`). Wait if Auto-review blocks the live write; after approval, continue.

- [ ] **Step 3: Backup**

```bash
cp /config/packages/presence_simulator.yaml /config/packages/presence_simulator.yaml.bak
cp /config/presence-simulator.yaml /config/presence-simulator.yaml.bak
```

- [ ] **Step 4: Copy package and dashboard**

Write `/config/packages/presence_simulator.yaml` and `/config/presence-simulator.yaml` through that Terminal using short `echo` lines (zsh needs Enter after a multi-line paste). Do not replace live `configuration.yaml`. Do not use Samba/SSH from this PC.

- [ ] **Step 5: Check and restart**

```bash
ha core check
```

Expected: configuration valid. Then:

```bash
ha core restart
```

Wait until Overview comes back. On the Presence simulator menu, confirm **Auto away**, **Away distance (miles)**, **Ask if off while away**, and the two buttons exist. Leave Auto away **off** unless the user wants it on immediately.

- [ ] **Step 6: Push GitHub and handover**

If any unpushed commits remain:

```bash
git push origin HEAD
```

Prepend `handover.md` with the live paths, `ha core check` result, and restart. Commit that log if it is not already in the last feature commit, then push.

```bash
git add handover.md
git commit -m "Record that Auto away was copied onto the live Home Assistant machine."
git push origin HEAD
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
| --- | --- |
| Auto away toggle, miles default 1, ask dropdown default Both | 1, 5 |
| Holdoff, quiet off, pending, two buttons | 1, 5 |
| All `person.*`, unknown GPS = away, miles × 1.609344, `zone.home` | 3, 4 |
| Auto-on / auto-off rules; lights stay on return | 2, 3 |
| Bedtime unchanged | 2 (do not touch bedtime) |
| Manual off while away; Phone / HA / Both; menu buttons always | 4, 5 |
| Correct = holdoff; Mistake = turn switch on; pending blocks auto-on | 3, 4 |
| No hard-coded person or `notify.mobile_app_*` | 3, 4 tests |
| README + contract tests | 5 |
| Live deploy via Terminal | 6 |
