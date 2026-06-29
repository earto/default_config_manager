"""Repairs for Default Config Manager."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


def create_integration_change_issue(
    hass: HomeAssistant,
    component: str,
    action: str,
) -> None:
    """Create a Repair issue when a default_config integration is enabled or disabled.

    This is the only Repair used by Default Config Manager.
    It informs the user that a system-level default_config component
    has been modified, which is meaningful and actionable.
    """

    ir.async_create_issue(
        hass,
        DOMAIN,
        f"default_config_change_{component}",
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="default_config_change",
        translation_placeholders={
            "component": component,
            "action": action,
        },
    )


def clear_integration_change_issue(hass: HomeAssistant, component: str) -> None:
    """Clear the Repair issue for a specific component."""
    ir.async_delete_issue(
        hass,
        DOMAIN,
        f"default_config_change_{component}",
    )

