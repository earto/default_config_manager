"""Init for Default Config Manager."""

from __future__ import annotations

import json
import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform, EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers import (
    config_validation as cv,
    issue_registry as ir,
    device_registry as dr
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DOMAIN, CONF_ADVANCED_MODE, MODE_1, MODE_2, MODE_3
from .helpers import get_static_integrations

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

def _create_restart_issue(hass: HomeAssistant) -> None:
    """Create restart issue."""
    ir.async_create_issue(
        hass, DOMAIN, "restart_required", is_fixable=True,
        severity=ir.IssueSeverity.WARNING, translation_key="restart_required"
    )

def _delete_restart_issue(hass: HomeAssistant) -> None:
    """Delete restart issue."""
    ir.async_delete_issue(hass, DOMAIN, "restart_required")

async def _async_sync_manifest(hass: HomeAssistant, entry: ConfigEntry, mode_code: int) -> None:
    """Sync dependencies to manifest.json."""
    try:
        core_default_config = await async_get_integration(hass, "default_config")
        factory_deps = core_default_config.dependencies
        disabled = []
        if mode_code == MODE_3:
            components = await get_static_integrations(hass)
            dr_inst = dr.async_get(hass)
            for comp in components:
                dev = dr_inst.async_get_device({(DOMAIN, f"{entry.entry_id}_{comp}")})
                if dev and dev.disabled_by:
                    disabled.append(comp)
        
        target = [d for d in factory_deps if d not in disabled]
        path = hass.config.path("custom_components", "default_config_manager", "manifest.json")
        
        def write():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if set(data.get("dependencies", [])) != set(target):
                _LOGGER.info("Syncing manifest: %s", target)
                data["dependencies"] = target
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
        
        await hass.async_add_executor_job(write)
    except Exception as e:
        _LOGGER.error("Manifest sync failed: %s", e)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setup integration."""
    hass.data.setdefault(DOMAIN, {})
    _delete_restart_issue(hass)
    
    yaml_enabled = "default_config" in hass.config.components
    components = await get_static_integrations(hass)
    advanced = False
    disabled = []
    
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.options.get(CONF_ADVANCED_MODE, False):
            advanced = True
            dr_inst = dr.async_get(hass)
            for comp in components:
                dev = dr_inst.async_get_device({(DOMAIN, f"{entry.entry_id}_{comp}")})
                if dev and dev.disabled_by:
                    disabled.append(comp)
    
    mode = MODE_1 if yaml_enabled else (MODE_3 if advanced else MODE_2)
    hass.data[DOMAIN].update({"mode_code": mode, "disabled": disabled})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    mode = hass.data[DOMAIN]["mode_code"]

    if mode != MODE_1:
        async def sync(_): await _async_sync_manifest(hass, entry, mode)
        
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, sync)
        entry.async_on_unload(hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, sync))
        entry.async_on_unload(hass.bus.async_listen("core_update_finished", sync))
        
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    mode = MODE_3 if entry.options.get(CONF_ADVANCED_MODE, False) else MODE_2
    await _async_sync_manifest(hass, entry, mode)
    _create_restart_issue(hass)
    await hass.config_entries.async_reload(entry.entry_id)
