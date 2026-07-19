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

        # Add the existing status sensor
        entities.append(Status(entry, integration, display_name, docs_url))
        
        # Add the new dependents diagnostic sensor
        entities.append(Dependents(entry, integration, display_name, docs_url))
    
    _LOGGER.debug("Adding %s diagnostic entities", len(entities))
    async_add_entities(entities, update_before_add=True)


class Status(SensorEntity):
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


class Dependents(SensorEntity):
    """Diagnostic sensor to track what depends on a specific integration."""
    
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, 
        entry: ConfigEntry, 
        integration: str, 
        display_name: str, 
        docs_url: str
    ) -> None:
        self._integration = integration
        self._attr_name = "Dependents (rely on this)"
        self._attr_unique_id = f"{entry.entry_id}_dependents_{integration}"
        
        # Bind to the exact same device as the Status sensor
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{integration}")},
            name=display_name,
            manufacturer="Home Assistant Core",
            model="Core Component",
            sw_version=__version__,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=docs_url,
        )
        
        self._attr_native_value = 0
        self._attr_extra_state_attributes = {"dependent_integrations": []}

    async def async_update(self) -> None:
        """Scan running manifests to calculate dependencies."""
        dependent_names: list[str] = []

        # Scan every currently running component on the system
        for loaded_domain in self.hass.config.components:
            # Skip checking our own proxy domain to prevent circular checks
            if loaded_domain == DOMAIN:
                continue

            try:
                # Fetches from Home Assistant's built-in in-memory manifest cache
                integration_info = await async_get_integration(self.hass, loaded_domain)
                
                # Check strict dependencies or structural execution order overrides
                is_dep = self._integration in (integration_info.dependencies or [])
                is_after_dep = self._integration in (integration_info.after_dependencies or [])

                if is_dep or is_after_dep:
                    dependent_names.append(integration_info.name)

            except Exception:
                # Safely ignore any components that fail to load their manifests during runtime
                continue

        # Update entity states
        self._attr_native_value = len(dependent_names)
        self._attr_extra_state_attributes = {
            "dependent_integrations": sorted(dependent_names)
        }
