import os
import json

from contextvars import ContextVar

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Template")
CONFIG_FILE_PATH = os.path.join(TEMPLATE_DIR, "config.json")

active_endpoint: ContextVar[str] = ContextVar("active_endpoint", default=None)

class Config:
    config_data = {}

    @classmethod
    def load_config(cls):
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    cls.config_data = json.load(f)
            except Exception as e:
                print(f"Failed to load config: {e}")
        else:
            # Recreate sensible default settings
            cls.config_data = {
                "server": {
                    "api_host": "127.0.0.1",
                    "api_port": "8080",
                    "response_delay_seconds": 2.0,
                    "post_response_mode": "201 - 000",
                    "get_response_mode": "200 - 000",
                    "delete_response_mode": "200 - 022",
                    "poll_success_count": 3,
                    "retry_count": 3,
                    "logging_enabled": True,
                    "random_response_enabled": False,
                    "timeout_mode": "Sleep",
                    "high_perf": False
                },
                "ui": {
                    "title": "UAEIPP Buyer Participant Simulator",
                    "theme": {
                        "bg_color": "#f1f5f9",
                        "panel_color": "#ffffff",
                        "accent_color": "#7c3aed",
                        "text_color": "#1e293b",
                        "text_muted": "#64748b",
                        "border_color": "#cbd5e1",
                        "dark_mode": True
                    }
                }
            }
            cls.save_config()

    @classmethod
    def save_config(cls):
        try:
            os.makedirs(TEMPLATE_DIR, exist_ok=True)
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(cls.config_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")

    @classmethod
    def get(cls, *keys, default=None):
        endpoint_key = active_endpoint.get()
        if not getattr(cls, "testing_mode", False) and endpoint_key and len(keys) == 2 and keys[0] == "server":
            # Try to get endpoints -> endpoint_key -> parameter
            val = cls.config_data
            for k in ["endpoints", endpoint_key, keys[1]]:
                if isinstance(val, dict) and k in val:
                    val = val[k]
                else:
                    val = None
                    break
            if val is not None:
                return val

        # Fallback / standard lookup
        val = cls.config_data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    @classmethod
    def set(cls, *keys, value=None):
        if not keys:
            return
        val = cls.config_data
        for k in keys[:-1]:
            if k not in val or not isinstance(val[k], dict):
                val[k] = {}
            val = val[k]
        val[keys[-1]] = value
        cls.save_config()

# Load immediately on import
Config.load_config()
