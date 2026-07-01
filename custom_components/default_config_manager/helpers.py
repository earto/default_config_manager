"""Helpers for Default Config Manager."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import homeassistant.components as ha_components
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def _load_default_config_dependencies(components_path: Path) -> List[str]:
    """Synchronous helper to read default_config manifest."""
    try:
        with components_path.open(encoding="utf-8") as f:
            data = json.load(f)
            return sorted(data.get("dependencies", []))
    except Exception as err:
        _LOGGER.error("Failed to load default_config manifest: %s", err)
        return []


async def get_static_integrations(hass: HomeAssistant) -> List[str]:
    """Return the list of static default_config integrations."""
    components_path = (
        Path(ha_components.__file__).resolve().parent
        / "default_config"
        / "manifest.json"
    )

    return await hass.async_add_executor_job(
        _load_default_config_dependencies,
        components_path,
    )


async def get_conditional_integrations(hass: HomeAssistant) -> List[str]:
    """Return conditional integrations enabled indirectly by default_config."""
    static_components = await get_static_integrations(hass)
    running_components = list(hass.config.components)

    return sorted(
        component
        for component in running_components
        if component not in static_components
    )


async def get_default_config_version(hass: HomeAssistant) -> str:
    """Return the version of HA's default_config integration."""
    try:
        # default_config is a core integration; read its manifest directly
        components_path = (
            Path(ha_components.__file__).resolve().parent
            / "default_config"
            / "manifest.json"
        )
        with components_path.open(encoding="utf-8") as f:
            data = json.load(f)
            return data.get("version", "unknown")
    except Exception as err:
        _LOGGER.error("Failed to read default_config version: %s", err)
        return "unknown"
