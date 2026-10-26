import lib.src.components.game_object as go
from typing import Callable
import math

from panda3d.core import BitMask32

class Terrain():

    def __init__(self, game):
        self.game = game
        self.bulk_load = game.bulk_load
        self.debug = game.debug
        self.save_span = game.save_span

        self.game_objects = []
        self.previous_objects = []
        self.object_dict = {}

        self.auto_section = [
            self.sec1, self.sec2, self.sec3, self.sec4,
            self.sec5, self.sec6, self.sec7, self.sec8,
            self.sec9, self.sec10, self.sec11, self.sec12,
            self.sec13, self.sec14, self.sec15, self.sec16,
            self.sec17, self.sec18, self.sec19, self.sec20,
            self.sec21, self.sec22, self.sec23, self.sec24,
            self.sec25, self.sec26, self.secLast
        ]

        self.save_count = 0
        # 生成済みのセクション数
        self.section_count = 0

        # 初期セーブポイント
        self.previous_objects = self.generateSaveZone(is_start=True)

        if self.bulk_load:
            # 全セクションを先に生成
            while self.section_count < len(self.auto_section):
                self.generateNextSection()

            # 全セクションをいったん非表示にする
            for objects in self.object_dict.values():
                for obj in objects:
                    obj.node.hide()
        else:
            # 最初のセクションだけ生成
            self.generateNextSection()

        # 最初のセクションセットを表示対象にする
        self.game_objects = self.object_dict[self.auto_section[0]]

        for obj in self.previous_objects + self.game_objects:
            obj.node.show()

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

    # 衝突で開始する移動
    def moveByCollision(self,
            target_vector: list[tuple[float, float, float]],
            loop: bool = False,
            speed: float = 1.0,):
        f = self.moveAround(target_vector, loop, speed)
        def func(target: go.GameObject, dt: float) -> None:
            if target.on_collision or target.getPos() != target.init_pos:
                f(target, dt)
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
                    obj = go.GameObject(parent=self.game.render, loader=self.game.loader, name=name, is_3d=True)
                    obj.setPos(x, y, z, init_pos=True)
                    obj.createCollider("box", debug=self.debug)
                    obj.collider.collision_np.node().setIntoCollideMask(
                        BitMask32.bit(1)
                    )
                    obj_list.append(obj)
        return obj_list

    # キャラ(花)生成関数
    def generateFlower(self, is_start: bool = False) -> go.GameObject:
        flower = go.GameObject(
            self.game.render,
            self.game.loader,
            "Dance_Flower",
            False,
        )
        flower.setScale(1.5, 1.5, 1.5)
        flower.setCamera(self.game.cam)
        flower.createCollider(
            "box",
            self.debug,
            box_size=(-0.3, -0.3, 0, 0.3, 0.3, 0.5),
        )
        flower.continuous = False

        # このセーブポイントが担当するセクション番号
        flower_section = self.section_count
        activated = False

        def func(target: go.GameObject, dt: float) -> None:
            nonlocal activated

            # 毎フレーム呼ばれても、衝突時に一度だけ処理する
            if activated or not target.on_collision:
                return

            activated = True

            if is_start:
                self.game.playSave()
                return

            self.flowerSEFunc(flower_section)(target, dt)
            self.advanceSection(flower_section)

        flower.setSelfFunction(func)
        return flower

    # セーブ地帯追加
    def generateSaveZone(self, is_start: bool = False) -> list[go.GameObject]:
        obj = []

        obj.extend(
            self.plane(
                name="Grass",
                offset=(-2, -2, 0),
                point1=(0, 0, 0),
                point2=(4, 4, 0),
            )
        )

        flower = self.generateFlower(is_start=is_start)
        flower.setPos(0, self.save_span * self.save_count, 1)
        obj.append(flower)

        self.save_count += 1
        return obj

    # セクション関数群
    def generateNextSection(self) -> None:
        if self.section_count >= len(self.auto_section):
            return

        func = self.auto_section[self.section_count]

        # 現在の section_count を使ってセクションを生成
        objects = func()

        # 次のセーブポイントの位置・番号に進む
        self.section_count += 1
        objects.extend(self.generateSaveZone())

        self.object_dict[func] = objects

    def advanceSection(self, next_index: int) -> None:
        # ひとつ前のセクションセットを非表示にする
        for obj in self.previous_objects:
            obj.node.hide()

        # 現在のセットを、ひとつ前のセットにする
        self.previous_objects = self.game_objects

        if next_index < len(self.auto_section):
            # 必要なセクションが未生成なら、ここで生成する
            func = self.auto_section[next_index]

            if func not in self.object_dict:
                self.generateNextSection()

            # 次のセクションセットに切り替える
            self.game_objects = self.object_dict[func]
        else:
            # 最終セーブポイントに到達した場合
            self.game_objects = []

        # 現在のセクションセットと次のセットを表示
        for obj in self.previous_objects + self.game_objects:
            obj.node.show()

    def flowerSEFunc(self, section_count: int):
        def func(target: go.GameObject, dt: float) -> None:
            if section_count >= len(self.auto_section):
                self.game.playSave()
                self.game.gameClear()
                return

            background_number = (
                section_count
                // math.ceil(len(self.auto_section) / 4)
                % len(self.game.background_data["backgrounds"])
            )

            self.game.setBackground(background_number)
            self.game.playSave()

        return func

    # 直進
    def sec1(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Grass", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        return obj

    # 二段ジャンプ
    def sec2(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Grass", offset=(0, 15, 0), point1=(0, 0, 0), point2=(0, 10, 0)))
        return obj

    # レッドブロック
    def sec3(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Grass", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        obj.extend(self.plane(name="Red", offset=(0, 20, 0), point1=(0, 0, 2), point2=(0, 6, 2)))
        return obj

    # 壁キック
    def sec4(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Grass", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        obj.extend(self.plane(name="Stone", offset=(0, 15, 0), point1=(-5, 0, 2), point2=(5, 0, 10)))
        obj.extend(self.plane(name="Stone", offset=(0, 9, 0), point1=(0, 0, 6), point2=(0, 0, 14)))
        return obj

    # 動くブロック
    def sec5(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Dart", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        red1 = self.plane(name="Red", offset=(0, 10, 2), point1=(0, 0, 0), point2=(0, 0, 0))
        red2 = self.plane(name="Red", offset=(0, 10, 2), point1=(0, 20, 0), point2=(0, 20, 0))
        self.setFunc(red1, lambda: self.moveAround([(0, 10, 0)], speed=2))
        self.setFunc(red2, lambda: self.moveAround([(0, -10, 0)], speed=2))
        obj.extend(red1)
        obj.extend(red2)
        return obj

    # チュートリアル終了
    
    # 点在床
    def sec6(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Dart", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0), step=4))
        red = self.plane(name="Red", offset=(6, 10, 2), point1=(0, 0, 0), point2=(0, 20, 0), step=4)
        self.setFunc(
            red,
            lambda: self.moveAround([(-12, 0, 0), (0, 4, 0), (12, 0, 0)], loop=True, speed=3),
        )
        obj.extend(red)
        return obj

    # 壁づたい
    def sec7(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Stone", offset=(-2, 5, 0), point1=(0, 0, 0), point2=(0, 30, 16)))
        obj.extend(self.plane(name="Stone", offset=(-1, 5, 0), point1=(0, 0, 0), point2=(0, 30, 0), step=6))
        return obj


    # 動く床
    def sec8(self) -> list[go.GameObject]:
        obj = []
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
        obj.extend(dart1)
        obj.extend(dart2)
        obj.extend(dart3)
        return obj

    # Redよけ渡
    def sec9(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Dart", offset=(-4, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        obj.extend(self.plane(name="Dart", offset=(4, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
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
        obj.extend(red1)
        obj.extend(red2)
        return obj

    # リフト
    def sec10(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Stone", offset=(0, 15, 0), point1=(-5, 0, 2), point2=(5, 0, 10)))
        obj.extend(self.plane(name="Stone", offset=(0, 9, 0), point1=(0, 0, 6), point2=(0, 0, 14)))
        obj.extend(self.plane(name="Red", offset=(0, 30, 2), point1=(-6, 0, 0), point2=(6, 0, 0)))
        dart = self.plane(name="Dart", offset=(0, 4, 0), point1=(-1, 0, 0), point2=(1, 2, 0))
        self.setFunc(
            dart,
            lambda: self.moveByCollision([(0, 30, 0)], speed=2)
        )
        obj.extend(dart)
        return obj

    # ハードル走
    def sec11(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Red", offset=(-2, 4, -2), point1=(0, 0, 0), point2=(4, 32, 0)))
        obj.extend(self.plane(name="Red", offset=(-2, 6, 2), point1=(0, 0, 0), point2=(0, 26, 0), step=6))
        obj.extend(self.plane(name="Red", offset=(0, 6, 2), point1=(0, 0, 0), point2=(0, 26, 0), step=6))
        obj.extend(self.plane(name="Red", offset=(2, 6, 2), point1=(0, 0, 0), point2=(0, 26, 0), step=6))
        dart1 = self.plane(name="Dart", offset=(-2, 4, 0), point1=(0, 0, 0), point2=(4, 32, 0))
        self.setFunc(
            dart1,
            lambda: self.moveByCollision([(0, 0, -10)], speed=4)
        )
        obj.extend(dart1)
        return obj

    # 迫り来る壁
    def sec12(self) -> list[go.GameObject]:
        obj = []
        dart1 = self.plane(name="Dart", offset=(-2, 4, 0), point1=(0, 0, 0), point2=(4, 32, 0))
        self.setFunc(
            dart1,
            lambda: self.moveByCollision([(0, 0, 10)], speed=4)
        )
        obj.extend(dart1)

        red1 = self.plane(name="Red", offset=(-4, 4, 2), point1=(0, 0, 0), point2=(8, 0, 10))
        self.setFunc(
            red1,
            lambda: self.moveAround([(0, 32, 0)], speed=5)
        )
        obj.extend(red1)
        return obj

    # 乗り継ぎリフト
    def sec13(self) -> list[go.GameObject]:
        obj = []
        dart1 = self.plane(name="Dart", offset=(-2, 4, 0), point1=(0, 0, 0), point2=(0, 0, 0))
        self.setFunc(
            dart1,
            lambda: self.moveByCollision([(0, 10, 0)], speed=3)
        )
        obj.extend(dart1)

        dart2 = self.plane(name="Dart", offset=(2, 14, 0), point1=(0, 0, 0), point2=(0, 0, 0))
        self.setFunc(
            dart2,
            lambda: self.moveByCollision([(0, 10, 0)], speed=3)
        )
        obj.extend(dart2)

        dart3 = self.plane(name="Dart", offset=(-2, 24, 0), point1=(0, 0, 0), point2=(0, 0, 0))
        self.setFunc(
            dart3,
            lambda: self.moveByCollision([(0, 10, 0)], speed=3)
        )
        obj.extend(dart3)

        obj.extend(self.plane(name="Red", offset=(-4, 14, 2), point1=(0, 0, 0), point2=(2, 0, 8)))
        obj.extend(self.plane(name="Red", offset=(-4, 18, 2), point1=(0, 0, 0), point2=(2, 0, 8)))
        obj.extend(self.plane(name="Red", offset=(2, 8, 2), point1=(0, 0, 0), point2=(2, 0, 8)))
        obj.extend(self.plane(name="Red", offset=(2, 24, 2), point1=(0, 0, 0), point2=(2, 0, 8)))
        return obj

    # 縄跳び
    def sec14(self) -> list[go.GameObject]:
        obj = []
        dart = self.plane(name="Dart", offset=(-2, 4, 0), point1=(0, 0, 0), point2=(4, 2, 0))
        self.setFunc(
            dart,
            lambda: self.moveByCollision([(0, 30, 0)], speed=2)
        )
        obj.extend(dart)
        red = self.plane(name="Red", offset=(-2, 36, 2), point1=(0, 0, 0), point2=(4, 0, 0))
        self.setFunc(
            red,
            lambda: self.moveAround([(0, -32, 0)], speed=8)
        )
        obj.extend(red)
        return obj

    # 半マス乗り
    def sec15(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Stone", offset=(-2, 10, 0), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(-1, 10, 2), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Stone", offset=(4, 20, 0), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(5, 20, 2), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Stone", offset=(10, 30, 0), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(11, 30, 2), point1=(0, 0, 0), point2=(0, 0, 0)))
        return obj

    # 駆け足
    def sec16(self) -> list[go.GameObject]:
        obj = []
        dart = self.plane(name="Dart", offset=(0, 4, 0), point1=(0, 0, 0), point2=(0, 0, 0))
        self.setFunc(
            dart,
            lambda: self.moveByCollision([(8, 0, 0), (0, 22, 0), (0, 0, 12), (-12, 0, 0)], speed=10)
        )
        obj.extend(dart)
        obj.extend(self.plane(name="Stone", offset=(-2, 12, 2), point1=(0, 0, 0), point2=(0, 0, 8)))
        obj.extend(self.plane(name="Stone", offset=(4, 12, 2), point1=(0, 0, 0), point2=(0, 0, 8)))
        obj.extend(self.plane(name="Red", offset=(2, 4, 0), point1=(0, 0, 0), point2=(6, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(8, 6, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        obj.extend(self.plane(name="Red", offset=(8, 26, 2), point1=(0, 0, 0), point2=(0, 0, 10)))
        obj.extend(self.plane(name="Red", offset=(4, 26, 12), point1=(0, 0, 0), point2=(2, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(-4, 26, 12), point1=(0, 0, 0), point2=(2, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(-4, 26, 2), point1=(0, 0, 0), point2=(10, 0, 8)))
        return obj

    # 壁よけ
    def sec17(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Grass", offset=(-2, 4, 0), point1=(0, 0, 0), point2=(4, 32, 0)))

        stone = self.plane(name="Stone", offset=(-2, 4, 2), point1=(0, 0, 0), point2=(4, 0, 2))
        self.setFunc(
            stone,
            lambda: self.moveAround([(0, 32, 0)], speed=15)
        )
        obj.extend(stone)

        stone = self.plane(name="Stone", offset=(-2, 36, 6), point1=(0, 0, 0), point2=(4, 0, 2))
        self.setFunc(
            stone,
            lambda: self.moveAround([(0, -32, 0)], speed=10)
        )
        obj.extend(stone)

        obj.extend(self.plane(name="Red", offset=(-4, 6, 6), point1=(0, 0, 0), point2=(8, 0, 8)))
        obj.extend(self.plane(name="Red", offset=(-4, 20, 2), point1=(0, 0, 0), point2=(8, 0, 2)))
        obj.extend(self.plane(name="Red", offset=(-4, 34, 6), point1=(0, 0, 0), point2=(8, 0, 8)))
        return obj

    # 柱
    def sec18(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Stone", offset=(-4, 2, 2), point1=(0, 0, 0), point2=(0, 0, 6)))
        obj.extend(self.plane(name="Stone", offset=(4, 2, 2), point1=(0, 0, 0), point2=(0, 0, 6)))
        stone1 = self.plane(name="Stone", offset=(0, 9, 0), point1=(0, 0, 0), point2=(0, 0, 4))
        stone1.extend(self.plane(name="Stone", offset=(0, 9, 10), point1=(0, 0, 0), point2=(0, 0, 2)))
        stone2 = self.plane(name="Stone", offset=(-6, 12, 16), point1=(0, 0, 0), point2=(0, 0, 4))
        stone3 = self.plane(name="Stone", offset=(6, 12, 16), point1=(0, 0, 0), point2=(0, 0, 4))
        self.setFunc(
            stone1,
            lambda: self.moveAround([(0, 0, 4), (0, 0, -6)], speed=2)
        )
        self.setFunc(
            stone2,
            lambda: self.moveAround([(0, 0, 2), (0, 0, -4)], speed=3)
        )
        self.setFunc(
            stone3,
            lambda: self.moveAround([(0, 0, 2), (0, 0, -4)], speed=3)
        )
        obj.extend(stone1)
        obj.extend(stone2)
        obj.extend(stone3)
        obj.extend(self.plane(name="Grass", offset=(-2, 20, 20), point1=(0, 0, 0), point2=(2, 0, 0)))
        return obj

    # マグマゾーン
    def sec19(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Dart", offset=(-6, 4, -2), point1=(0, 0, 0), point2=(12, 32, 0)))
        obj.extend(self.plane(name="Stone", offset=(-4, 30, 0), point1=(0, 0, 0), point2=(2, 2, 0)))
        obj.extend(self.plane(name="Stone", offset=(1, 10, 0), point1=(0, 0, 0), point2=(2, 2, 0)))
        red = self.plane(name="Red", offset=(-6, 4, -3), point1=(0, 0, 0), point2=(12, 32, 0))
        self.setFunc(
            red,
            lambda: self.moveAround([(0, 0, 2.8)], speed=0.5)
        )
        obj.extend(red)
        return obj

    # 前後左右避け
    def sec20(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Dart", offset=(0, 10, 0), point1=(0, 0, 0), point2=(0, 20, 0)))
        obj.extend(self.plane(name="Dart", offset=(8, 10, 4), point1=(0, 0, 0), point2=(0, 20, 0)))
        obj.extend(self.plane(name="Dart", offset=(-8, 10, 4), point1=(0, 0, 0), point2=(0, 20, 0)))
        red1 = self.plane(name="Red", offset=(-8, 10, 6), point1=(0, 0, 0), point2=(0, 0, 6))
        red1.extend(self.plane(name="Red", offset=(8, 10, 6), point1=(0, 0, 0), point2=(0, 0, 6)))
        red2 = self.plane(name="Red", offset=(0, 30, 2), point1=(0, 0, 0), point2=(0, 0, 10))
        self.setFunc(
            red1,
            lambda: self.moveAround([(0, 20, 0)], speed=8)
        )
        self.setFunc(
            red2,
            lambda: self.moveAround([(0, -20, 0)], speed=8)
        )
        obj.extend(red1)
        obj.extend(red2)
        red3 = self.plane(name="Red", offset=(-12, 10, 2), point1=(0, 0, 0), point2=(0, 20, 0))
        red4 = self.plane(name="Red", offset=(12, 10, 6), point1=(0, 0, 0), point2=(0, 20, 6))
        self.setFunc(
            red3,
            lambda: self.moveAround([(24, 0, 0)], speed=6)
        )
        self.setFunc(
            red4,
            lambda: self.moveAround([(-24, 0, 0)], speed=6)
        )
        obj.extend(red3)
        obj.extend(red4)
        return obj

    # 壁キックアスレチック
    def sec21(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Stone", offset=(0, 4, 0), point1=(0, 0, 0), point2=(0, 0, 12), step=6))
        obj.extend(self.plane(name="Stone", offset=(-4, 10, 0), point1=(0, 0, 0), point2=(8, 0, 16)))
        obj.extend(self.plane(name="Stone", offset=(-4, 16, 8), point1=(0, 0, 0), point2=(8, 0, 16)))
        obj.extend(self.plane(name="Stone", offset=(0, 16, 0), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(-4, 16, 6), point1=(0, 0, 0), point2=(8, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(-4, 14, 8), point1=(0, 0, 0), point2=(8, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(-4, 12, 16), point1=(0, 0, 0), point2=(8, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(0, 22, 4), point1=(0, 0, 0), point2=(0, 0, 20), step=8))
        obj.extend(self.plane(name="Stone", offset=(0, 22, 6), point1=(0, 0, 0), point2=(0, 0, 24), step=8))
        obj.extend(self.plane(name="Red", offset=(-4, 28, 0), point1=(0, 0, 0), point2=(8, 0, 28)))
        return obj

    # 隙間くぐり
    def sec22(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Red", offset=(-4, 8, 0), point1=(0, 0, 0), point2=(8, 0, 4)))
        red1 = self.plane(name="Red", offset=(-4, 8, 12), point1=(0, 0, 0), point2=(8, 0, 6))
        obj.extend(self.plane(name="Red", offset=(-2, 14, -2), point1=(0, 0, 0), point2=(4, 0, 0)))
        dart1 = self.plane(name="Dart", offset=(-2, 14, 0), point1=(0, 0, 0), point2=(4, 0, 0))
        self.setFunc(
            red1,
            lambda: self.moveAround([(0, 0, -6)], speed=2)
        )
        self.setFunc(
            dart1,
            lambda: self.moveByCollision([(0, 0, -4)], speed=6)
        )
        obj.extend(red1)
        obj.extend(dart1)

        obj.extend(self.plane(name="Red", offset=(-4, 20, 0), point1=(0, 0, 0), point2=(8, 0, 4)))
        red2 = self.plane(name="Red", offset=(-4, 20, 12), point1=(0, 0, 0), point2=(8, 0, 6))
        obj.extend(self.plane(name="Red", offset=(-2, 26, -2), point1=(0, 0, 0), point2=(4, 0, 0)))
        dart2 = self.plane(name="Dart", offset=(-2, 26, 0), point1=(0, 0, 0), point2=(4, 0, 0))
        self.setFunc(
            red2,
            lambda: self.moveAround([(0, 0, -6)], speed=4)
        )
        self.setFunc(
            dart2,
            lambda: self.moveByCollision([(0, 0, -4)], speed=6)
        )
        obj.extend(red2)
        obj.extend(dart2)

        obj.extend(self.plane(name="Red", offset=(-4, 32, 0), point1=(0, 0, 0), point2=(8, 0, 4)))
        red2 = self.plane(name="Red", offset=(-4, 32, 12), point1=(0, 0, 0), point2=(8, 0, 6))
        self.setFunc(
            red2,
            lambda: self.moveAround([(0, 0, -6)], speed=6)
        )
        obj.extend(red2)
        return obj

    # 馬飛び
    def sec23(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Grass", offset=(0, 4, 0), point1=(0, 0, 0), point2=(0, 32, 0), step=6))
        obj.extend(self.plane(name="Red", offset=(0, 5, 1), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(0, 11, 1), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(0, 17, 2), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(0, 23, 2), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(0, 29, 3), point1=(0, 0, 0), point2=(0, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(0, 35, 3), point1=(0, 0, 0), point2=(0, 0, 0)))
        return obj

    # 斜め
    def sec24(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Grass", offset=(-2, 4, 0), point1=(0, 0, 0), point2=(4, 0, 0)))
        obj.extend(self.plane(name="Dart", offset=(-2, 6, 0), point1=(0, 0, 0), point2=(4, 12, 0)))
        obj.extend(self.plane(name="Grass", offset=(-2, 20, 0), point1=(0, 0, 0), point2=(4, 0, 0)))
        obj.extend(self.plane(name="Dart", offset=(-2, 22, 0), point1=(0, 0, 0), point2=(4, 12, 0)))
        obj.extend(self.plane(name="Grass", offset=(-2, 36, 0), point1=(0, 0, 0), point2=(4, 0, 0)))
        red1 = self.plane(name="Red", offset=(-4, 4, -2), point1=(0, 0, 0), point2=(8, 0, 0))
        red2 = self.plane(name="Red", offset=(-4, 36, -2), point1=(0, 0, 0), point2=(8, 0, 0))
        red3 = self.plane(name="Red", offset=(-4, 20, -2), point1=(0, 0, 0), point2=(8, 0, 0))
        red4 = self.plane(name="Red", offset=(-4, 12, 4), point1=(0, 0, 0), point2=(8, 0, 0))
        red5 = self.plane(name="Red", offset=(-4, 28, 4), point1=(0, 0, 0), point2=(8, 0, 0))
        self.setFunc(
            red1,
            lambda: self.moveAround([(0, 8, 6), (0, 8, -6), (0, 8, 6), (0, 8, -6)], speed=4)
        )
        self.setFunc(
            red2,
            lambda: self.moveAround([(0, -8, 6), (0, -8, -6), (0, -8, 6), (0, -8, -6)], speed=4)
        )
        self.setFunc(
            red3,
            lambda: self.moveAround([(0, 8, 6), (0, 8, -6), (0, -8, 6), (0, -8, -6), (0, -8, 6), (0, -8, -6)], speed=4)
        )
        self.setFunc(
            red4,
            lambda: self.moveAround([(0, -8, -6), (0, 8, 6), (0, 8, -6), (0, 8, 6), (0, 8, -6), (0, -8, 6), (0, -8, -6)], speed=4)
        )
        self.setFunc(
            red5,
            lambda: self.moveAround([(0, -8, -6), (0, -8, 6), (0, -8, -6), (0, 8, 6), (0, 8, -6), (0, 8, 6), (0, 8, -6)], speed=4)
        )
        obj.extend(red1)
        obj.extend(red2)
        obj.extend(red3)
        obj.extend(red4)
        obj.extend(red5)
        return obj

    # 不安定な足場にレーザー
    def sec25(self) -> list[go.GameObject]:
        obj = []
        dart = self.plane(name="Dart", offset=(-2, 4, 0), point1=(0, 0, 0), point2=(4, 32, 0))
        obj.extend(self.plane(name="Red", offset=(-2, 4, -2), point1=(0, 0, 0), point2=(4, 32, 0)))
        red1 = self.plane(name="Red", offset=(-4, 4, 3), point1=(0, 0, 0), point2=(0, 32, 0))
        red2 = self.plane(name="Red", offset=(-4, 4, 3), point1=(0, 0, 0), point2=(8, 0, 0))
        red3 = self.plane(name="Red", offset=(-2, 4, 2), point1=(0, 0, 0), point2=(0, 0, 6))
        red4 = self.plane(name="Red", offset=(0, 4, 2), point1=(0, 0, 0), point2=(0, 0, 6))
        red5 = self.plane(name="Red", offset=(2, 36, 2), point1=(0, 0, 0), point2=(0, 0, 6))
        self.setFunc(
            dart,
            lambda: self.moveByCollision([(0, 0, -10)], speed=4)
        )
        self.setFunc(
            red1,
            lambda: self.moveAround([(8, 0, 0)], speed=2)
        )
        self.setFunc(
            red2,
            lambda: self.moveAround([(0, 32, 0)], speed=3)
        )
        self.setFunc(
            red3,
            lambda: self.moveAround([(0, 32, 0)], speed=5)
        )
        self.setFunc(
            red4,
            lambda: self.moveAround([(0, 32, 0)], speed=7)
        )
        self.setFunc(
            red5,
            lambda: self.moveAround([(0, -32, 0)], speed=5)
        )
        obj.extend(dart)
        obj.extend(red1)
        obj.extend(red2)
        obj.extend(red3)
        obj.extend(red4)
        obj.extend(red5)
        return obj

    # 上下挟み
    def sec26(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Red", offset=(0, 4, -4), point1=(0, 0, 0), point2=(0, 32, 0)))
        obj.extend(self.plane(name="Red", offset=(0, 4, 10), point1=(0, 0, 0), point2=(0, 32, 0)))
        dart1 = self.plane(name="Dart", offset=(0, 4, 0), point1=(0, 0, 0), point2=(0, 0, 0))
        self.setFunc(
            dart1,
            lambda: self.moveByCollision([(0, 22, 0)], speed=3)
        )
        obj.extend(dart1)
        obj.extend(self.plane(name="Red", offset=(-2, 10, 2), point1=(0, 0, 0), point2=(4, 0, 0)))
        obj.extend(self.plane(name="Red", offset=(0, 26, -2), point1=(0, 0, 0), point2=(0, 0, 0)))
        red1 = self.plane(name="Red", offset=(-4, 18, 10), point1=(0, 0, 0), point2=(8, 0, 6))
        self.setFunc(
            red1,
            lambda: self.moveAround([(0, 0, -8)], speed=2)
        )
        obj.extend(red1)
        red2 = self.plane(name="Red", offset=(-4, 32, 10), point1=(0, 0, 0), point2=(8, 0, 6))
        self.setFunc(
            red2,
            lambda: self.moveAround([(0, 0, -8)], speed=2)
        )
        obj.extend(red2)
        red3 = self.plane(name="Red", offset=(-4, 32, -10), point1=(0, 0, 0), point2=(8, 0, 2))
        self.setFunc(
            red3,
            lambda: self.moveAround([(0, 0, 8)], speed=2)
        )
        obj.extend(red3)
        return obj

    # おしまい
    def secLast(self) -> list[go.GameObject]:
        obj = []
        obj.extend(self.plane(name="Stone", offset=(-2, 4, 0), point1=(0, 0, 0), point2=(4, 8, 0)))
        obj.extend(self.plane(name="Dart", offset=(-2, 14, 0), point1=(0, 0, 0), point2=(4, 8, 0)))
        obj.extend(self.plane(name="Grass", offset=(-2, 24, 0), point1=(0, 0, 0), point2=(4, 12, 0)))
        return obj

    def update(self, dt: float):
        for obj in self.game_objects + self.previous_objects:
            obj.update(dt)