from typing import Any

from panda3d.core import Camera,NodePath,OrthographicLens
from panda3d.core import CardMaker, TextureStage, TransparencyAttrib

motion_data = {
    "Furvival_Foco32": {
        "front": {
            "yip": [(0, 0.5), (1, 0.5)],
            "idle": [(4, 0.2), (5, 0.2), (6, 0.2), (7, 0.2)],
            "walk": [(8, 0.1), (9, 0.1), (10, 0.1), (11, 0.1)],
            "jump": [(12, 2)],
            "fall": [(16, 2)],
        },
        "right": {
            "yip": [(20, 0.5), (21, 0.5)],
            "idle": [(24, 0.2), (25, 0.2), (26, 0.2), (27, 0.2)],
            "walk": [(28, 0.1), (29, 0.1), (30, 0.1), (31, 0.1)],
            "jump": [(32, 2)],
            "fall": [(36, 2)],
        },
        "back": {
            "yip": [(40, 0.5)],
            "idle": [(44, 0.2), (45, 0.2), (46, 0.2), (47, 0.2)],
            "walk": [(48, 0.1), (49, 0.1), (50, 0.1), (51, 0.1)],
            "jump": [(52, 2)],
            "fall": [(56, 2)],
        },
        "left": {
            "yip": [(60, 0.5), (61, 0.5)],
            "idle": [(64, 0.2), (65, 0.2), (66, 0.2), (67, 0.2)],
            "walk": [(68, 0.1), (69, 0.1), (70, 0.1), (71, 0.1)],
            "jump": [(72, 2)],
            "fall": [(76, 2)],
        },
    },
    "Grass": {
        "front": {
            "idle": [(0, 0.3), (1, 0.3), (2, 0.3), (3, 0.3)],
        }
    },
    "Dart": {
        "front": {
            "idle": [(0, 0.3), (1, 0.3), (2, 0.3), (3, 0.3)]
        }
    },
    "Dance_Flower": {
        "front": {
            "idle": [(1, 1)],
            "dance": [(0, 0.2), (1, 0.2), (2, 0.2), (3, 0.2), (4, 0.2), (5, 0.2), (6, 0.2)],
        }
    },
    "Red": {
        "front": {
            "idle": [(0, 0.3), (1, 0.3), (2, 0.3), (3, 0.3)]
        }
    }
}


class SpriteAnimator:
    def __init__(
        self,
        node: NodePath,
        name: str,
        json_data: dict[str, Any],
        is_3d: bool,
    ):
        self.node = node
        self.stage = TextureStage.getDefault()
        self.json_data = json_data
        self.name = name
        self.is_3d = is_3d

        self.sprite_width = self.json_data["meta"]["size"]["w"]
        self.sprite_height = self.json_data["meta"]["size"]["h"]

        self.direction = motion_data[self.name].keys().__iter__().__next__()
        self.motion = motion_data[self.name][self.direction].keys().__iter__().__next__()
        self.frame_index = 0
        self.elapsed_time = 0.0
        self.loop = True

        stage = TextureStage.getDefault()
        # 1コマ分のUV範囲に縮小
        ratio_x = self.json_data["frames"][self.name + "0.png"]["sourceSize"]["w"] / self.sprite_width
        ratio_y = self.json_data["frames"][self.name + "0.png"]["sourceSize"]["h"] / self.sprite_height
        
        if not self.is_3d:
            self.node.setTexScale(stage, ratio_x, ratio_y)


        self.setFrame(
            self.direction,
            self.motion,
            self.frame_index,
        )

    def setFrame(
        self,
        direction: str,
        motion: str,
        frame_index: int,
    ) -> None:
        frame_data = motion_data[self.name][direction][motion][frame_index]
        frame_number, duration = frame_data

        offset_data = self.json_data["frames"][
            self.name + f"{frame_number}.png"
        ]["frame"]

        self.node.setTexOffset(
            self.stage,
            offset_data["x"] / self.sprite_width,
            1 - (
                offset_data["y"] + offset_data["h"]
            ) / self.sprite_height,
        )

    def play(
        self,
        direction: str,
        motion: str,
        loop: bool = True,
    ) -> None:
        # 同じモーションの再指定では再スタートしない
        if (
            self.direction == direction
            and self.motion == motion
        ):
            self.loop = loop
            return

        self.direction = direction
        self.motion = motion
        self.frame_index = 0
        self.elapsed_time = 0.0
        self.loop = loop

        self.setFrame(
            self.direction,
            self.motion,
            self.frame_index,
        )

    def update(self, dt: float) -> None:
        frames = motion_data[self.name][self.direction][self.motion]

        # 現在のフレームの表示時間
        _, duration = frames[self.frame_index]
        self.elapsed_time += dt

        if self.elapsed_time < duration:
            return

        # 時間超過分を保持し、時間刻みの誤差を抑える
        self.elapsed_time -= duration

        # 次のフレームへ
        if self.frame_index + 1 < len(frames):
            self.frame_index += 1
        elif self.loop:
            self.frame_index = 0
        else:
            # 非ループなら最後のフレームで停止
            self.elapsed_time = 0.0
            return

        self.setFrame(
            self.direction,
            self.motion,
            self.frame_index,
        )