from typing import Any
import lib.utils.asset_path as path

from panda3d.core import NodePath, TextureStage

motion_data = path.motion_data()

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
    ) -> bool:
        # 同じモーションの再指定では再スタートしない
        if (
            self.direction == direction
            and self.motion == motion
        ):
            self.loop = loop
            return False

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
        return True

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