"""Repairs for Default Config Manager."""

from __future__ import annotations
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.components.repairs import RepairsFlow


class RestartRequiredFlow(RepairsFlow):
    """Handler for an issue requiring a restart."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Handle the initialization step."""
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None):
        """Handle the confirmation step."""
        if user_input is not None:
            # Trigger the actual restart
            await self.hass.services.async_call("homeassistant", "restart")
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="confirm")


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow | None:
    """Create flow."""
    if issue_id == "restart_required":
        return RestartRequiredFlow()
    return None
