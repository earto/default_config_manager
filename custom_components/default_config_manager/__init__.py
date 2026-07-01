"""Init for Default Config Manager."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.loader import async_get_integration

from .const import (
    DOMAIN,
    CONF_ADVANCED_MODE,
    CONF_COMPONENTS_TO_DISABLE,
    MODE_1,
    MODE_2,
    MODE_3,
)
from .helpers import get_static_integrations, get_conditional_integrations
from .repairs import create_integration_change_issue, clear_integration_change_issue

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Default Config Manager from a config entry."""
    entry._hass = hass
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # YAML detection
    if "default_config" in hass.config.components:
        hass.data.setdefault(DOMAIN, {})["yaml_config"] = True

    yaml_config = hass.data.setdefault(DOMAIN, {}).get("yaml_config", False)

    static_integrations = await get_static_integrations(hass)
    conditional_integrations = await get_conditional_integrations(hass)

    advanced_mode = entry.options.get(CONF_ADVANCED_MODE, False)
    disabled_components = entry.options.get(CONF_COMPONENTS_TO_DISABLE, [])

    # Mode detection
    if yaml_config:
        mode_code = MODE_1
    elif advanced_mode:
        mode_code = MODE_3
    else:
        mode_code = MODE_2

    if mode_code == MODE_1:
        return True

    if mode_code == MODE_2:
        return True

    if mode_code == MODE_3:
        # Apply enable/disable logic
        for component in static_integrations:

            # Disable component
            if component in disabled_components:
                clear_integration_change_issue(hass, component)

                # Remove from active components if present
                if component in hass.config.components:
                    hass.config.components.remove(component)
                    create_integration_change_issue(hass, component, "disabled")

            # Enable component
            else:
                if component not in hass.config.components:
                    clear_integration_change_issue(hass, component)

                    result = await async_setup_component(hass, component, {})
                    if result:
                        create_integration_change_issue(hass, component, "enabled")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Default Config Manager config entry."""
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
