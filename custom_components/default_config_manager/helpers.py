"""Helper functions for the Default Config Manager integration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import homeassistant.components as ha_components

_LOGGER = logging.getLogger(__name__)


async def get_static_integrations(hass) -> List[str]:
    """Return the list of static default_config integrations."""
    try:
        components_path = (
            Path(ha_components.__file__).resolve().parent
            / "default_config"
            / "manifest.json"
        )

        with components_path.open(encoding="utf-8") as f:
            data = json.load(f)
            return sorted(data.get("dependencies", []))

    except Exception as err:
        _LOGGER.error("Failed to load default_config manifest: %s", err)
        return []


async def get_conditional_integrations(hass) -> List[str]:
    """Return conditional integrations enabled indirectly by default_config."""
    static_components = await get_static_integrations(hass)
    running_components = list(hass.config.components)

    return sorted(
        component
        for component in running_components
        if component not in static_components
    )
