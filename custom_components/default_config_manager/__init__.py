"""Init for Default Config Manager."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import homeassistant.components.default_config as ha_default_config
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers import (
    config_validation as cv, 
    issue_registry as ir, 
    device_registry as dr, 
    repairs
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component

from .const import (
    DOMAIN,
    CONF_ADVANCED_MODE,
    MODE_1,
    MODE_2,
    MODE_3,
)
from .helpers import get_static_integrations

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


# --- Repair Flow Handling ---

class RestartRequiredFlow(repairs.RepairsFlow):
    """Handler for an issue requiring a restart."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Handle the initialization step."""
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None):
        """Handle the confirmation step."""
        if user_input is not None:
            # Trigger the actual restart
            await self.hass.services.async_call("homeassistant", "restart")
            return self.async_create_entry(data={})

        return self.async_show_form(step_id="confirm")


def _create_restart_issue(hass: HomeAssistant) -> None:
    """Create the restart required issue."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        "restart_required",
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="restart_required",
    )


def _delete_restart_issue(hass: HomeAssistant) -> None:
    """Delete the restart required issue."""
    ir.async_delete_issue(hass, DOMAIN, "restart_required")


# --- Setup Logic ---

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Default Config Manager integration."""
    _LOGGER.debug("Setting up Default Config Manager")

    # Register the repair flow
    repairs.async_register_repairs_flow(
        hass, DOMAIN, "restart_required", RestartRequiredFlow
    )
    _delete_restart_issue(hass)

    yaml_config_enabled = "default_config" in hass.config.components
    components = await get_static_integrations(hass)
    
    advanced_mode = False
    disabled_components: list[str] = []

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.options.get(CONF_ADVANCED_MODE, False):
            advanced_mode = True
            device_registry = dr.async_get(hass)
            for component in components:
                device = device_registry.async_get_device(
                    identifiers={(DOMAIN, f"{entry.entry_id}_{component}")}
                )
                if device and device.disabled_by:
                    disabled_components.append(component)

    mode_code = MODE_1 if yaml_config_enabled else (MODE_3 if advanced_mode else MODE_2)
    _LOGGER.info("Default Config Manager running in mode_code=%s", mode_code)

    if mode_code == MODE_1:
        return True

    enabled_components = components if mode_code == MODE_2 else [
        c for c in components if c not in disabled_components
    ]
    
    setup_tasks = [async_setup_component(hass, c, config) for c in enabled_components]
    if setup_tasks:
        await asyncio.gather(*setup_tasks)

    await ha_default_config.async_setup(hass, config)
    return True


# --- Entry Point Handling ---

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Options updated. Creating restart issue.")
    _create_restart_issue(hass)
    await hass.config_entries.async_reload(entry.entry_id)
