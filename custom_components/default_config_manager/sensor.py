"""Sensor platform for Default Config Manager."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, __version__
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_COMPONENTS_TO_DISABLE, DOMAIN
from .helpers import get_static_integrations

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Default Config Manager diagnostic sensors."""
    _LOGGER.debug("Initializing Default Config Hub sensor platform")
    
    if "default_config" in hass.config.components:
        return

    components = await get_static_integrations(hass)
    disabled_components = entry.options.get(CONF_COMPONENTS_TO_DISABLE, [])

    entities: list[SensorEntity] = []

    for component in components:
        entities.append(
            DefaultConfigDependencySensor(entry, component, disabled_components)
        )
    _LOGGER.debug("Adding %s diagnostic entities to the Hub", len(entities))
    
    async_add_entities(entities, update_before_add=True)


class DefaultConfigDependencySensor(SensorEntity):
    """Individual component loaded state."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry, component: str, disabled_components: list[str]) -> None:
        self._component = component
        self._is_disabled_by_user = component in disabled_components
        self._attr_name = component.replace("_", " ").title()
        self._attr_unique_id = f"{entry.entry_id}_dep_{component}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Default Config Hub",
            manufacturer="Default Config Manager",
            sw_version=__version__,
        )

    def update(self) -> None:
        """Check live component registry."""
        if self._is_disabled_by_user:
            self._attr_native_value = "Disabled"
        elif self._component in self.hass.config.components:
            self._attr_native_value = "Running"
        else:
            self._attr_native_value = "Disconnected"
