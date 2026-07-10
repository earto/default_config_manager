"""Init for Default Config Manager."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

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


async def _async_sync_manifest(hass: HomeAssistant, entry: ConfigEntry, mode_code: int) -> None:
    """Helper to dynamically calculate and overwrite the manifest.json dependencies."""
    try:
        core_default_config = await async_get_integration(hass, "default_config")
        factory_deps = core_default_config.dependencies
        
        disabled_components = []
        # Only respect disabled devices if running in Advanced Mode (MODE_3)
        if mode_code == MODE_3:
            components = await get_static_integrations(hass)
            device_registry = dr.async_get(hass)
            for component in components:
                device = device_registry.async_get_device(
                    identifiers={(DOMAIN, f"{entry.entry_id}_{component}")}
                )
                if device and device.disabled_by:
                    disabled_components.append(component)
                    
        target_dependencies = [
            dep for dep in factory_deps if dep not in disabled_components
        ]

        dcm_manifest_path = hass.config.path(
            "custom_components", "default_config_manager", "manifest.json"
        )

        if os.path.exists(dcm_manifest_path):
            def update_manifest_file():
                with open(dcm_manifest_path, "r", encoding="utf-8") as f:
                    dcm_manifest = json.load(f)

                # Use sets to ignore list ordering differences
                if set(dcm_manifest.get("dependencies", [])) != set(target_dependencies):
                    _LOGGER.info("Manifest sync required. Overwriting manifest.json on disk.")
                    dcm_manifest["dependencies"] = target_dependencies
                    
                    with open(dcm_manifest_path, "w", encoding="utf-8") as f:
                        json.dump(dcm_manifest, f, indent=2)
                else:
                    _LOGGER.debug("Manifest is already perfectly aligned with current settings.")

            # Safely execute the file I/O off the main event loop
            await hass.async_add_executor_job(update_manifest_file)
    except Exception as err:
        _LOGGER.error("Failed during manifest sync execution: %s", err)


# --- Setup Logic ---

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Default Config Manager integration."""
    _LOGGER.debug("Setting up Default Config Manager")
    hass.data.setdefault(DOMAIN, {})

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

    # Store state globally for downstream logic
    hass.data[DOMAIN]["mode_code"] = mode_code

    if mode_code == MODE_1:
        _LOGGER.warning("Factory 'default_config' detected. Forcing MODE_1 stand-down.")
        return True

    # NOTE: Manual asyncio.gather setup completely removed here.
    # Stage 1 Core handles this natively via our dynamically built manifest.
    return True


# --- Entry Point Handling ---

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    mode_code = hass.data[DOMAIN].get("mode_code", MODE_2)

    if mode_code != MODE_1:
        # 1. PRE-EMPTIVE WATCHDOG (Catches Core Updates)
        async def run_watchdog_sync(event) -> None:
            _LOGGER.debug("Running pre-emptive watchdog sync")
            await _async_sync_manifest(hass, entry, mode_code)

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, run_watchdog_sync)

        # 2. DEVICE REGISTRY SYNC (Catches UI Toggles Instantly)
        async def async_device_registry_updated(event) -> None:
            if event.data.get("action") == "update":
                device_id = event.data.get("device_id")
                device_registry = dr.async_get(hass)
                device = device_registry.async_get(device_id)
                
                # If a user clicked Enable/Disable on a DCM device in the UI
                if device and any(identifier[0] == DOMAIN for identifier in device.identifiers):
                    _LOGGER.info("DCM component toggled in UI. Synchronizing manifest.json.")
                    await _async_sync_manifest(hass, entry, mode_code)
                    _create_restart_issue(hass)

        entry.async_on_unload(
            hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, async_device_registry_updated)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update (Catches config_flow Mode Switches)."""
    _LOGGER.debug("Options updated. Syncing manifest and creating restart issue.")
    
    # Calculate the new mode instantly
    mode_code = MODE_3 if entry.options.get(CONF_ADVANCED_MODE, False) else MODE_2
    hass.data[DOMAIN]["mode_code"] = mode_code
    
    # Write the new configuration to manifest before reloading
    await _async_sync_manifest(hass, entry, mode_code)
    
    _create_restart_issue(hass)
    await hass.config_entries.async_reload(entry.entry_id)
