from pathlib import Path

from conftest import (
    AUTOMATIONS_PATH,
    COMPOSE_PATH,
    CONFIG_PATH,
    CUSTOMIZE_PATH,
    DASHBOARD_PATH,
    GROUPS_PATH,
    PACKAGE_PATH,
    SCENES_PATH,
    SCRIPTS_PATH,
    SECRETS_PATH,
    UI_LOVELACE_PATH,
    load_configuration,
)


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
    assert DASHBOARD_PATH.is_file()
    assert UI_LOVELACE_PATH.is_file()
    assert AUTOMATIONS_PATH.is_file()
    assert SCRIPTS_PATH.is_file()
    assert SCENES_PATH.is_file()
    assert SECRETS_PATH.is_file()
    assert GROUPS_PATH.is_file()
    assert CUSTOMIZE_PATH.is_file()
    assert COMPOSE_PATH.is_file()
    assert (ROOT / "requirements-dev.txt").is_file()
    assert (ROOT / "requirements-dev.txt").is_file()


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


def test_loop_script_targets_light_group_members_not_the_group(package):
    """Light groups are a single light entity; expand('light.group') returns
    the group itself, so turn_off would kill every member at once."""
    blob = _script_blob(package)
    assert "state_attr" in blob
    assert "entity_id" in blob
    assert "expand('light.presence_simulator_lights')" not in blob
    assert "ne" in blob
    assert "light.presence_simulator_lights" in blob


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


REQUIRED_AUTOMATION_IDS = {
    "presence_simulator_start_sunset",
    "presence_simulator_start_time",
    "presence_simulator_start_on_switch",
    "presence_simulator_resume_on_start",
    "presence_simulator_stop_bedtime",
    "presence_simulator_stop_on_switch",
}

AUTO_AWAY_AUTOMATION_IDS = {
    "presence_simulator_auto_away_evaluate",
    "presence_simulator_manual_off_while_away",
    "presence_simulator_confirm_off_correct",
    "presence_simulator_confirm_off_mistake",
    "presence_simulator_distance_unit_convert",
}


def _automations(package):
    items = package["automation"]
    assert isinstance(items, list)
    return {item["id"]: item for item in items}


def test_required_automations_exist(package):
    assert REQUIRED_AUTOMATION_IDS | AUTO_AWAY_AUTOMATION_IDS == set(_automations(package))


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


def test_stop_on_switch_skips_group_off_when_quiet_off(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_stop_on_switch"])
    assert "input_boolean.presence_simulator_quiet_off" in blob
    assert "script.turn_off" in blob
    assert "light.turn_off" in blob
    assert "light.presence_simulator_lights" in blob


def test_configuration_registers_presence_simulator_sidebar():
    config = load_configuration()
    assert config["lovelace"]["mode"] == "yaml"
    dash = config["lovelace"]["dashboards"]["presence-simulator"]
    assert dash["mode"] == "yaml"
    assert dash["title"] == "Presence simulator"
    assert dash["show_in_sidebar"] is True
    assert dash["filename"] == "presence-simulator.yaml"
    assert config["automation"] == "automations.yaml"
    assert config["script"] == "scripts.yaml"
    assert config["scene"] == "scenes.yaml"
    assert config["group"] == "groups.yaml"
    assert config["homeassistant"]["customize"] == "customize.yaml"


def test_presence_simulator_dashboard_shows_start_and_bedtime():
    import yaml

    for path in (DASHBOARD_PATH, UI_LOVELACE_PATH):
        assert path.is_file()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "views" in data
        blob = yaml.safe_dump(data, sort_keys=False)
        assert "input_datetime.presence_simulator_start" in blob
        assert "input_datetime.presence_simulator_bedtime" in blob


def test_readme_covers_install_and_smoke_test():
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "packages" in text
    assert "include_dir_named" in text
    assert "presence simulator lights" in text
    assert "helpers" in text
    assert "switch on" in text or "presence simulator" in text
    assert "switch off" in text
    assert "grouped light" in text or "group" in text
    assert "sidebar" in text
    assert "presence simulator start" in text
    assert "presence simulator bedtime" in text


def test_package_defines_auto_away_helpers(package):
    booleans = package["input_boolean"]
    assert "presence_simulator_auto_away" in booleans
    assert booleans["presence_simulator_auto_away"]["name"] == "Auto away"
    assert "presence_simulator_auto_holdoff" in booleans
    assert "presence_simulator_quiet_off" in booleans
    assert "presence_simulator_confirm_off_pending" in booleans
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
    ask = package["input_select"]["presence_simulator_ask_if_off_while_away"]
    assert ask["name"] == "Ask if off while away"
    assert ask["options"] == ["Phone", "Home Assistant", "Both"]
    assert ask["initial"] == "Both"
    buttons = package["input_button"]
    assert "presence_simulator_off_correct" in buttons
    assert "presence_simulator_off_mistake" in buttons


def test_auto_away_evaluate_uses_distance_and_all_persons(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_auto_away_evaluate"])
    assert "states.person" in blob
    assert "zone.home" in blob
    assert "distance(" in blob
    assert "1.609344" in blob
    assert "presence_simulator_distance_unit" in blob
    assert "Miles (mi)" in blob
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


def test_manual_off_while_away_asks_correct_or_mistake(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_manual_off_while_away"])
    assert "presence_simulator_confirm_off_pending" in blob
    assert "presence_simulator_ask_if_off_while_away" in blob
    assert "notify.notify" in blob
    assert "continue_on_error" in blob
    assert "persistent_notification.create" in blob
    assert "presence_simulator_off_while_away" in blob
    assert "PRESENCE_SIMULATOR_OFF_CORRECT" in blob
    assert "PRESENCE_SIMULATOR_OFF_MISTAKE" in blob
    assert "Phone" in blob
    assert "Home Assistant" in blob
    assert "notify.mobile_app_" not in blob
    assert "states.person" in blob
    assert "1.609344" in blob
    assert "presence_simulator_distance_unit" in blob
    assert "Miles (mi)" in blob


def test_confirm_off_correct_sets_holdoff(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_confirm_off_correct"])
    assert "PRESENCE_SIMULATOR_OFF_CORRECT" in blob
    assert "presence_simulator_off_correct" in blob
    assert "from_state" in blob
    assert "presence_simulator_auto_holdoff" in blob
    assert "presence_simulator_confirm_off_pending" in blob
    assert "presence_simulator_off_while_away" in blob


def test_confirm_off_mistake_turns_simulator_back_on(package):
    blob = yaml_dump_section(_automations(package)["presence_simulator_confirm_off_mistake"])
    assert "PRESENCE_SIMULATOR_OFF_MISTAKE" in blob
    assert "presence_simulator_off_mistake" in blob
    assert "from_state" in blob
    assert "input_boolean.presence_simulator" in blob
    assert "presence_simulator_confirm_off_pending" in blob


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


def test_dashboard_shows_auto_away_controls_not_internals():
    import yaml

    for path in (DASHBOARD_PATH, UI_LOVELACE_PATH, ROOT / "dashboards" / "presence_simulator.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        blob = yaml.safe_dump(data, sort_keys=False)
        assert "input_boolean.presence_simulator_auto_away" in blob
        assert "Auto away" in blob
        assert "input_number.presence_simulator_away_miles" in blob
        assert "Away distance" in blob
        assert "Away distance (miles)" not in blob
        assert "input_select.presence_simulator_distance_unit" in blob
        assert "Distance unit" in blob
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
    assert "distance unit" in text
    assert "kilometers (km)" in text or "kilometres (km)" in text
    assert "miles (mi)" in text
