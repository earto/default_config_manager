"""Init for Default Config Manager."""

from __future__ import annotations

import asyncio
import json
import logging

import homeassistant.components.default_config as ha_default_config
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er, issue_registry as ir
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_setup_component

from .const import CONF_ADVANCED_MODE, DOMAIN, MODE_1, MODE_2, MODE_3
from .helpers import get_static_integrations

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


def _create_restart_issue(hass: HomeAssistant) -> None:
    """Create the restart required issue in repairs dashboard."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        "restart_required",
        is_fixable=True,  # Set to True to trigger your repairs.py flow
        severity=ir.IssueSeverity.WARNING,
        translation_key="restart_required",
    )


def _delete_restart_issue(hass: HomeAssistant) -> None:
    """Delete the restart required issue."""
    ir.async_delete_issue(hass, DOMAIN, "restart_required")


async def _async_sync_manifest(hass: HomeAssistant, entry: ConfigEntry, mode_code: int) -> bool:
    """Sync dependencies to manifest.json. Returns True if file was changed."""
    try:
        core_default_config = await async_get_integration(hass, "default_config")
        factory_deps = core_default_config.dependencies
        
        disabled = []
        if mode_code == MODE_3:
            components = await get_static_integrations(hass)
            dr_inst = dr.async_get(hass)
            for comp in components:
                dev = dr_inst.async_get_device(identifiers={(DOMAIN, f"{entry.entry_id}_{comp}")})
                if dev and dev.disabled_by:
                    disabled.append(comp)
        
        target = [d for d in factory_deps if d not in disabled]
        path = hass.config.path("custom_components", "default_config_manager", "manifest.json")
        
        def write() -> bool:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if set(data.get("dependencies", [])) != set(target):
                _LOGGER.info("DCM Manifest Sync: Updating dependencies to %s", target)
                data["dependencies"] = target
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return True
            return False
            
        return await hass.async_add_executor_job(write)
    except Exception as e:
        _LOGGER.error("Manifest sync failed: %s", e)
        return False


async def _async_purge_proxy_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Purge all proxy entities and devices."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)

    entities = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
    
    _LOGGER.debug("Purge initiated: Found %d entities and %d devices for entry %s", 
                  len(entities), len(devices), entry.entry_id)

    # Clear disabled state and remove proxy entities
    for entity_entry in entities:
        _LOGGER.debug("Purging entity: %s", entity_entry.entity_id)
        # Clear disabled to avoid wrong state on restored orphan
        if entity_entry.disabled_by:
            ent_reg.async_update_entity(entity_entry.entity_id, disabled_by=None)
            
        ent_reg.async_remove(entity_entry.entity_id)

    # Re-enable and remove proxy devices
    for device_entry in devices:
        _LOGGER.debug("Purging device: %s (ID: %s)", device_entry.name, device_entry.id)
        # Clear disabled to avoid wrong state on restored orphan
        if device_entry.disabled_by:
            dev_reg.async_update_device(device_entry.id, disabled_by=None)
            
        dev_reg.async_remove_device(device_entry.id)


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
    
    # Store current state so our efficient listeners can check it instantly
    for entry in hass.config_entries.async_entries(DOMAIN):
         hass.data[DOMAIN][entry.entry_id] = mode_code
         _LOGGER.debug("DCM State: Stored mode %s for entry %s", mode_code, entry.entry_id)

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
    mode = hass.data[DOMAIN].get(entry.entry_id, MODE_2)
    
    if mode != MODE_3:
        _LOGGER.debug("Setup: Mode %s detected, purging registry.", mode)
        await _async_purge_proxy_devices(hass, entry)
    else:
        _LOGGER.debug("Setup: Mode 3 active, skipping registry purge.")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    # Silent boot sync
    async def sync_on_boot(_): 
        await _async_sync_manifest(hass, entry, hass.data[DOMAIN].get(entry.entry_id, MODE_2))
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, sync_on_boot)
    
    # UI Toggle Listener
    async def sync_on_registry_change(event):
        if event.data.get("action") == "update" and "disabled_by" in event.data.get("changes", {}):
            
            # FAST PATH: Ignore instantly if not in Mode 3
            if hass.data[DOMAIN].get(entry.entry_id, MODE_2) != MODE_3:
                return
                
            device_registry = dr.async_get(hass)
            device = device_registry.async_get(event.data.get("device_id", ""))
            
            # If the device exists and belongs to us, check if the manifest needs writing
            if device and entry.entry_id in device.config_entries:
                if await _async_sync_manifest(hass, entry, MODE_3):
                    _create_restart_issue(hass)
                    
    entry.async_on_unload(
        hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, sync_on_registry_change)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    old_mode = hass.data[DOMAIN].get(entry.entry_id, MODE_2)
    new_mode = MODE_3 if entry.options.get(CONF_ADVANCED_MODE, False) else MODE_2
    
    _LOGGER.debug("Mode change detected: %s -> %s", old_mode, new_mode)
    
    hass.data[DOMAIN][entry.entry_id] = new_mode 
    
    if old_mode == MODE_3 and new_mode == MODE_2:
        _LOGGER.debug("Removing proxy devices from registry")
        await _async_purge_proxy_devices(hass, entry)
        
    if await _async_sync_manifest(hass, entry, new_mode):
        _LOGGER.debug("Trigger restart notification")
        _create_restart_issue(hass)
        
    await hass.config_entries.async_reload(entry.entry_id)
    
