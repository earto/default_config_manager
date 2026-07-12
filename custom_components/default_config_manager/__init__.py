"""The Default Config Manager integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import device_registry as dr
from homeassistant.components import default_config as ha_default_config
from homeassistant.setup import async_setup_component

from .const import CONF_ADVANCED_MODE, DOMAIN, MODE_0, MODE_1, MODE_2, MODE_3
from .helpers import get_static_integrations

_LOGGER = logging.getLogger(__name__)


def _delete_restart_issue(hass: HomeAssistant) -> None:
    """Clear restart required issue."""
    ir.async_delete_issue(hass, DOMAIN, "restart_required")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Default Config Manager integration."""
    _LOGGER.debug("Setting up Default Config Manager")
    
    # Clear any lingering issues on a fresh boot
    _delete_restart_issue(hass)
    ir.async_delete_issue(hass, DOMAIN, "missing_yaml")

    # Check for presence in configuration.yaml
    launched_via_yaml = DOMAIN in config
    default_config_in_yaml = "default_config" in config

    if launched_via_yaml:
        _LOGGER.debug("YAML check: '%s' detected in configuration.yaml", DOMAIN)
    else:
        _LOGGER.debug("YAML check: '%s' NOT detected in configuration.yaml", DOMAIN)

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

    # Hierarchy Logic
    if default_config_in_yaml:
        mode_code = MODE_1  # Factory default_config wins
    elif not launched_via_yaml:
        mode_code = MODE_0  # Neither are present
    else:
        mode_code = MODE_3 if advanced_mode else MODE_2  # DCM is active

    _LOGGER.info("Default Config Manager running in mode_code=%s", mode_code)
    
    hass.data.setdefault(DOMAIN, {})
    
    # Store current state so our efficient listeners can check it instantly
    for entry in hass.config_entries.async_entries(DOMAIN):
         hass.data[DOMAIN][entry.entry_id] = mode_code
         _LOGGER.debug("DCM State: Stored mode %s for entry %s", mode_code, entry.entry_id)

    # Stand down for Mode 0 and Mode 1
    if mode_code in (MODE_0, MODE_1):
        if mode_code == MODE_0:
            # Trigger the UI warning for Mode 0
            ir.async_create_issue(
                hass,
                DOMAIN,
                "missing_yaml",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="missing_yaml",
            )
        return True

    enabled_components = components if mode_code == MODE_2 else [
        c for c in components if c not in disabled_components
    ]
    
    setup_tasks = [async_setup_component(hass, c, config) for c in enabled_components]
    if setup_tasks:
        await asyncio.gather(*setup_tasks)

    await ha_default_config.async_setup(hass, config)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Default Config Manager from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
