from pathlib import Path
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

with open(PROJECT_DIR / "config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

def get_window_size() -> tuple[int, int]:
    return config["window"]["width"], config["window"]["height"]

def get_debug_mode() -> bool:
    return config["system"]["debug_mode"]

def get_window_config() -> dict:
    return config["window"]

def get_audio_config() -> dict:
    return config["audio"]

def get_camera_config() -> dict:
    return config["camera"]

def get_background_config() -> dict:
    return config["background"]

def get_gravity_config() -> dict:
    return config["gravity"]

def get_player_config() -> dict:
    return config["player"]

def get_map_config() -> dict:
    return config["map"]

def get_system_config() -> dict:
    return config["system"]
