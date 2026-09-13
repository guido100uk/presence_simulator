# Presence Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Home Assistant package that, while a manual switch is on, randomly turns a user-picked light group on and off during an evening window and turns those lights off at bedtime or when the switch is turned off.

**Architecture:** One YAML package (`packages/presence_simulator.yaml`) holds input helpers, an abortable loop script, and start/stop automations. The user creates a Light Group helper named **Presence simulator lights** (`light.presence_simulator_lights`) and adds members in the Home Assistant UI. A minimal `configuration.yaml` enables `packages:` for this repo as a config root. Pytest parses the YAML and checks the entity/script contract; live bulbs are not required.

**Tech Stack:** Home Assistant YAML packages, Jinja templates, Python 3 + pytest + PyYAML.

## Global Constraints

- Activation is **manual switch only** (`input_boolean.presence_simulator`); no away/person/zone detection.
- Do **not** hard-code household light entity IDs. The only light target is `light.presence_simulator_lights`.
- Evening window is **same local calendar day**. Bedtime must be after the effective start. Overnight windows are out of scope.
- If **Use sunset** is on, start is `sun.sun` below the horizon; if off, start is `input_datetime.presence_simulator_start`. End is `input_datetime.presence_simulator_bedtime`.
- Loop script must be abortable with `script.turn_off` (`mode: restart`).
- Stable entity IDs from the spec (do not rename): `input_boolean.presence_simulator`, `input_boolean.presence_simulator_use_sunset`, `input_datetime.presence_simulator_start`, `input_datetime.presence_simulator_bedtime`, `input_number.presence_simulator_min_minutes`, `input_number.presence_simulator_max_minutes`, `light.presence_simulator_lights`, `script.presence_simulator_loop`.
- Automation `id` values: `presence_simulator_start_sunset`, `presence_simulator_start_time`, `presence_simulator_start_on_switch`, `presence_simulator_resume_on_start`, `presence_simulator_stop_bedtime`, `presence_simulator_stop_on_switch`.
- Helper defaults: switch off; use-sunset intended on (README tells the user to enable it on first install because `input_boolean` has no YAML initial); start `18:00`; bedtime `23:00`; min `5`; max `25`.
- Do not add brightness, colour, scenes, weekday calendars, or automatic away detection.

---

## File structure

| File | Responsibility |
| --- | --- |
| `requirements-dev.txt` | pytest and PyYAML for contract tests |
| `tests/conftest.py` | Load package YAML; parse `configuration.yaml` including `!include_dir_named` |
| `tests/test_presence_simulator_package.py` | YAML validity, entity contract, template sanity, README smoke-test notes |
| `configuration.yaml` | `default_config` + `homeassistant.packages` include |
| `packages/presence_simulator.yaml` | Helpers, loop script, start/stop automations |
| `README.md` | Install, create light group, defaults, 5-minute smoke test |

---

### Task 1: Test harness and helper contract

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/conftest.py`
- Create: `tests/test_presence_simulator_package.py`
- Create: `configuration.yaml`
- Create: `packages/presence_simulator.yaml`

**Interfaces:**
- Consumes: nothing (empty repo aside from the spec).
- Produces: `load_package()` → `dict`; `load_configuration()` → `dict`; package helpers under `input_boolean`, `input_datetime`, `input_number` with the spec entity keys (without the domain prefix).

- [ ] **Step 1: Write the failing tests and harness**

Create `requirements-dev.txt`:

```text
pytest>=8.0
PyYAML>=6.0
```

Create `tests/conftest.py`:

```python
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "packages" / "presence_simulator.yaml"
CONFIG_PATH = ROOT / "configuration.yaml"


def _ignore_include(loader, node):
    return str(loader.construct_scalar(node))


def load_package() -> dict:
    return yaml.safe_load(PACKAGE_PATH.read_text(encoding="utf-8"))


def load_configuration() -> dict:
    loader = yaml.SafeLoader
    loader.add_constructor("!include_dir_named", _ignore_include)
    return yaml.load(CONFIG_PATH.read_text(encoding="utf-8"), Loader=loader)


@pytest.fixture
def package() -> dict:
    return load_package()
```

Create `tests/test_presence_simulator_package.py` with only the helper/config tests for this task:

```python
from pathlib import Path

from conftest import CONFIG_PATH, PACKAGE_PATH, load_configuration


ROOT = Path(__file__).resolve().parents[1]


def test_package_yaml_is_well_formed(package):
    assert isinstance(package, dict)


def test_configuration_yaml_is_well_formed():
    config = load_configuration()
    assert config["homeassistant"]["packages"] == "packages"
    assert "default_config" in config


def test_package_defines_required_helpers(package):
    assert "presence_simulator" in package["input_boolean"]
    assert "presence_simulator_use_sunset" in package["input_boolean"]
    assert "presence_simulator_start" in package["input_datetime"]
    assert "presence_simulator_bedtime" in package["input_datetime"]
    assert package["input_datetime"]["presence_simulator_start"]["has_date"] is False
    assert package["input_datetime"]["presence_simulator_start"]["has_time"] is True
    assert package["input_datetime"]["presence_simulator_bedtime"]["has_date"] is False
    assert package["input_datetime"]["presence_simulator_bedtime"]["has_time"] is True
    mins = package["input_number"]["presence_simulator_min_minutes"]
    maxs = package["input_number"]["presence_simulator_max_minutes"]
    assert mins["initial"] == 5
    assert maxs["initial"] == 25
    assert mins["min"] == 1
    assert maxs["min"] == 1


def test_package_and_config_files_exist():
    assert PACKAGE_PATH.is_file()
    assert CONFIG_PATH.is_file()
    assert (ROOT / "requirements-dev.txt").is_file()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/test_presence_simulator_package.py -v
```

Expected: FAIL because `packages/presence_simulator.yaml` and/or `configuration.yaml` do not exist (`FileNotFoundError`) or helpers are missing.

- [ ] **Step 3: Write minimal configuration and helpers**

Create `configuration.yaml`:

```yaml
default_config:

homeassistant:
  packages: !include_dir_named packages
```

Create `packages/presence_simulator.yaml`:

```yaml
input_boolean:
  presence_simulator:
    name: Presence simulator
    icon: mdi:home-account
  presence_simulator_use_sunset:
    name: Presence simulator use sunset
    icon: mdi:weather-sunset

input_datetime:
  presence_simulator_start:
    name: Presence simulator start
    has_date: false
    has_time: true
    icon: mdi:clock-start
  presence_simulator_bedtime:
    name: Presence simulator bedtime
    has_date: false
    has_time: true
    icon: mdi:clock-end

input_number:
  presence_simulator_min_minutes:
    name: Presence simulator min minutes
    min: 1
    max: 120
    step: 1
    mode: box
    unit_of_measurement: min
    initial: 5
    icon: mdi:timer-minus
  presence_simulator_max_minutes:
    name: Presence simulator max minutes
    min: 1
    max: 180
    step: 1
    mode: box
    unit_of_measurement: min
    initial: 25
    icon: mdi:timer-plus
```

Do not add household `light.*` entity IDs. Do not add the loop script yet.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_presence_simulator_package.py -v
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add requirements-dev.txt tests/conftest.py tests/test_presence_simulator_package.py configuration.yaml packages/presence_simulator.yaml
git commit -m "test: add presence simulator helper contract and package stubs"
```

---

### Task 2: Loop script with template sanity

**Files:**
- Modify: `tests/test_presence_simulator_package.py` (append script tests)
- Modify: `packages/presence_simulator.yaml` (add `script.presence_simulator_loop`)

**Interfaces:**
- Consumes: helpers from Task 1 (`input_boolean.presence_simulator`, `input_boolean.presence_simulator_use_sunset`, `input_datetime.presence_simulator_start`, `input_datetime.presence_simulator_bedtime`, `input_number.presence_simulator_min_minutes`, `input_number.presence_simulator_max_minutes`).
- Produces: `script.presence_simulator_loop` — `mode: restart`, `repeat.while` gated by switch + evening window, random usable member `on`/`off`, delay using min/max with `min + 1` when max ≤ min, skip when the group has no `on`/`off` members.

- [ ] **Step 1: Write the failing script tests**

Append to `tests/test_presence_simulator_package.py`:

```python
def _script_blob(package) -> str:
    return yaml_dump_section(package["script"]["presence_simulator_loop"])


def yaml_dump_section(section) -> str:
    import yaml

    return yaml.safe_dump(section, sort_keys=False)


def test_loop_script_is_abortable(package):
    script = package["script"]["presence_simulator_loop"]
    assert script["mode"] == "restart"


def test_loop_script_gates_on_switch_and_same_day_window(package):
    blob = _script_blob(package)
    assert "input_boolean.presence_simulator" in blob
    assert "presence_simulator_use_sunset" in blob
    assert "below_horizon" in blob
    assert "presence_simulator_start" in blob
    assert "presence_simulator_bedtime" in blob


def test_loop_script_skips_empty_or_unavailable_group(package):
    blob = _script_blob(package)
    assert "light.presence_simulator_lights" in blob
    assert "selectattr" in blob
    assert "on" in blob and "off" in blob
    assert "count" in blob


def test_loop_script_fixes_min_ge_max_wait(package):
    blob = _script_blob(package)
    assert "presence_simulator_min_minutes" in blob
    assert "presence_simulator_max_minutes" in blob
    assert "min + 1" in blob


def test_loop_script_does_not_hardcode_household_lights(package):
    blob = _script_blob(package)
    assert "light.presence_simulator_lights" in blob
    assert "light.living_room" not in blob
    assert "light.kitchen" not in blob
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
python -m pytest tests/test_presence_simulator_package.py::test_loop_script_is_abortable tests/test_presence_simulator_package.py::test_loop_script_gates_on_switch_and_same_day_window tests/test_presence_simulator_package.py::test_loop_script_skips_empty_or_unavailable_group tests/test_presence_simulator_package.py::test_loop_script_fixes_min_ge_max_wait tests/test_presence_simulator_package.py::test_loop_script_does_not_hardcode_household_lights -v
```

Expected: FAIL with `KeyError: 'script'` (or missing `presence_simulator_loop`).

- [ ] **Step 3: Add the loop script**

Append this exact block to `packages/presence_simulator.yaml` (keep the Task 1 helpers above it):

```yaml
script:
  presence_simulator_loop:
    alias: Presence simulator loop
    mode: restart
    sequence:
      - repeat:
          while:
            - condition: template
              value_template: >
                {% set use_sunset = is_state('input_boolean.presence_simulator_use_sunset', 'on') %}
                {% set bedtime = states('input_datetime.presence_simulator_bedtime') %}
                {% set start = states('input_datetime.presence_simulator_start') %}
                {% set now_t = now().strftime('%H:%M:%S') %}
                {% set after_start = is_state('sun.sun', 'below_horizon') if use_sunset else (now_t >= start) %}
                {% set before_bed = now_t < bedtime %}
                {{ is_state('input_boolean.presence_simulator', 'on')
                   and after_start and before_bed }}
          sequence:
            - variables:
                members: >
                  {{
                    expand('light.presence_simulator_lights')
                    | selectattr('state', 'in', ['on', 'off'])
                    | map(attribute='entity_id')
                    | list
                  }}
                wait_minutes: >
                  {% set min = states('input_number.presence_simulator_min_minutes') | int(5) %}
                  {% set max = states('input_number.presence_simulator_max_minutes') | int(25) %}
                  {% if max <= min %}
                    {% set max = min + 1 %}
                  {% endif %}
                  {{ range(min, max + 1) | random }}
            - if:
                - condition: template
                  value_template: "{{ members | count > 0 }}"
              then:
                - variables:
                    target_light: "{{ members | random }}"
                    want_on: "{{ [true, false] | random }}"
                - if:
                    - condition: template
                      value_template: "{{ want_on }}"
                  then:
                    - action: light.turn_on
                      target:
                        entity_id: "{{ target_light }}"
                  else:
                    - action: light.turn_off
                      target:
                        entity_id: "{{ target_light }}"
            - delay:
                minutes: "{{ wait_minutes | int }}"
```

Empty or all-unavailable group: `members | count` is 0, so no `light.turn_*` runs; the delay still happens and the while condition is rechecked. Single member is allowed (`members | random` on a one-item list).

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_presence_simulator_package.py -v
```

Expected: PASS (all Task 1 and Task 2 tests).

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py packages/presence_simulator.yaml
git commit -m "feat: add abortable presence simulator loop script"
```

---

### Task 3: Start and stop automations

**Files:**
- Modify: `tests/test_presence_simulator_package.py` (append automation tests)
- Modify: `packages/presence_simulator.yaml` (add `automation:` list)

**Interfaces:**
- Consumes: `script.presence_simulator_loop` and the Task 1 helpers.
- Produces: six automations with the Global Constraints `id` values. Start automations call `script.turn_on` on `script.presence_simulator_loop` only when the switch is on and the matching window applies. Stop automations call `script.turn_off` on that script and `light.turn_off` on `light.presence_simulator_lights` only.

- [ ] **Step 1: Write the failing automation tests**

Append to `tests/test_presence_simulator_package.py`:

```python
REQUIRED_AUTOMATION_IDS = {
    "presence_simulator_start_sunset",
    "presence_simulator_start_time",
    "presence_simulator_start_on_switch",
    "presence_simulator_resume_on_start",
    "presence_simulator_stop_bedtime",
    "presence_simulator_stop_on_switch",
}


def _automations(package):
    items = package["automation"]
    assert isinstance(items, list)
    return {item["id"]: item for item in items}


def test_required_automations_exist(package):
    assert REQUIRED_AUTOMATION_IDS == set(_automations(package))


def test_start_automations_only_run_script_when_switch_on(package):
    autos = _automations(package)
    for key in (
        "presence_simulator_start_sunset",
        "presence_simulator_start_time",
        "presence_simulator_start_on_switch",
        "presence_simulator_resume_on_start",
    ):
        blob = yaml_dump_section(autos[key])
        assert "input_boolean.presence_simulator" in blob
        assert "script.presence_simulator_loop" in blob
        assert "script.turn_on" in blob
        assert "light.turn_off" not in blob


def test_sunset_start_requires_use_sunset(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_start_sunset"])
    assert "sunset" in blob
    assert "presence_simulator_use_sunset" in blob


def test_fixed_start_requires_use_sunset_off(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_start_time"])
    assert "presence_simulator_start" in blob
    assert "presence_simulator_use_sunset" in blob


def test_switch_and_restart_gate_on_window(package):
    for key in (
        "presence_simulator_start_on_switch",
        "presence_simulator_resume_on_start",
    ):
        blob = yaml_dump_section(_automations(package)[key])
        assert "below_horizon" in blob
        assert "presence_simulator_bedtime" in blob


def test_stop_automations_abort_script_and_turn_group_off(package):
    autos = _automations(package)
    bedtime = yaml_dump_section(autos["presence_simulator_stop_bedtime"])
    switch_off = yaml_dump_section(autos["presence_simulator_stop_on_switch"])
    assert "presence_simulator_bedtime" in bedtime
    assert "script.turn_off" in bedtime and "light.turn_off" in bedtime
    assert "script.presence_simulator_loop" in bedtime
    assert "light.presence_simulator_lights" in bedtime
    assert "script.turn_off" in switch_off and "light.turn_off" in switch_off
    assert "light.presence_simulator_lights" in switch_off
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
python -m pytest tests/test_presence_simulator_package.py::test_required_automations_exist -v
```

Expected: FAIL with `KeyError: 'automation'`.

- [ ] **Step 3: Add the automations**

Append this exact block to `packages/presence_simulator.yaml`:

```yaml
automation:
  - id: presence_simulator_start_sunset
    alias: Presence simulator start at sunset
    trigger:
      - trigger: sun
        event: sunset
    condition:
      - condition: state
        entity_id: input_boolean.presence_simulator
        state: "on"
      - condition: state
        entity_id: input_boolean.presence_simulator_use_sunset
        state: "on"
      - condition: template
        value_template: >
          {{ now().strftime('%H:%M:%S') < states('input_datetime.presence_simulator_bedtime') }}
    action:
      - action: script.turn_on
        target:
          entity_id: script.presence_simulator_loop

  - id: presence_simulator_start_time
    alias: Presence simulator start at start time
    trigger:
      - trigger: time
        at: input_datetime.presence_simulator_start
    condition:
      - condition: state
        entity_id: input_boolean.presence_simulator
        state: "on"
      - condition: state
        entity_id: input_boolean.presence_simulator_use_sunset
        state: "off"
      - condition: template
        value_template: >
          {{ now().strftime('%H:%M:%S') < states('input_datetime.presence_simulator_bedtime') }}
    action:
      - action: script.turn_on
        target:
          entity_id: script.presence_simulator_loop

  - id: presence_simulator_start_on_switch
    alias: Presence simulator start on switch
    trigger:
      - trigger: state
        entity_id: input_boolean.presence_simulator
        to: "on"
    condition:
      - condition: template
        value_template: >
          {% set use_sunset = is_state('input_boolean.presence_simulator_use_sunset', 'on') %}
          {% set bedtime = states('input_datetime.presence_simulator_bedtime') %}
          {% set start = states('input_datetime.presence_simulator_start') %}
          {% set now_t = now().strftime('%H:%M:%S') %}
          {% set after_start = is_state('sun.sun', 'below_horizon') if use_sunset else (now_t >= start) %}
          {{ after_start and now_t < bedtime }}
    action:
      - action: script.turn_on
        target:
          entity_id: script.presence_simulator_loop

  - id: presence_simulator_resume_on_start
    alias: Presence simulator resume after restart
    trigger:
      - trigger: homeassistant
        event: start
    condition:
      - condition: state
        entity_id: input_boolean.presence_simulator
        state: "on"
      - condition: template
        value_template: >
          {% set use_sunset = is_state('input_boolean.presence_simulator_use_sunset', 'on') %}
          {% set bedtime = states('input_datetime.presence_simulator_bedtime') %}
          {% set start = states('input_datetime.presence_simulator_start') %}
          {% set now_t = now().strftime('%H:%M:%S') %}
          {% set after_start = is_state('sun.sun', 'below_horizon') if use_sunset else (now_t >= start) %}
          {{ after_start and now_t < bedtime }}
    action:
      - action: script.turn_on
        target:
          entity_id: script.presence_simulator_loop

  - id: presence_simulator_stop_bedtime
    alias: Presence simulator stop at bedtime
    trigger:
      - trigger: time
        at: input_datetime.presence_simulator_bedtime
    action:
      - action: script.turn_off
        target:
          entity_id: script.presence_simulator_loop
      - action: light.turn_off
        target:
          entity_id: light.presence_simulator_lights

  - id: presence_simulator_stop_on_switch
    alias: Presence simulator stop on switch
    trigger:
      - trigger: state
        entity_id: input_boolean.presence_simulator
        to: "off"
    action:
      - action: script.turn_off
        target:
          entity_id: script.presence_simulator_loop
      - action: light.turn_off
        target:
          entity_id: light.presence_simulator_lights
```

After bedtime, `presence_simulator_start_on_switch` fails the window template, so the loop does not start. Resume-on-start uses the same gate and does not turn lights on.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_presence_simulator_package.py -v
```

Expected: PASS (all tests so far).

- [ ] **Step 5: Commit**

```bash
git add tests/test_presence_simulator_package.py packages/presence_simulator.yaml
git commit -m "feat: start and stop presence simulator from schedule and switch"
```

---

### Task 4: README install and smoke test

**Files:**
- Create: `README.md`
- Modify: `tests/test_presence_simulator_package.py` (append README tests)

**Interfaces:**
- Consumes: entity IDs and automation behaviour from Tasks 1–3.
- Produces: `README.md` that documents the `packages:` include, creating `light.presence_simulator_lights`, helper defaults, and the 5-minute smoke test from the spec.

- [ ] **Step 1: Write the failing README tests**

Append to `tests/test_presence_simulator_package.py`:

```python
def test_readme_covers_install_and_smoke_test():
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "packages" in text
    assert "include_dir_named" in text
    assert "presence simulator lights" in text
    assert "helpers" in text
    assert "switch on" in text or "presence simulator" in text
    assert "switch off" in text
    assert "grouped light" in text or "group" in text
```

- [ ] **Step 2: Run the README test to verify it fails**

Run:

```bash
python -m pytest tests/test_presence_simulator_package.py::test_readme_covers_install_and_smoke_test -v
```

Expected: FAIL with `FileNotFoundError` for `README.md`.

- [ ] **Step 3: Write README.md**

Create `README.md`:

```markdown
# Home Assistant presence simulator

Evening light schedule plus a manual presence simulator. While **Presence simulator** is on, Home Assistant randomly turns lights in one group on and off from sunset (or a start time you set) until bedtime, then turns that group off.

## Install

1. Copy `packages/presence_simulator.yaml` into your Home Assistant `config/packages/` folder.
2. If packages are not enabled, add this to `configuration.yaml` (this repo already has it):

```yaml
homeassistant:
  packages: !include_dir_named packages
```

3. Restart Home Assistant (or reload YAML).
4. Create the light group in the UI:
   - Settings → Devices & services → Helpers → Create helper → Group → Light group
   - Name: `Presence simulator lights` (entity ID must be `light.presence_simulator_lights`)
   - Add the lights you want simulated. Do not add lights you do not want changed.
5. Open the **Presence simulator use sunset** helper and turn it **on** (recommended). If you prefer a fixed start, leave it off and set **Presence simulator start** (default 18:00).
6. Set **Presence simulator bedtime** (default 23:00, same calendar evening). Set min/max minutes between changes if you want (defaults 5 and 25).

## Helpers

| Entity | Default | Purpose |
| --- | --- | --- |
| `input_boolean.presence_simulator` | off | Master switch |
| `input_boolean.presence_simulator_use_sunset` | off until you enable it | Start at sunset when on |
| `input_datetime.presence_simulator_start` | 18:00 after you set it | Fixed start when sunset is off |
| `input_datetime.presence_simulator_bedtime` | 23:00 after you set it | All grouped lights off |
| `input_number.presence_simulator_min_minutes` | 5 | Minimum wait |
| `input_number.presence_simulator_max_minutes` | 25 | Maximum wait |
| `light.presence_simulator_lights` | created in Helpers | Only lights this package changes |

`input_datetime` helpers do not keep a YAML default after first create — set 18:00 and 23:00 once in the UI if they are empty. Bedtime must be later the same local day than the start (no overnight windows).

## 5-minute smoke test

1. Put at least one real light in **Presence simulator lights**.
2. Set start a minute or two in the past (or wait until after sunset if Use sunset is on) and bedtime later tonight.
3. Turn **Presence simulator** **on**. A grouped light should change within the min/max window (for a quick test, set min and max to 1).
4. Turn **Presence simulator** **off**. Every light in the group should turn off.
5. Lights that are not in the group must stay as you left them.

If the group is empty, nothing is toggled. If a member is unavailable, it is skipped.
```

- [ ] **Step 4: Run all tests**

Run:

```bash
python -m pytest tests/test_presence_simulator_package.py -v
```

Expected: PASS (full suite, including README).

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_presence_simulator_package.py
git commit -m "docs: explain presence simulator install and smoke test"
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
| --- | --- |
| Manual switch only | Task 1 helpers + Task 3 start conditions |
| Configurable light group, no hardcoded household IDs | Task 2 script + tests; Task 4 README helper |
| Evening window sunset or start → bedtime, same day | Task 2 while-template; Task 3 start/stop |
| Random on/off + random wait | Task 2 script |
| All group lights off at bedtime or switch off | Task 3 stop automations |
| Restart resume only inside window | Task 3 `presence_simulator_resume_on_start` |
| Empty group no-op; skip unavailable; min ≥ max → min+1 | Task 2 script + template tests |
| YAML parse + entity contract | Tasks 1–3 tests |
| README install + 5-minute test | Task 4 |
| `configuration.yaml` packages include | Task 1 |

No second subsystem. No placeholders. Entity IDs match the spec and are repeated consistently across tasks.
