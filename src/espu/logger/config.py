# Do NOT touch this file unless you know what you are doing!

DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40
CRITICAL = 50

LEVEL_NAMES = {
    DEBUG: "DEBUG",
    INFO: "INFO",
    WARNING: "WARNING",
    ERROR: "ERROR",
    CRITICAL: "CRITICAL"
}

# Precompute mappings to avoid repeated .upper(), .lower() or .capitalize()
LEVEL_MAPPINGS = {
    "DEBUG": {"low": "debug", "up": "DEBUG", "case": "Debug"},
    "INFO": {"low": "info", "up": "INFO", "case": "Info"},
    "WARNING": {"low": "warning", "up": "WARNING", "case": "Warning"},
    "ERROR": {"low": "error", "up": "ERROR", "case": "Error"},
    "CRITICAL": {"low": "critical", "up": "CRITICAL", "case": "Critical"}
}