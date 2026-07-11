"""Sensor platform for Default Config Manager."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, __version__
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ADVANCED_MODE, DOMAIN
from .helpers import get_static_integrations

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Default Config Manager diagnostic sensors."""
    _LOGGER.debug("Initializing Default Config Manager sensor platform")
    
    if "default_config" in hass.config.components:
        return

    advanced_mode = entry.options.get(CONF_ADVANCED_MODE, False)
    
    # Clean up is now handled strictly in __init__.py during transitions.
    if not advanced_mode:
        _LOGGER.debug("Basic Mode active. Proxy device creation skipped.")
        return

    # Mode 3: Advanced Mode active. Build the proxy devices.
    components = await get_static_integrations(hass)
    entities: list[SensorEntity] = []

    for component in components:
        entities.append(
            DefaultConfigDependencySensor(entry, component)
        )
    
    _LOGGER.debug("Adding %s diagnostic entities", len(entities))
    async_add_entities(entities, update_before_add=True)


class DefaultConfigDependencySensor(SensorEntity):
    """Individual component service sensor."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry, component: str) -> None:
        self._component = component
        self._attr_name = "Status" 
        self._attr_unique_id = f"{entry.entry_id}_dep_{component}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{component}")},
            name=component.replace("_", " ").title(),
            manufacturer="Home Assistant Core",
            sw_version=__version__,
            entry_type=DeviceEntryType.SERVICE,
        )

    def update(self) -> None:
        """Check live component registry."""
        if self._component in self.hass.config.components:
            self._attr_native_value = "Running"
        else:
            self._attr_native_value = "Disconnected"
