import lib.src.components.game_object as go
from typing import Callable
import math

from panda3d.core import (
    CollisionRay,
    CollisionHandlerQueue,
    BitMask32,
    Point3,
    WindowProperties,
    DirectionalLight,
    AmbientLight,
    CollisionHandlerEvent, 
    CollisionNode,
    CollisionTraverser,
    Camera,
    NodePath,
    OrthographicLens,
    Vec3,
    ClockObject
)

class Terrain():

    def __init__(self, render, loader, cam, bulk_load: bool, debug: bool, save_zone: int, save_span: int):
        self.render = render
        self.loader = loader
        self.cam = cam
        self.bulk_load = bulk_load
        self.debug = debug
        self.save_zone = save_zone
        self.save_span = save_span
        self.gameObjects = []
        self.trash = []
        self.auto_section = [self.sec1, self.sec2, self.sec3, self.sec4, self.sec5, self.sec6, self.sec7, self.sec8, self.sec9, self.sec10, self.sec11]
        self.auto_section = [self.sec11]
        self.save_count = 0
        self.section_count = 0

        self.generateSaveZone()
        if self.bulk_load:
            for _ in range(len(self.auto_section)):
                self.nextSection()

    # 関数セット用関数
    def setFunc(
        self,
        obj_list: list[go.GameObject],
        func_factory: Callable[[], Callable[[go.GameObject, float], None]],
    ) -> None:
        for obj in obj_list:
            obj.setSelfFunction(func=func_factory())

    # 周回移動関数
    def moveAround(self,
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

    # オブジェクト設置用関数
    def plane(self,
        name: str,
        offset: tuple[float, float, float],
        point1: tuple[float, float, float],
        point2: tuple[float, float, float], 
        step: int=2
        ) -> list[go.GameObject]:
        obj_list = []
        for x in range(int(offset[0]) + int(point1[0]), int(offset[0]) + int(point1[0]) + int(point2[0] - point1[0]) + 1, step):
            for y in range(int(offset[1]) + int(point1[1]) + self.section_count * self.save_span, int(offset[1]) + int(point1[1]) + int(point2[1] - point1[1]) + self.section_count * self.save_span + 1, step):
                for z in range(int(offset[2]) + int(point1[2]), int(offset[2]) + int(point1[2]) + int(point2[2] - point1[2]) + 1, step):
                    obj = go.GameObject(parent=self.render, loader=self.loader, name=name, is_3d=True)
                    obj.setPos(x, y, z, init_pos=True)
                    obj.createCollider("box", debug=self.debug)
                    obj.collider.collision_np.node().setIntoCollideMask(
                        BitMask32.bit(1)
                    )
                    obj_list.append(obj)
        return obj_list

    # キャラ(花)生成関数
    def generateFlower(self) -> go.GameObject:
        flower = go.GameObject(self.render, self.loader, "Dance_Flower", False)
        flower.setScale(1.5, 1.5, 1.5)
        flower.setCamera(self.cam)
        flower.createCollider("box", self.debug, box_size=(-0.3, -0.3, 0, 0.3, 0.3, 0.5))
        flower.continuous = False
        if not self.bulk_load:
            def func(target: go.GameObject, dt: float) -> None:
                self.nextSection()
                target.self_func = None
            flower.setSelfFunction(func)
        return flower

    # セーブ地帯追加
    def generateSaveZone(self) -> None:
        self.gameObjects.extend(self.plane(name="Grass", offset=(-2, -2, 0), point1=(0, 0, 0), point2=(4, 4, 0)))
        flower = self.generateFlower()
        flower.setPos(0, self.save_span * self.save_count, 1)
        self.gameObjects.append(flower)
        self.save_count += 1

    # セクション関数群
    def set_section(self, func) -> None:
        func()
        self.section_count += 1

    # 直進
    def sec1(self) -> None:
        self.gameObjects.extend(self.plane(name="Grass", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))

    # 二段ジャンプ
    def sec2(self) -> None:
        self.gameObjects.extend(self.plane(name="Grass", offset=(0, 15, 0), point1=(0, 0, 0), point2=(0, 10, 0)))

    # レッドブロック
    def sec3(self) -> None:
        self.gameObjects.extend(self.plane(name="Grass", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        self.gameObjects.extend(self.plane(name="Red", offset=(0, 20, 0), point1=(0, 0, 2), point2=(0, 6, 2)))

    # 壁キック
    def sec4(self) -> None:
        self.gameObjects.extend(self.plane(name="Grass", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        self.gameObjects.extend(self.plane(name="Stone", offset=(0, 15, 0), point1=(-5, 0, 2), point2=(5, 0, 10)))
        self.gameObjects.extend(self.plane(name="Stone", offset=(0, 9, 0), point1=(0, 0, 6), point2=(0, 0, 14)))

    # 動くブロック
    def sec5(self) -> None:
        self.gameObjects.extend(self.plane(name="Dart", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        red1 = self.plane(name="Red", offset=(0, 10, 2), point1=(0, 0, 0), point2=(0, 0, 0))
        red2 = self.plane(name="Red", offset=(0, 10, 2), point1=(0, 20, 0), point2=(0, 20, 0))
        self.setFunc(red1, lambda: self.moveAround([(0, 10, 0)], speed=2))
        self.setFunc(red2, lambda: self.moveAround([(0, -10, 0)], speed=2))
        self.gameObjects.extend(red1)
        self.gameObjects.extend(red2)

    # チュートリアル終了
    
    # 点在床
    def sec6(self) -> None:
        self.gameObjects.extend(self.plane(name="Dart", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0), step=4))
        red = self.plane(name="Red", offset=(6, 10, 2), point1=(0, 0, 0), point2=(0, 20, 0), step=4)
        self.setFunc(
            red,
            lambda: self.moveAround([(-12, 0, 0), (0, 4, 0), (12, 0, 0)], loop=True, speed=3),
        )
        self.gameObjects.extend(red)

    # 壁づたい
    def sec7(self) -> None:
        self.gameObjects.extend(self.plane(name="Stone", offset=(-2, 5, 0), point1=(0, 0, 0), point2=(0, 30, 16)))

    # 動く床
    def sec8(self) -> None:
        dart1 = self.plane(name="Grass", offset=(0, 6, 0), point1=(0, 0, 0), point2=(2, 2, 0))
        dart2 = self.plane(name="Grass", offset=(0, 6, 0), point1=(-8, 14, 4), point2=(-6, 16, 4))
        dart3 = self.plane(name="Grass", offset=(0, 6, 0), point1=(2, 24, 6), point2=(4, 26, 6))
        self.setFunc(
            dart1,
            lambda: self.moveAround([(0, 0, 8)], speed=2)
        )
        self.setFunc(
            dart2,
            lambda: self.moveAround([(0, 0, -4)], speed=2)
        )
        self.setFunc(
            dart3,
            lambda: self.moveAround([(0, 0, -6)], speed=2)
        )
        self.gameObjects.extend(dart1)
        self.gameObjects.extend(dart2)
        self.gameObjects.extend(dart3)

    # Redよけ渡
    def sec9(self) -> None:
        self.gameObjects.extend(self.plane(name="Dart", offset=(-4, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        self.gameObjects.extend(self.plane(name="Dart", offset=(4, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        red1 = self.plane(name="Red", offset=(-8, 10, 2), point1=(0, 0, 0), point2=(0, 0, 8))
        red2 = self.plane(name="Red", offset=(4, 10, 2), point1=(0, 20, 0), point2=(0, 20, 8))
        self.setFunc(
            red1,
            lambda: self.moveAround([(0, 20, 0), (4, 0, 0), (0, -20, 0)], True, 12)
        )
        self.setFunc(
            red2,
            lambda: self.moveAround([(0, -20, 0), (4, 0, 0), (0, 20, 0)], True, 12)
        )
        self.gameObjects.extend(red1)
        self.gameObjects.extend(red2)

    # リフト
    def sec10(self) -> None:
        self.gameObjects.extend(self.plane(name="Stone", offset=(0, 15, 0), point1=(-5, 0, 2), point2=(5, 0, 10)))
        self.gameObjects.extend(self.plane(name="Stone", offset=(0, 9, 0), point1=(0, 0, 6), point2=(0, 0, 14)))
        self.gameObjects.extend(self.plane(name="Red", offset=(0, 30, 2), point1=(-6, 0, 0), point2=(6, 0, 0)))
        dart = self.plane(name="Dart", offset=(0, 4, 0), point1=(-1, 0, 0), point2=(1, 2, 0))
        def func_func():
            f = self.moveAround([(0, 30, 0)], speed=2)
            def func(target: go.GameObject, dt: float) -> None:
                if target.on_collision or target.getPos() != target.init_pos:
                    f(target, dt)
            return func

        self.setFunc(
            dart,
            lambda: func_func()
        )
        self.gameObjects.extend(dart)

    # ハードル走
    def sec11(self) -> None:
        self.gameObjects.extend(self.plane(name="Red", offset=(-2, 4, -2), point1=(0, 0, 0), point2=(4, 30, 0)))
        self.gameObjects.extend(self.plane(name="Red", offset=(-2, 6, 2), point1=(0, 0, 0), point2=(0, 26, 0), step=6))
        self.gameObjects.extend(self.plane(name="Red", offset=(0, 6, 2), point1=(0, 0, 0), point2=(0, 26, 0), step=6))
        self.gameObjects.extend(self.plane(name="Red", offset=(2, 6, 2), point1=(0, 0, 0), point2=(0, 26, 0), step=6))
        dart1 = self.plane(name="Dart", offset=(-2, 4, 0), point1=(0, 0, 0), point2=(4, 32, 0))
        def func_func():
            f = self.moveAround([(0, 0, -10)], speed=4)
            def func(target: go.GameObject, dt: float) -> None:
                if target.on_collision or target.getPos() != target.init_pos:
                    f(target, dt)
                
            return func
        self.setFunc(
            dart1,
            lambda: func_func()
        )
        self.gameObjects.extend(dart1)

    # 迫り来る壁
    def sec12(self) -> None:
        dart1 = self.plane(name="Dart", offset=(0, 4, 0), point1=(0, 0, 0), point2=(0, 0, 0))


    def nextSection(self) -> None:
        if not self.bulk_load:
            for obj in self.trash:
                obj.remove()
            self.trash.clear()
            self.trash.extend(self.gameObjects)
            self.gameObjects.clear()
        
        self.set_section(self.auto_section[self.section_count])
        self.generateSaveZone()

    def update(self, dt: float):
        for obj in self.trash + self.gameObjects:
            obj.update(dt)