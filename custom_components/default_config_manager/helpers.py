"""Helper functions for the Default Config Manager integration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import homeassistant.components as ha_components

from .const import DOMAIN, LOGGER_PREFIX

_LOGGER = logging.getLogger(__name__)


def get_default_config_components() -> list[str]:
    """Return a list of components included in Home Assistant's default_config.

    This is dynamically loaded from HA's own manifest so it always stays
    perfectly aligned with Home Assistant's behaviour.
    """
    try:
        components_path = (
            Path(ha_components.__file__).resolve().parent
            / "default_config"
            / "manifest.json"
        )

        with components_path.open(encoding="utf-8") as f:
            data = json.load(f)
            return data.get("dependencies", [])

    except Exception as err:
        _LOGGER.error("%s: Failed to load default_config manifest: %s", LOGGER_PREFIX, err)
        return []


def get_conditional_integrations(
    running_components: List[str],
    static_components: List[str],
) -> List[str]:
    """Return conditional integrations enabled indirectly by default_config.

    Conditional integrations are:
    - running
    - NOT static default_config integrations

    This definition is fully dynamic and automatically adapts to changes in
    Home Assistant's discovery behaviour without requiring code updates.
    """

    return sorted(
        component
        for component in running_components
        if component not in static_components
    )
