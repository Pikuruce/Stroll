from pathlib import Path
from typing import Any
import math

from panda3d.core import (
    NodePath,
    CardMaker,
    TransparencyAttrib,
)
from panda3d.physics import ActorNode

import lib.utils.asset_path as path
import lib.src.components.sprite_animator as sprani
import lib.src.components.collider as col


class GameObject:
    def __init__(
        self,
        parent: NodePath,
        loader: Any,
        name: str,
        is_3d: bool = True,
        use_gravity: bool = False,
        physics_mgr = None,
        gravity_force = None,
    ):
        if use_gravity:
            self.actor_node = ActorNode(name)
            self.node = parent.attachNewNode(self.actor_node)

            physics_mgr.attachPhysicalNode(self.actor_node)
            self.actor_node.getPhysical(0).addLinearForce(gravity_force)
        else:
            self.actor_node = None
            self.node = parent.attachNewNode(name)

        self.loader = loader
        self.name = name
        self.is_3d = is_3d

        self.shadow = None
        if is_3d:
            model, json_data = self.load3DModel(name)
        else:
            model, shadow, json_data = self.load2DModel(name)
            
            self.shadow_node = self.node.attachNewNode("shadow")
            shadow.reparentTo(self.shadow_node)
            self.shadow = shadow



        model.reparentTo(self.node)
        self.model = model

        self.sprite_animator = sprani.SpriteAnimator(
            model, name, json_data, is_3d
        )

        self.sprite_animator.play(direction="front", motion="idle", loop=True)

        self.collider = None
        self.camera = None
        self.self_func = None

    def createCollider(self, collision_type: str,
                       debug: bool, 
                       sphere_size: tuple = (0, 0, 0.5, 0.45), 
                       box_size: tuple = (-1.0, -1.0, -1.0, 1.0, 1.0, 1.0),) -> None:
        self.collider = col.Collider(
            parent=self.node,
            name=self.name,
            collision_type=collision_type,
            debug=debug,
            sphere_size=sphere_size,
            box_size=box_size
        )

    def load3DModel(
        self, name: str
    ) -> tuple[NodePath, dict[str, Any] | None]:

        model_path, texture_path, json_data = path.object_path(name)
        file_path = Path(model_path.toOsSpecific())

        if not file_path.is_file():
            raise FileNotFoundError(
                f"Model file not found: {file_path}"
            )

        texture = self.loader.loadTexture(texture_path)

        if texture is None:
            raise RuntimeError(
                f"Texture loading failed: {texture_path}"
            )

        model = self.loader.loadModel(model_path, noCache=True)
        model.setTexture(texture)

        if model is None or model.isEmpty():
            raise RuntimeError(
                f"Model loading failed: {model_path}"
            )

        if json_data is None:
            raise RuntimeError(
                f"JSON data loading failed: {name}"
            )

        return model, json_data

    def load2DModel(
        self, name: str
    ) -> tuple[NodePath, NodePath, dict[str, Any] | None]:
        json_data = None

        img_path, json_data = path.character_path(name)
        shadow_path = path.character_shadow_path()

        file_path = Path(img_path.toOsSpecific())
        shadow_file_path = Path(shadow_path.toOsSpecific())

        if not file_path.is_file():
            raise FileNotFoundError(
                f"Image file not found: {file_path}"
            )

        if not shadow_file_path.is_file():
            raise FileNotFoundError(
                f"Shadow image file not found: {shadow_file_path}"
            )

        if json_data is None:
            raise RuntimeError(
                f"JSON data loading failed: {name}"
            )

        image = self.loader.loadTexture(img_path)
        shadow_image = self.loader.loadTexture(shadow_path)

        if image is None:
            raise RuntimeError(
                f"Texture loading failed: {img_path}"
            )

        if shadow_image is None:
            raise RuntimeError(
                f"Texture loading failed: {shadow_path}"
            )

        card_maker = CardMaker(name)
        card_maker.setFrame(-0.5, 0.5, 0.0, 1.0)

        shadow_card_maker = CardMaker("Furvival_Shadow")
        shadow_card_maker.setFrame(-0.5, 0.5, 0.0, 1.0)

        # 親ノードへの登録は、呼び出し元で行う
        card = NodePath(card_maker.generate())
        card.setTexture(image)
        card.setTransparency(TransparencyAttrib.MAlpha)

        shadow_card = NodePath(shadow_card_maker.generate())
        shadow_card.setTexture(shadow_image)
        shadow_card.setP(-90)
        shadow_card.setScale(0.6, 0.6, 0.6)
        shadow_card.setPos(0, -0.25, 0.05)
        shadow_card.setTransparency(TransparencyAttrib.MAlpha)
        

        return card, shadow_card, json_data

    def faceCamera(self) -> None:
        if self.camera is None:
            return

        # カメラとキャラクターのワールド座標
        camera_pos = self.camera.getPos(self.node.getParent())
        character_pos = self.node.getPos(self.node.getParent())

        dx = camera_pos.x - character_pos.x
        dy = camera_pos.y - character_pos.y

        # 水平方向の角度を計算
        heading = math.degrees(math.atan2(dx, -dy))

        # モデルだけ回転させる（コリジョンは回転しない）
        self.model.setH(heading)

    def setPos(self, x, y, z) -> None:
        self.node.setPos(x, y, z)

    def getPos(self):
        return self.node.getPos()

    def setScale(self, x, y=None, z=None) -> None:
        if y is None:
            self.node.setScale(x)
        else:
            self.node.setScale(x, y, z)

    def setCamera(self, camera) -> None:
        self.camera = camera

    def setSelfFunction(self, func) -> None:
        self.self_func = func

    def remove(self) -> None:
        self.node.removeNode()

    def update(self, dt: float) -> None:
        if hasattr(self, "sprite_animator"):
            self.sprite_animator.update(dt)

        if not self.is_3d and self.camera is not None:
            self.faceCamera()

        if self.self_func is not None:
            self.self_func(self, dt)