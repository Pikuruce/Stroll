from pathlib import Path
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

with open(PROJECT_DIR / "config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

def get_window_size() -> tuple[int, int]:
    return config["window"]["width"], config["window"]["height"]

def get_debug_mode() -> bool:
    return config["system"]["debug_mode"]