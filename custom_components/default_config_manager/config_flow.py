"""Config flow for Default Config Manager."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import __version__ as ha_version

# Adjust these imports based on your actual const.py and helpers.py structure
from .const import DOMAIN, CONF_ADVANCED_MODE
from .helpers import get_standard_integrations

class DefaultConfigManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Default Config Manager."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""
        # Enforce single instance allowed
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # Check the boolean value of the checkbox
            is_advanced = user_input.get("enable_advanced_mode", False)

            # Create the entry. 
            # We store the mode in 'options' so it can be changed later via options_flow
            return self.async_create_entry(
                title="Default Config Manager",
                data={},
                options={
                    CONF_ADVANCED_MODE: is_advanced
                }
            )

        # Retrieve dynamic data for the UI placeholders
        # We use HA's core version for default_config_version
        standard_integrations = get_standard_integrations(self.hass)
        total_integrations = len(standard_integrations)

        # Define the schema with the optional checkbox (defaults to unchecked/False)
        data_schema = vol.Schema(
            {
                vol.Optional("enable_advanced_mode", default=False): bool,
            }
        )

        # Show the form and pass the exact placeholders mapped in strings.json
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            description_placeholders={
                "default_config_version": ha_version,
                "total_integrations": str(total_integrations),
            },
        )
