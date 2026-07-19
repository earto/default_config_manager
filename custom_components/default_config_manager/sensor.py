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
from homeassistant.loader import async_get_integration

from .const import DOMAIN, MODE_3
from .helpers import get_standard_integrations

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
    integrations = await get_standard_integrations(hass)
    entities: list[SensorEntity] = []

    for integration in integrations:
        try:
            # Fetch the manifest data for the core component
            integration_info = await async_get_integration(hass, integration)
            display_name = integration_info.name
            docs_url = integration_info.manifest.get(
                "documentation", 
                f"https://www.home-assistant.io/integrations/{integration}"
            )
        except Exception as err:
            _LOGGER.warning("Failed to load manifest for %s, using fallback: %s", integration, err)
            # Fallback to standard formatting if the loader fails
            display_name = integration.replace("_", " ").title()
            docs_url = f"https://www.home-assistant.io/integrations/{integration}"

        entities.append(
            DefaultConfigDependencySensor(entry, integration, display_name, docs_url)
        )
    
    _LOGGER.debug("Adding %s diagnostic entities", len(entities))
    async_add_entities(entities, update_before_add=True)


class DefaultConfigDependencySensor(SensorEntity):
    """Diagnostic sensor for an integration status."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry, integration: str, display_name: str, docs_url: str) -> None:
        self._integration = integration
        self._attr_name = "Status" 
        self._attr_unique_id = f"{entry.entry_id}_dep_{integration}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{integration}")},
            name=display_name,
            manufacturer="Home Assistant Core",
            model="Core Component",
            sw_version=__version__,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=docs_url,
        )

    def update(self) -> None:
        """Check running integrations in registry."""
        if self._integration in self.hass.config.components:
            self._attr_native_value = "Running"
        else:
            self._attr_native_value = "Disconnected"
