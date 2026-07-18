"""Constants for Default Config Manager."""

DOMAIN = "default_config_manager"
NAME = "Default Config Manager"

CONF_ADVANCED_MODE = "advanced_mode"
CONF_COMPONENTS_TO_DISABLE = "components_to_disable"

MODE_0 = 0  # Unmanaged (Missing YAML)
MODE_1 = 1  # Unmanaged (Factory YAML wins)
MODE_2 = 2  # Managed (Basic)
MODE_3 = 3  # Managed (Advanced)

MODE_DISPLAY = {
    MODE_0: "None (Missing from config file)",
    MODE_1: "Unmanaged (default_config is enabled)",
    MODE_2: "Managed (Default)",
    MODE_3: "Managed (Advanced)",
}
