from pathlib import Path
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

with open(PROJECT_DIR / "config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

def getSystemConfig() -> bool:
    return config["system"]

def getWindowConfig() -> dict:
    return config["window"]

def getAudioConfig() -> dict:
    return config["audio"]

def getCameraConfig() -> dict:
    return config["camera"]

def getBackgroundConfig() -> dict:
    return config["background"]

def getGravityConfig() -> dict:
    return config["gravity"]

def getPlayerConfig() -> dict:
    return config["player"]

def getMapConfig() -> dict:
    return config["map"]
