"""Constants for Default Config Manager."""

DOMAIN = "default_config_manager"
NAME = "Default Config Manager"

CONF_ADVANCED_MODE = "advanced_mode"

MODE_0 = 0  # Unmanaged (Missing YAML)
MODE_1 = 1  # Unmanaged (Standard YAML wins)
MODE_2 = 2  # Managed (Basic)
MODE_3 = 3  # Managed (Advanced)

MODE_DISPLAY = {
    MODE_0: "None (Not in config file)",
    MODE_1: "Unmanaged (Standard default_config is enabled)",
    MODE_2: "Managed (Basic)",
    MODE_3: "Managed (Advanced)",
}
"""Constants for Default Config Manager."""

DOMAIN = "default_config_manager"
NAME = "Default Config Manager"
CONF_ADVANCED_MODE = "advanced_mode"

# Mode used in options_flow.py
MODE_0 = 0  # Unmanaged (Missing YAML)
MODE_1 = 1  # Unmanaged (Standard YAML wins)
MODE_2 = 2  # Managed (Basic)
MODE_3 = 3  # Managed (Advanced)

MODE_DISPLAY = {
    MODE_0: "None (Not in config file)",
    MODE_1: "Unmanaged (Standard default_config is enabled)",
    MODE_2: "Managed (Basic)",
    MODE_3: "Managed (Advanced)",
}

# Config-file states, only used in config_flow.py
CONFIG_STATE_MODE_0 = "mode_0" # Missing YAML
CONFIG_STATE_MODE_1_STANDARD_ONLY = "mode_1_standard_only" # Standard YAML
CONFIG_STATE_MODE_1_BOTH = "mode_1_both" # Standard YAML wins
CONFIG_STATE_CORRECT = "correct" # Only DCM in YAML

CONFIG_FILE_STATE_DISPLAY = {
    CONFIG_STATE_MODE_0: "None (Not in config file)",
    CONFIG_STATE_MODE_1_STANDARD_ONLY: "Unmanaged (Standard default_config is enabled)",
    CONFIG_STATE_MODE_1_BOTH: "Unmanaged (Both default_config and default_config_manager present)",
    CONFIG_STATE_CORRECT: "Managed (default_config_manager correctly configured)",
}
