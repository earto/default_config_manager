"""Init for Default Config Manager."""

from __future__ import annotations

import asyncio
import logging
import json
import os

import homeassistant.components.default_config as ha_default_config
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform, EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers import (
    config_validation as cv, 
    issue_registry as ir, 
    device_registry as dr
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component
from homeassistant.loader import async_get_integration

from .const import DOMAIN, CONF_ADVANCED_MODE, MODE_1, MODE_2, MODE_3
from .helpers import get_static_integrations

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

def _create_restart_issue(hass: HomeAssistant) -> None:
    """Create the restart required issue."""
    ir.async_create_issue(hass, DOMAIN, "restart_required", is_fixable=True,
        severity=ir.IssueSeverity.WARNING, translation_key="restart_required")

def _delete_restart_issue(hass: HomeAssistant) -> None:
    """Delete the restart required issue."""
    ir.async_delete_issue(hass, DOMAIN, "restart_required")

async def _async_sync_manifest(hass: HomeAssistant, entry: ConfigEntry, mode_code: int) -> bool:
    """Silent-healer: sync dependencies to manifest.json. Returns True if changed."""
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
        
        def write() -> bool:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            current_deps = data.get("dependencies", [])
            if set(current_deps) != set(target):
                _LOGGER.info("DCM Manifest Sync: Updating dependencies to: %s", target)
                data["dependencies"] = target
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return True # We made a change
            return False # No change needed
        
        return await hass.async_add_executor_job(write)
    except Exception as e:
        _LOGGER.error("Manifest sync failed: %s", e)
        return False

# --- Setup Logic ---

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Default Config Manager integration."""
    _LOGGER.debug("Setting up Default Config Manager")
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
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["mode_code"] = mode_code

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
    
    # 1. Silent-healer boot-time registration (Never triggers restart nag)
    async def sync_on_boot(_): 
        await _async_sync_manifest(hass, entry, hass.data[DOMAIN].get("mode_code", MODE_2))
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, sync_on_boot)
    
    # 2. Manual toggle listener (Triggers restart nag ONLY if a DCM device was toggled)
    async def sync_on_registry_change(event):
        # Filter for actual 'disabled_by' toggle events
        if event.data.get("action") == "update" and "disabled_by" in event.data.get("changes", {}):
            device_id = event.data.get("device_id")
            device_registry = dr.async_get(hass)
            device = device_registry.async_get(device_id)
            
            # If the toggled device belongs to DCM and we are in Mode 3
            if device and entry.entry_id in device.config_entries:
                current_mode = hass.data[DOMAIN].get("mode_code", MODE_2)
                if current_mode == MODE_3:
                    changed = await _async_sync_manifest(hass, entry, current_mode)
                    if changed:
                        _LOGGER.debug("DCM device toggled. Creating restart issue.")
                        _create_restart_issue(hass)

    entry.async_on_unload(hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, sync_on_registry_change))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Options updated. Processing state transitions.")
    
    old_advanced = hass.data[DOMAIN].get("mode_code") == MODE_3
    new_advanced = entry.options.get(CONF_ADVANCED_MODE, False)
    
    # Mode 3 -> Mode 2 cleanup
    if old_advanced and not new_advanced:
        _LOGGER.debug("Transitioning to Basic Mode: Clearing disabled proxy states.")
        await _async_enable_all_proxy_devices(hass, entry)
        
    mode = MODE_3 if new_advanced else MODE_2
    hass.data[DOMAIN]["mode_code"] = mode 
    
    # Only nag if the manifest actually changed
    changed = await _async_sync_manifest(hass, entry, mode)
    if changed:
        _LOGGER.debug("Manifest changed during options update. Creating restart issue.")
        _create_restart_issue(hass)
        
    await hass.config_entries.async_reload(entry.entry_id)
