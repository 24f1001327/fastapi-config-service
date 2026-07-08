import os
from typing import List

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load .env file
load_dotenv()

# Default configuration
DEFAULT_CONFIG = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def parse_bool(value):
    """Convert various string representations to bool."""
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "on",
    }


def coerce_value(key, value):
    """Convert values to the required type."""
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return parse_bool(value)

    return str(value)


@app.get("/")
def home():
    return {"message": "Configuration Service"}


@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):
    config = DEFAULT_CONFIG.copy()

    # -------------------------------
    # Layer 2: YAML
    # -------------------------------
    if os.path.exists("config.development.yaml"):
        with open("config.development.yaml", "r") as f:
            yaml_config = yaml.safe_load(f) or {}

        for key, value in yaml_config.items():
            config[key] = coerce_value(key, value)

    # -------------------------------
    # Layer 3: .env
    # -------------------------------
    env_mapping = {
        "APP_PORT": "port",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
        "APP_DEBUG": "debug",
        "NUM_WORKERS": "workers",
    }

    for env_key, config_key in env_mapping.items():
        value = os.getenv(env_key)
        if value is not None:
            config[config_key] = coerce_value(config_key, value)

    # -------------------------------
    # Layer 4: OS Environment (APP_*)
    # -------------------------------
    for env_key, value in os.environ.items():
        if not env_key.startswith("APP_"):
            continue

        key = env_key[4:].lower()

        if key == "log_level":
            config["log_level"] = value
        elif key == "api_key":
            config["api_key"] = value
        elif key == "port":
            config["port"] = int(value)
        elif key == "debug":
            config["debug"] = parse_bool(value)
        elif key == "workers":
            config["workers"] = int(value)

    # -------------------------------
    # Layer 5: CLI overrides
    # -------------------------------
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)

        config[key] = coerce_value(key, value)

    # Never expose the real API key
    config["api_key"] = "****"

    return config