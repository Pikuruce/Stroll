import lib.src.components.game_object as go
from typing import Callable
import math

# 関数セット用関数
def setFunc(obj_list: list[go.GameObject], func) -> None:
    for obj in obj_list:
        obj.setSelfFunction(func=func)

# 回転関数
def rotation(h: float, p: float, r: float, s: float) -> None:
    def func(target: go.GameObject, dt: float) -> None:
        rotate = target.getRotate()
        target.setRotate(rotate[0] + h * s, rotate[1] + p * s, rotate[2] + r * s)

    return func

# 周回移動関数
def moveAround(
    target_vector: list[tuple[float, float, float]],
    loop: bool = False,
    speed: float = 1.0,
) -> Callable[[go.GameObject, float], None]:
    if not target_vector:
        raise ValueError("target_vector must not be empty")
    if speed <= 0:
        raise ValueError("speed must be greater than 0")

    # 移動状態を、この関数専用に保持する
    points = None
    target_index = 1
    direction = 1

    def func(target: go.GameObject, dt: float) -> None:
        nonlocal points, target_index, direction

        # 初回実行時に、初期位置と各目的地を計算する
        if points is None:
            if target.init_pos is None:
                raise ValueError(
                    "init_pos must be set before using moveAround"
                )

            start = target.init_pos
            current = (start.x, start.y, start.z)
            points = [current]

            for x, y, z in target_vector:
                current = (
                    current[0] + x,
                    current[1] + y,
                    current[2] + z,
                )
                points.append(current)

        # 現在位置と目的地
        pos = target.getPos()
        destination = points[target_index]

        dx = destination[0] - pos.x
        dy = destination[1] - pos.y
        dz = destination[2] - pos.z

        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        step = speed * dt

        # 目的地に到着、または通り過ぎる場合
        if distance <= step or distance < 1e-6:
            target.setPos(
                destination[0],
                destination[1],
                destination[2],
            )

            # 次の目的地を決める
            if loop:
                # 最後の地点まで来たら初期位置へ戻る
                target_index = (
                    0
                    if target_index == len(points) - 1
                    else target_index + 1
                )
            else:
                # 端まで来たら進行方向を反転する
                if target_index == len(points) - 1:
                    direction = -1
                elif target_index == 0:
                    direction = 1

                target_index += direction

        else:
            # 目的地に向かって一定速度で移動する
            ratio = step / distance

            target.setPos(
                pos.x + dx * ratio,
                pos.y + dy * ratio,
                pos.z + dz * ratio,
            )

    return func
