"""Helper functions for the Default Config Manager integration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import homeassistant.components as ha_components

from .const import DOMAIN, LOGGER_PREFIX

_LOGGER = logging.getLogger(__name__)

# Discovery-based integrations that can load conditional integrations
DISCOVERY_PARENTS = {
    "zeroconf",
    "ssdp",
    "usb",
    "cloud",
    "mobile_app",
    "energy",
}


def get_default_config_components() -> list[str]:
    """Return a list of components included in Home Assistant's default_config."""
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
    """Return conditional integrations loaded indirectly by default_config.

    Conditional integrations are:
    - running
    - NOT static default_config components
    - AND likely loaded by discovery parents (zeroconf, ssdp, usb, cloud, mobile_app, energy)
    """

    conditional = []

    for component in running_components:
        # Skip static default_config integrations
        if component in static_components:
            continue

        # If any discovery parent is running, this component may have been loaded by it
        if any(parent in running_components for parent in DISCOVERY_PARENTS):
            conditional.append(component)

    return sorted(conditional)
