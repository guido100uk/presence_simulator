from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "packages" / "presence_simulator.yaml"
CONFIG_PATH = ROOT / "configuration.yaml"
DASHBOARD_PATH = ROOT / "presence-simulator.yaml"
UI_LOVELACE_PATH = ROOT / "ui-lovelace.yaml"
AUTOMATIONS_PATH = ROOT / "automations.yaml"
SCRIPTS_PATH = ROOT / "scripts.yaml"
SCENES_PATH = ROOT / "scenes.yaml"
SECRETS_PATH = ROOT / "secrets.yaml"
GROUPS_PATH = ROOT / "groups.yaml"
CUSTOMIZE_PATH = ROOT / "customize.yaml"
COMPOSE_PATH = ROOT / "docker-compose.yml"


def _ignore_include(loader, node):
    return str(loader.construct_scalar(node))


def load_package() -> dict:
    return yaml.safe_load(PACKAGE_PATH.read_text(encoding="utf-8"))


def load_configuration() -> dict:
    loader = yaml.SafeLoader
    loader.add_constructor("!include_dir_named", _ignore_include)
    loader.add_constructor("!include", _ignore_include)
    return yaml.load(CONFIG_PATH.read_text(encoding="utf-8"), Loader=loader)


@pytest.fixture
def package() -> dict:
    return load_package()
