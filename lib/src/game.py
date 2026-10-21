import copy,random
from panda3d.core import WindowProperties,DirectionalLight,AmbientLight
from panda3d.core import CollisionHandlerEvent, CollisionNode,CollisionSphere,CollisionBox,CollisionTraverser,CollisionHandlerPusher
from panda3d.core import Camera,NodePath,OrthographicLens
from panda3d.physics import ActorNode,PhysicsCollisionHandler, ForceNode, LinearVectorForce
from panda3d.core import Vec3
from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.ShowBase import ShowBase
import lib.utils.asset_path as path
import lib.utils.app_config as ac
import lib.src.components.game_object as go
from direct.task import Task
from panda3d.core import ClockObject
from panda3d.core import (
    CollisionRay,
    CollisionHandlerQueue,
    BitMask32,
    Point3,
)
import math

class cgprogram(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.exitFunc=self.exit
        self.accept('escape',self.userExit)

        self.debug = ac.get_debug_mode()
        properties=WindowProperties()
        properties.setSize(ac.get_window_size())
        self.win.requestProperties(properties)

        self.disableMouse()

        # カメラ設定
        self.camera_angle = 0.0
        self.camera_rotate_speed = 90.0  # 1秒あたりの回転角度
        self.camera_distance = 20.0
        self.camera_height = 10.0

        lens=OrthographicLens()
        lens.setFilmSize(2,2)
        lens.setNearFar(-1000,1000)

        bgcam=Camera('background')
        bgcam.setLens(lens)
        bgnp=NodePath(bgcam)
        bgnp.setDepthTest(False)
        bgnp.setDepthWrite(False)
        bgdr=self.win.makeDisplayRegion()
        bgdr.setCamera(bgnp)
        bgdr.sort=-100

        fgcam=Camera('foreground')#1
        fgcam.setLens(lens)#1
        fgnp=NodePath(fgcam)#1
        fgnp.setDepthTest(False)#1
        fgnp.setDepthWrite(False)#1
        fgdr=self.win.makeDisplayRegion()#1
        fgdr.setCamera(fgnp)#1
        fgdr.sort=100


        self.background = self.loadImage("Furvival_Background1.png", scale=(1.4, 1.0, 1.4))
        self.background.reparentTo(bgnp)

        self.foreground1 = self.loadImage("Furvival_Foreground1.png", scale=(1.0, 1.0, 1.0))
        self.foreground1.reparentTo(fgnp)
        self.foreground1.setTransparency(True)

        light1=AmbientLight('light1')
        light1.setColor((0.5,0.5,0.5,1))
        light1=self.render.attachNewNode(light1)
        self.render.setLight(light1)

        light2=DirectionalLight('light2')
        light2.setColor((0.8,0.8,0.8,1))
        light2=self.render.attachNewNode(light2)
        light2.setHpr(0,-60,0)
        self.render.setLight(light2)

        # 物理システムの更新を有効化
        self.enableParticles()

        gravity_node = ForceNode("world-gravity")
        gravity_np = self.render.attachNewNode(gravity_node)

        self.gravity_force = LinearVectorForce(0, 0, -35)
        gravity_node.addForce(self.gravity_force)

        self.gameObjects = []

        #床
        self.gameObjects.extend(self.plane(offset=(0, -4, 0), name="Grass", point1=(0, 0, 0), point2=(8, 10, 2)))
        self.gameObjects.extend(self.plane(offset=(20, -4, 0), name="Grass", point1=(0, 0, 0), point2=(8, 10, 2)))

        flower = go.GameObject(self.render, self.loader, "Dance_Flower", False)
        flower.setPos(1, 0, 1)
        flower.camera = self.cam
        self.gameObjects.append(flower)
        #壁
        self.gameObjects.extend(self.plane(offset=(28, -4, 2), name="Dart", point1=(0, 0, 0), point2=(2, 10, 20)))
        self.gameObjects.extend(self.plane(offset=(22, -4, 6), name="Dart", point1=(0, 0, 0), point2=(2, 10, 22)))
        #上の床
        self.gameObjects.extend(self.plane(offset=(28, -4, 22), name="Grass", point1=(0, 0, 0), point2=(10, 26, 2)))
        #壁
        self.gameObjects.extend(self.plane(offset=(28, 26, 0), name="Dart", point1=(0, 0, 0), point2=(10, 2, 26)))
        #床
        self.gameObjects.extend(self.plane(offset=(28, 22, 0), name="Grass", point1=(0, 0, 0), point2=(10, 4, 2)))
        #点在床
        self.gameObjects.extend(self.plane(offset=(38, 10, 0), name="Grass", point1=(2, 12, 0), point2=(4, 14, 2)))
        self.gameObjects.extend(self.plane(offset=(38, 10, 0), name="Grass", point1=(4, 6, 0), point2=(6, 8, 2)))
        self.gameObjects.extend(self.plane(offset=(38, 10, 0), name="Grass", point1=(0, 2, 0), point2=(2, 4, 2)))
        self.gameObjects.extend(self.plane(offset=(38, 10, 0), name="Grass", point1=(6, -4, 0), point2=(8, -2, 2)))
        self.gameObjects.extend(self.plane(offset=(38, 10, 0), name="Grass", point1=(10, -10, 0), point2=(12, -8, 2)))
        #床
        self.gameObjects.extend(self.plane(offset=(38, -10, 0), name="Grass", point1=(0, 0, 0), point2=(10, 10, 2)))

        self.player = go.GameObject(parent=self.render, name="Furvival_Foco32", loader=self.loader, is_3d=False, use_gravity=True, physics_mgr=self.physicsMgr, gravity_force=self.gravity_force)
        self.player.setPos(0, 0, 2)
        self.gameObjects.append(self.player)
        self.player.createCollider("box", debug=self.debug, box_size=(-0.5, -0.5, 0, 0.5, 0.5, 1.0))
        self.player.camera = self.cam

        # プレイヤー専用ライト
        player_light = DirectionalLight("player_light")
        player_light.setColor((1.0, 1.0, 1.0, 1.0))

        self.player_light_np = self.render.attachNewNode(player_light)

        # プレイヤーの方向に向ける
        self.player_light_np.setHpr(0, -30, 0)

        # プレイヤーだけにライトを適用
        self.player.node.setLight(self.player_light_np)

        self.player_light_np.reparentTo(self.cam)
        self.player_light_np.setPos(0, 0, 0)
        self.player_light_np.setHpr(0, 0, 0)

        # 地面検出用のCollisionRay
        self.shadow_ray = CollisionRay(0, 0, 0, 0, 0, -1)

        self.shadow_ray_node = CollisionNode("shadow-ray")
        self.shadow_ray_node.addSolid(self.shadow_ray)

        # 地面専用の衝突マスク
        self.shadow_ray_node.setFromCollideMask(BitMask32.bit(1))
        self.shadow_ray_node.setIntoCollideMask(BitMask32.allOff())

        self.shadow_ray_np = self.render.attachNewNode(
            self.shadow_ray_node
        )

        self.shadow_queue = CollisionHandlerQueue()
        self.shadow_traverser = CollisionTraverser()

        self.shadow_traverser.addCollider(
            self.shadow_ray_np,
            self.shadow_queue,
        )

        # プレイヤー自身にはレイが当たらないようにする
        self.player.collider.collision_np.node().setIntoCollideMask(
            BitMask32.bit(0)
        )

        self.background_start_x = 50
        self.background_start_z = 0

        self.cTrav=CollisionTraverser()
        self.physics_handler = PhysicsCollisionHandler()

        self.physics_handler.addCollider(
            self.player.collider.collision_np,
            self.player.node,
        )

        self.cTrav.addCollider(
            self.player.collider.collision_np,
            self.physics_handler,
        )

        self.taskMgr.add(self.update, "update")

        self.keys = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
            "space": False,
            "right_arrow": False,
            "left_arrow": False
        }

        self.move_speed = 8.0
        self.max_fall_speed = -15
        self.jump = False
        self.jump_count = 2
        self.jump_power = 15.0
        self.jump_cooltime = 0.3
        self.inertia = 20
        self.dx = 0.0
        self.dy = 0.0

        self.accept("w", self.setKey, ["up", True])
        self.accept("w-up", self.setKey, ["up", False])

        self.accept("s", self.setKey, ["down", True])
        self.accept("s-up", self.setKey, ["down", False])

        self.accept("a", self.setKey, ["left", True])
        self.accept("a-up", self.setKey, ["left", False])

        self.accept("d", self.setKey, ["right", True])
        self.accept("d-up", self.setKey, ["right", False])

        self.accept("space", self.setKey, ["space", True])
        self.accept("space-up", self.setKey, ["space", False])

        self.accept("arrow_right", self.setKey, ["right_arrow", True])
        self.accept("arrow_right-up", self.setKey, ["right_arrow", False])

        self.accept("arrow_left", self.setKey, ["left_arrow", True])
        self.accept("arrow_left-up", self.setKey, ["left_arrow", False])

        self.on_collision = False

        self.cTravEvent = CollisionTraverser()
        self.handler = CollisionHandlerEvent()

        self.handler.addInPattern("%fn-into")
        self.handler.addOutPattern("%fn-out")

        self.cTravEvent.addCollider(
            self.player.collider.collision_np,
            self.handler,
        )

        self.accept(
            "Furvival_Foco32-into",
            self.onCollisionStartPlayer,
        )
        self.accept(
            "Furvival_Foco32-out",
            self.onCollisionEndPlayer,
        )

        # BGMを読み込む
        self.bgm = self.loader.loadMusic("assets/sounds/marble soda.ogg")

        # ループ再生
        self.bgm.setLoop(True)
        self.bgm.setVolume(0.5)
        self.bgm.play()

    def onCollisionStartPlayer(self, entry):
        # 衝突した面の法線ベクトルを render 座標系で取得
        self.normal = entry.getSurfaceNormal(self.render)
        if self.normal.z == 1:
            self.jump_count = 2
        elif self.normal != -1:
            self.jump_count = max(self.jump_count, 1)

        if not self.on_collision:
            self.jump = False
        self.on_collision = True

    def onCollisionEndPlayer(self, entry):
        #self.normal.x = 0.0
        #self.normal.y = 0.0
        self.on_collision = False

    def loadImage(self, image_name: str, scale: tuple[float, float, float]) -> OnscreenImage:
        img_path = path.image_path(image_name)
        if not img_path.exists():
            raise FileNotFoundError(f"Image file not found: {img_path}")

        texture = self.loader.loadTexture(img_path)
        if texture is None:
            raise RuntimeError(f"Texture loading failed: {img_path}")
        
        return OnscreenImage(image=texture, scale=scale)

    def plane(self, 
        name: str,
        offset: tuple[float, float, float],
        point1: tuple[float, float, float],
        point2: tuple[float, float, float], 
        ) -> list[go.GameObject]:
        obj_list = []
        for x in range(int(offset[0]) + int(point1[0]), int(offset[0]) + int(point1[0]) + int(point2[0] - point1[0]), 2):
            for y in range(int(offset[1]) + int(point1[1]), int(offset[1]) + int(point1[1]) + int(point2[1] - point1[1]), 2):
                for z in range(int(offset[2]) + int(point1[2]), int(offset[2]) + int(point1[2]) + int(point2[2] - point1[2]), 2):
                    obj = go.GameObject(parent=self.render, loader=self.loader, name=name, is_3d=True)
                    obj.setPos(x, y, z)
                    obj.createCollider("box", debug=self.debug)
                    obj.collider.collision_np.node().setIntoCollideMask(
                        BitMask32.bit(1)
                    )
                    obj_list.append(obj)
        return obj_list

    def playerMove(self, dt: float) -> None:

        dz = 0.0
        physical = self.player.actor_node.getPhysicsObject()
        velocity = physical.getVelocity()

        angle = math.radians(self.camera_angle)

        # カメラが向いている水平前方
        forward_x = math.sin(angle)
        forward_y = math.cos(angle)

        # カメラから見た右方向
        right_x = math.cos(angle)
        right_y = -math.sin(angle)

        # ワールド座標での移動量をカメラ基準に変換
        screen_right = self.dx * right_x + self.dy * right_y
        screen_forward = self.dx * forward_x + self.dy * forward_y

        # WASD の入力
        input_x = (
            int(self.keys["right"]) - int(self.keys["left"])
        )
        input_y = (
            int(self.keys["up"]) - int(self.keys["down"])
        )

        # カメラ基準の入力をワールド座標の方向に変換
        move_x = right_x * input_x + forward_x * input_y
        move_y = right_y * input_x + forward_y * input_y

        # 斜め移動が速くならないように正規化
        length = math.hypot(move_x, move_y)

        if length > 1.0:
            move_x /= length
            move_y /= length

        if self.jump:

            next_dx = self.dx + move_x / self.inertia
            next_dy = self.dy + move_y / self.inertia

            if abs(self.dx) <= 1 or abs(next_dx) < abs(self.dx):
                self.dx = next_dx

            if abs(self.dy) <= 1 or abs(next_dy) < abs(self.dy):
                self.dy = next_dy

        else:
            self.dx = move_x
            self.dy = move_y

        if self.keys["space"] and self.jump_count > 0 and self.jump_cooltime <= 0:
            velocity.z = 0
            self.jump = True
            self.jump_count -= 1
            self.jump_cooltime = 0.3
            if self.normal.z == 1:
                dz = 1
            elif self.normal.z != -1:
                self.dx = self.normal.x * 1
                self.dy = self.normal.y * 1
                dz = 0.8

        if abs(screen_right) > abs(screen_forward):
            direction = "right" if screen_right > 0 else "left"
        elif abs(screen_forward) > 0:
            direction = "back" if screen_forward > 0 else "front"
        else:
            direction = self.player.sprite_animator.direction

        if abs(velocity.z) > 1.5:
            motion = "jump" if velocity.z > 0 else "fall"
        elif self.dx != 0 or self.dy != 0:
            motion = "walk"
        else:
            motion = "idle"

        self.player.sprite_animator.play(
            direction=direction,
            motion=motion,
            loop=True,
        )


        physical.setVelocity(
            Vec3(
                self.dx * self.move_speed,
                self.dy * self.move_speed,
                max(min(velocity.z + dz * self.jump_power, self.jump_power), self.max_fall_speed),
            )
        )

    def playerShadow(self, dt: float):
        player_pos = self.player.getPos()
        
        if player_pos.z < -5:
            self.player.setPos(0, 0, 1.5)
            self.player.actor_node.getPhysicsObject().setVelocity(
            Vec3(0, 0, 0)
            )

        self.cTrav.traverse(self.render)

        self.cTravEvent.traverse(self.render)

        for obj in self.gameObjects:
            obj.update(dt)

        # プレイヤーのワールド座標
        #player_pos = self.player.node.getPos(self.render)

        # プレイヤーの少し上から真下へレイを飛ばす
        self.shadow_ray.setOrigin(
            player_pos.x,
            player_pos.y,
            player_pos.z,
        )

        self.shadow_queue.clearEntries()
        self.shadow_traverser.traverse(self.render)
        self.shadow_queue.sortEntries()

        if self.shadow_queue.getNumEntries() > 0:
            # 最も近い地面との交点を取得
            entry = self.shadow_queue.getEntry(0)
            ground_pos = entry.getSurfacePoint(self.render)

            # 影を地面の少し上に置く
            self.player.shadow_node.setPos(
                self.render,
                Point3(
                    player_pos.x,
                    player_pos.y,
                    ground_pos.z + 0.02,
                ),
            )

            self.player.shadow_node.show()
        else:
            # 地面がなければ影を消す
            self.player.shadow_node.hide()

    def cameraMove(self, dt: float):
        # 右矢印で時計回り、左矢印で反時計回り
        rotate_input = (
            int(self.keys["left_arrow"])
            - int(self.keys["right_arrow"])
        )

        self.camera_angle -= (
            rotate_input * self.camera_rotate_speed * dt
        )

        # 角度をラジアンに変換
        angle = math.radians(self.camera_angle)

        # プレイヤーのワールド座標
        player_pos = self.player.node.getPos(self.render)

        # プレイヤーを中心にカメラを配置
        offset_x = -self.camera_distance * math.sin(angle)
        offset_y = -self.camera_distance * math.cos(angle)

        self.cam.setPos(
            player_pos.x + offset_x,
            player_pos.y + offset_y,
            player_pos.z + self.camera_height,
        )

        # 常にプレイヤーを向く
        self.cam.lookAt(self.player.node)

        # 背景のスクロール
        offset_x = (
            player_pos.x - self.background_start_x
        ) * 0.005

        self.background.setX(-offset_x)

        offset_z = (
            player_pos.z - self.background_start_z
        ) * 0.005

        self.background.setZ(-offset_z)

    def update(self, _task: Task) -> None:
        dt = ClockObject.getGlobalClock().getDt()
        if self.jump_cooltime >= 0:
            self.jump_cooltime -= dt

        self.playerMove(dt)
        self.playerShadow(dt)
        self.cameraMove(dt)

        return Task.cont

    def setKey(self, key, value):
        self.keys[key] = value
    

    def exit(self):
        self.taskMgr.remove(self.taskMgr.getAllTasks())
        self.destroy()
