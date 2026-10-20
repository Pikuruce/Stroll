from pathlib import Path
from panda3d.core import Filename
import yaml
import json
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
ASSET_DIR = PROJECT_DIR / "assets"

with open(PROJECT_DIR / "config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

CHARACTER_DIR = ASSET_DIR / config["assets"][0]
IMAGE_DIR = ASSET_DIR / config["assets"][1]
OBJECT_DIR = ASSET_DIR / config["assets"][2]
SOUND_DIR = ASSET_DIR / config["assets"][3]

def character_path(character_name: str) -> tuple[Filename, dict[str, Any]]:
    character_dir = CHARACTER_DIR / character_name

    image_file = character_dir / f"{character_name}.png"
    json_file = character_dir / f"{character_name}.json"

    with open(json_file, encoding="utf-8") as f:
        json_data = json.load(f)

    image_path = Filename.fromOsSpecific(str(image_file))

    return image_path, json_data

def character_shadow_path() -> Filename:
    shadow_file = CHARACTER_DIR / "Furvival_Shadow.png"
    shadow_path = Filename.fromOsSpecific(str(shadow_file))
    return shadow_path

def image_path(*parts: str) -> Filename:
    return Filename.fromOsSpecific(str(IMAGE_DIR.joinpath(*parts)))

def object_path(object_name: str) -> tuple[Filename, Filename, dict[str, Any]]:
    object_dir = OBJECT_DIR / object_name

    model_file = object_dir / f"{object_name}.obj"
    texture_file = object_dir / f"{object_name}.png"
    json_file = object_dir / f"{object_name}.json"

    with open(json_file, encoding="utf-8") as f:
        json_data = json.load(f)

    model_path = Filename.fromOsSpecific(str(model_file))
    texture_path = Filename.fromOsSpecific(str(texture_file))

    return model_path, texture_path, json_data

def sound_path(*parts: str) -> Filename:
    return Filename.fromOsSpecific(str(SOUND_DIR.joinpath(*parts)))