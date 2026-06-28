"""Helper functions for the Default Config Manager integration."""

from __future__ import annotations

import json
from pathlib import Path
import logging

import homeassistant.components as ha_components

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


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
        _LOGGER.error(
            "Failed to load default_config manifest for %s: %s", DOMAIN, err
        )
        return []
