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
FONT_DIR = ASSET_DIR / config["assets"][4]

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

def bgm_path(*parts: str) -> Filename:
    bgm_dir = SOUND_DIR / "bgm"
    return Filename.fromOsSpecific(str(bgm_dir.joinpath(*parts)))

def se_path(*parts: str) -> Filename:
    se_dir = SOUND_DIR / "se"
    return Filename.fromOsSpecific(str(se_dir.joinpath(*parts)))

def motion_data() -> dict:
    motion_file = ASSET_DIR / "animation.json"

    with open(motion_file) as f:
        json_data = json.load(f)

    return list_to_tuple_hook(json_data)

def font_file() -> str:
    font = FONT_DIR / "DotGothic16-Regular.ttf"
    return Filename.fromOsSpecific(str(font)).getFullpath()

# JSONをパースする際、末端のリストが「すべて数値」かつ「長さが2」ならタプルに変換する関数
def list_to_tuple_hook(obj):
    for key, value in obj.items():
        if isinstance(value, dict):
            continue  # さらに深いネストは再帰的に処理されるためスルー

        if isinstance(value, list):
            new_list = []
            for item in value:
                # 要素が [数値, 数値] の形（リスト）であればタプルに変換
                if isinstance(item, list) and all(
                    isinstance(x, (int, float)) for x in item
                ):
                    new_list.append(tuple(item))
                else:
                    new_list.append(item)
            obj[key] = new_list
    return obj

def background_data() -> dict:
    background_file = IMAGE_DIR / "background.json"

    with open(background_file) as f:
        json_data = json.load(f)

    return json_data