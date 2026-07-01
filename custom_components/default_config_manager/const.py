"""Constants for Default Config Manager"""

DOMAIN = "default_config_manager"
NAME = "Default Config Manager"

CONF_ADVANCED_MODE = "advanced_mode"
CONF_COMPONENTS_TO_DISABLE = "components_to_disable"

# Internal mode codes (do NOT store display names)
MODE_1 = 1  # Basic (Config File)
MODE_2 = 2  # Basic (Managed)
MODE_3 = 3  # Advanced (Managed)

MODE_DISPLAY = {
    MODE_1: "Basic (Config File)",
    MODE_2: "Basic (Managed)",
    MODE_3: "Advanced (Managed)",
}
