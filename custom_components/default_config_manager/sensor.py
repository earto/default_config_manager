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

from .const import DOMAIN, MODE_3
from .helpers import get_factory_integrations

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Default Config Manager diagnostic sensors."""
    _LOGGER.debug("Initializing Default Config Manager sensor platform")
    
    # Get mode_code stored by __init__.py
    mode_code = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    
    if mode_code != MODE_3:
        _LOGGER.debug("Advanced Mode (Mode 3) not active. Proxy device creation skipped.")
        return

    # Advanced mode enabled, create proxy devices.
    integrations = await get_factory_integrations(hass)
    entities: list[SensorEntity] = []

    for integration in integrations:
        entities.append(
            DefaultConfigDependencySensor(entry, integration)
        )
    
    _LOGGER.debug("Adding %s diagnostic entities", len(entities))
    async_add_entities(entities, update_before_add=True)


class DefaultConfigDependencySensor(SensorEntity):
    """Diagnostic sensor for an integration status."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry, integration: str) -> None:
        self._integration = integration
        self._attr_name = "Status" 
        self._attr_unique_id = f"{entry.entry_id}_dep_{integration}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{integration}")},
            name=integration.replace("_", " ").title(),
            manufacturer="Home Assistant Core",
            sw_version=__version__,
            entry_type=DeviceEntryType.SERVICE,
        )

    def update(self) -> None:
        """Check running integrations in registry."""
        if self._integration in self.hass.config.components:
            self._attr_native_value = "Running"
        else:
            self._attr_native_value = "Disconnected"
