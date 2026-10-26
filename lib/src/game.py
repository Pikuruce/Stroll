from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.ShowBase import ShowBase
import lib.utils.asset_path as path
import lib.utils.app_config as ac
import lib.src.components.game_object as go
import lib.src.components.terrain as terrain
from direct.task import Task
import math
from direct.gui.OnscreenText import OnscreenText

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
    ClockObject,
    LVector3f,
    TextNode,
    FontPool
)

from panda3d.physics import PhysicsCollisionHandler, ForceNode, LinearVectorForce

class cgprogram(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.exitFunc=self.exit

        # システム設定
        system_config = ac.get_system_config()
        self.debug = system_config["debug_mode"]

        # フォント読み込み
        self.game_font = FontPool.loadFont(path.font_file())

        # 画面設定
        window_config = ac.get_window_config()
        self.window_width = window_config["width"]
        self.window_height = window_config["height"]
        self.full_screen = window_config["fullscreen"]
        self.setupScreen()

        # カメラ設定
        camera_config = ac.get_camera_config()
        self.camera_rotate_speed = camera_config["rotate_speed"]
        self.camera_distance = camera_config["distance"]
        self.camera_height = camera_config["height"]
        self.camera_pitch_speed = camera_config["pitch_speed"]
        self.camera_min_pitch = camera_config["min_pitch"]
        self.camera_max_pitch = camera_config["max_pitch"]
        self.camera_collision_margin = camera_config["collision_margin"]
        self.camera_return_speed = camera_config["return_speed"]
        self.mouse_sensitivity = camera_config["mouse_sensitivity"]
        self.camera_angle = 0.0
        self.camera_pitch = 0.0
        self.mouse_center_x = 0
        self.mouse_center_y = 0
        self.centerMouse()
        self.disableMouse()
        self.setupCamera()

        # バックグラウンド設定
        background_config = ac.get_background_config()
        self.background_start_x = background_config["start_x"]
        self.background_start_z = background_config["start_z"]
        self.background_data = path.background_data()
        self.setupBackground()

        # 重力設定
        gravity_config = ac.get_gravity_config()
        self.force = gravity_config["force"]
        self.setupGravity()

        # プレイヤー設定
        player_config = ac.get_player_config()
        self.move_speed = player_config["move_speed"]
        self.max_fall_speed = player_config["max_fall_speed"]
        self.jump_power = player_config["jump_power"]
        self.inertia = player_config["inertia"]
        self.jump = False
        self.jump_count = 2
        self.jump_cooltime = 0.3
        self.collision_end_detect = 0.0
        self.dx = 0.0
        self.dy = 0.0
        self.normal = LVector3f(0, 0, 1)
        self.setupPlayer()

        # オーディオ設定
        audio_config = ac.get_audio_config()
        self.master_volume = audio_config["master_volume"]
        self.bgm_volume = audio_config["bgm_volume"]
        self.se_volume = audio_config["se_volume"]
        self.setupAudio()

        # マップ設定
        map_config = ac.get_map_config()
        self.save_span = map_config["save_span"]
        self.bulk_load = map_config["bulk_load"]
        self.flower = None
        self.terrain = terrain.Terrain(self)

        # 操作キー設定
        self.setupKey()

        # 当たり判監視定設定
        self.setupCollision()

        # タスクスタート
        self.clear = False
        self.game_time = 0.0
        self.bgm.play()
        self.taskMgr.add(self.update, "update")

    def setupScreen(self) -> None:
        properties = WindowProperties()
        properties.setFullscreen(self.full_screen)
        properties.setCursorHidden(True)

        if self.full_screen:
            # ディスプレイの解像度を指定する
            properties.setSize(
                self.pipe.getDisplayWidth(),
                self.pipe.getDisplayHeight(),
            )
        else:
            properties.setSize(
                self.window_width,
                self.window_height,
            )

        self.win.requestProperties(properties)

    def setupAudio(self) -> None:
        # BGM・SEを読み込む
        self.bgm = self.loader.loadSfx(path.bgm_path("marble soda.wav"))
        self.se_clear = self.loader.loadSfx(path.bgm_path("clear.wav"))
        self.se_back = self.loader.loadSfx(path.se_path("se_back.wav"))
        self.se_jump = self.loader.loadSfx(path.se_path("se_jump.wav"))
        self.se_save = self.loader.loadSfx(path.se_path("se_save.wav"))

        # BGM設定
        self.bgm.setLoop(True)
        self.bgm.setVolume(self.master_volume * self.bgm_volume)
        self.se_clear.setLoop(False)
        self.se_clear.setVolume(self.master_volume * self.bgm_volume)

        # SE設定
        self.se_back.setLoop(False)
        self.se_back.setVolume(self.master_volume * self.se_volume)
        self.se_jump.setLoop(False)
        self.se_jump.setVolume(self.master_volume * self.se_volume)
        self.se_save.setLoop(False)
        self.se_save.setVolume(self.master_volume * self.se_volume)

    def setupCamera(self) -> None:
        # カメラの障害物検出用レイ
        self.camera_ray = CollisionRay()

        self.camera_ray_node = CollisionNode("camera-ray")
        self.camera_ray_node.addSolid(self.camera_ray)

        # 壁や床など、bit(1) のオブジェクトを検出
        self.camera_ray_node.setFromCollideMask(BitMask32.bit(1))
        self.camera_ray_node.setIntoCollideMask(BitMask32.allOff())

        self.camera_ray_np = self.render.attachNewNode(
            self.camera_ray_node
        )

        self.camera_ray_queue = CollisionHandlerQueue()
        self.camera_ray_traverser = CollisionTraverser()

        self.camera_ray_traverser.addCollider(
            self.camera_ray_np,
            self.camera_ray_queue,
        )

        # カメラの現在の距離（初期値は通常のカメラ位置）
        self.camera_current_distance = math.sqrt(
            self.camera_distance ** 2
            + (self.camera_height - 0.5) ** 2
        )

    def setupBackground(self) -> None:
        self.light1 = AmbientLight("light1")
        color_data = self.background_data["backgrounds"]["0"]["color"]
        self.light1.setColor((color_data["r"], color_data["g"], color_data["b"], color_data["a"]))

        self.light1_np = self.render.attachNewNode(self.light1)
        self.render.setLight(self.light1_np)

        self.light2 = DirectionalLight("light2")
        self.light2.setColor((0.8, 0.8, 0.8, 1.0))

        self.light2_np = self.render.attachNewNode(self.light2)
        self.light2_np.setHpr(0, -60, 0)
        self.render.setLight(self.light2_np)

        lens=OrthographicLens()
        lens.setFilmSize(2,2)
        lens.setNearFar(-1000,1000)

        bgcam=Camera('background')
        bgcam.setLens(lens)
        self.bgnp = NodePath(bgcam)
        self.bgnp.setDepthTest(False)
        self.bgnp.setDepthWrite(False)

        bgdr = self.win.makeDisplayRegion()
        bgdr.setCamera(self.bgnp)
        bgdr.sort = -100

        fgcam=Camera('foreground')#1
        fgcam.setLens(lens)#1
        fgnp=NodePath(fgcam)#1
        fgnp.setDepthTest(False)#1
        fgnp.setDepthWrite(False)#1
        fgdr=self.win.makeDisplayRegion()#1
        fgdr.setCamera(fgnp)#1
        fgdr.sort=100


        self.background = self.loadImage("Furvival_Background1.png", scale=(1.4, 1.0, 1.4))
        self.background.reparentTo(self.bgnp)

        self.foreground1 = self.loadImage("Furvival_Foreground1.png", scale=(1.0, 1.0, 1.0))
        self.foreground1.reparentTo(fgnp)
        self.foreground1.setTransparency(True)

        self.explain_text = OnscreenText(
            text=f"WASD: move   SPACE: jump   ARROW or MOUSE: camera   F11: fullscreen",
            parent=self.foreground1,
            pos=(-0.45, -0.95),
            scale=0.03,
            fg=(1, 1, 0, 0.35),
            font=self.game_font,
            align=TextNode.ACenter,
            mayChange=False,
        )

    def setupGravity(self) -> None:
        # 物理システムの更新を有効化
        self.enableParticles()

        gravity_node = ForceNode("world-gravity")
        gravity_np = self.render.attachNewNode(gravity_node)

        self.gravity_force = LinearVectorForce(0, 0, self.force)
        gravity_node.addForce(self.gravity_force)

    def setupPlayer(self) -> None:
        self.player = go.GameObject(parent=self.render, name="Furvival_Foco32", loader=self.loader, is_3d=False, use_gravity=True, physics_mgr=self.physicsMgr, gravity_force=self.gravity_force)
        self.player.setPos(0, 0, 2)
        self.player.createCollider("box", debug=self.debug, box_size=(-0.5, -0.5, 0, 0.5, 0.5, 1.0))
        self.player.setCamera(self.cam)

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

    def setupKey(self) -> None:
        self.keys = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
            "space": False,
            "right_arrow": False,
            "left_arrow": False,
            "up_arrow": False,
            "down_arrow": False,
        }

        self.respown_point = self.player.getPos()

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

        self.accept("arrow_up", self.setKey, ["up_arrow", True])
        self.accept("arrow_up-up", self.setKey, ["up_arrow", False])

        self.accept("arrow_down", self.setKey, ["down_arrow", True])
        self.accept("arrow_down-up", self.setKey, ["down_arrow", False])

        self.accept("f11", self.switchFullscreen)
        self.accept('escape',self.userExit)

    def setupCollision(self) -> None:
        self.cTravEvent = CollisionTraverser()
        self.handler = CollisionHandlerEvent()

        self.handler.addInPattern("%fn-into")
        self.handler.addOutPattern("%fn-out")
        self.handler.addInPattern("%fn-into-%in")

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
        self.accept(
            "Furvival_Foco32-into-Red",
            self.onCollisionRed,
        )
        self.accept(
            "Furvival_Foco32-into-Dance_Flower",
            self.onCollisionDanceFlower,
        )

    def switchFullscreen(self):
        next_full_screen = not self.full_screen

        properties = WindowProperties()
        properties.setFullscreen(next_full_screen)

        if next_full_screen:
            properties.setSize(
                self.pipe.getDisplayWidth(),
                self.pipe.getDisplayHeight(),
            )
        else:
            properties.setSize(
                self.window_width,
                self.window_height,
            )

        self.win.requestProperties(properties)
        self.full_screen = next_full_screen

    def onCollisionStartPlayer(self, entry):
        # 衝突した面の法線ベクトルを render 座標系で取得
        self.normal = entry.getSurfaceNormal(self.render)
        if self.normal.z == 1:
            self.jump_count = 2
        elif self.normal != -1:
            self.jump_count = max(self.jump_count, 1)

        if not self.player.on_collision:
            self.jump = False

        player = self.player

        # プレイヤー自身の状態を変更
        player.on_collision = True

        # 衝突相手の状態を変更
        other = self.getGameObject(entry.getIntoNodePath())

        if other is not None:
            other.on_collision = True

    def onCollisionEndPlayer(self, entry):
        self.collision_end_detect = 0.1
        self.player.on_collision = False
        # 衝突相手の状態を変更
        other = self.getGameObject(entry.getIntoNodePath())

        if other is not None:
            other.on_collision = False

    def onCollisionRed(self, entry):
        self.playerRespown()

    def onCollisionDanceFlower(self, entry):
        into_np = entry.getIntoNodePath()
        flower = None

        while not into_np.isEmpty():
            flower = next(
                (obj for obj in self.terrain.getGameObjects() if obj.node == into_np),
                None
            )

            if flower is not None:
                break

            into_np = into_np.getParent()

        if flower is not None:
            if self.flower is not None and self.flower != flower:
                self.flower.sprite_animator.play(direction="front", motion="idle", loop=False)
                self.respown_point = flower.getPos()
            if flower.sprite_animator.play(direction="front", motion="dance", loop=True):
                self.flower = flower
                self.flower.ignitionFunc()

    def getGameObject(self, node: NodePath) -> go.GameObject | None:
        while not node.isEmpty():
            if node.hasPythonTag("game_object"):
                return node.getPythonTag("game_object")
            node = node.getParent()

        return None

    def loadImage(self, image_name: str, scale: tuple[float, float, float]) -> OnscreenImage:
        img_path = path.image_path(image_name)
        if not img_path.exists():
            raise FileNotFoundError(f"Image file not found: {img_path}")

        texture = self.loader.loadTexture(img_path)
        if texture is None:
            raise RuntimeError(f"Texture loading failed: {img_path}")
        
        return OnscreenImage(image=texture, scale=scale)

    def setBackground(self, number: int) -> None:
        # 既存の背景画像を破棄
        if self.background is not None:
            self.background.destroy()

        data = self.background_data["backgrounds"][str(number)]

        # 新しい背景画像を生成
        self.background = self.loadImage(
            data["name"],
            scale=(1.4, 1.0, 1.4),
        )

        r = data["color"]["r"]
        g = data["color"]["g"]
        b = data["color"]["b"]
        a = data["color"]["a"]
        self.light1.setColor((r, g, b, a))

        # 背景用カメラの子ノードにする
        self.background.reparentTo(self.bgnp)

    def playerRespown(self) -> None:
            self.player.setPos(self.respown_point.x, self.respown_point.y, self.respown_point.z)
            self.player.actor_node.getPhysicsObject().setVelocity(
            Vec3(0, 0, 0)
            )
            self.playBack()

    def playJump(self) -> None:
        self.se_jump.play()

    def playBack(self) -> None:
        self.se_back.play()

    def playSave(self) -> None:
        self.se_save.play()

    def playClear(self) -> None:
        self.se_clear.play()

    def playBGM(self) -> None:
        self.bgm.play()
    
    def stopBGM(self) -> None:
        self.bgm.stop()

    def gameClear(self) -> None:
        self.disableMovementKeys()
        self.clear = True

        # BGMがなければ、そのままクリアSEを再生
        if self.bgm is None:
            self.playClear()
            return

        self.bgm_start_volume = self.bgm.getVolume()
        self.bgm_fade_duration = 2.0
        self.bgm_fade_elapsed = 0.0

        self.taskMgr.add(
            self.fadeOutBGM,
            "fadeOutBGM",
        )

    def showClearText(self) -> None:
        self.clear_text = OnscreenText(
            text=f"Thank you for playing\nTime {int(self.game_time)} s",
            parent=self.aspect2d,
            pos=(0, 0.5),
            scale=0.12,
            fg=(1, 1, 0, 1),
            font=self.game_font,
            align=TextNode.ACenter,
            mayChange=False,
        )
        self.clear_sub_text = OnscreenText(
            text=f"please push 'escape'",
            parent=self.aspect2d,
            pos=(0, 0.2),
            scale=0.08,
            fg=(1, 1, 0, 1),
            font=self.game_font,
            align=TextNode.ACenter,
            mayChange=False,
        )

    def disableMovementKeys(self) -> None:
        for key in ("w", "s", "a", "d", "space"):
            self.ignore(key)
            self.ignore(f"{key}-up")
        self.keys["up"] = False
        self.keys["down"] = False
        self.keys["left"] = False
        self.keys["right"] = False
        self.keys["space"] = False

    def centerMouse(self) -> None:
        self.mouse_center_x = self.win.getXSize() // 2
        self.mouse_center_y = self.win.getYSize() // 2

        self.win.movePointer(
            0,
            self.mouse_center_x,
            self.mouse_center_y,
        )


    def fadeOutBGM(self, task: Task) -> int:
        dt = ClockObject.getGlobalClock().getDt()
        self.bgm_fade_elapsed += dt

        progress = min(
            self.bgm_fade_elapsed / self.bgm_fade_duration,
            1.0,
        )

        self.bgm.setVolume(
            self.bgm_start_volume * (1.0 - progress)
        )

        if progress >= 1.0:
            self.stopBGM()
            self.playClear()
            self.showClearText()
            return Task.done

        return Task.cont

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

            speed = math.hypot(next_dx, next_dy)

            if speed > 1:
                scale = 1 / speed
                next_dx *= scale
                next_dy *= scale

            self.dx = next_dx
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

            # ジャンプSE
            self.playJump()

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

        if self.clear and motion == "idle":
            self.player.sprite_animator.play(direction="front", motion="hand_wave")
        else:
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

    def playerShadow(self, dt: float) -> None:
        player_pos = self.player.getPos()

        # プレイヤーの少し上から真下へレイを飛ばす
        self.shadow_ray.setOrigin(
            player_pos.x,
            player_pos.y,
            player_pos.z + 0.1,
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
        # マウスの移動量を取得
        mouse_dx = 0.0
        mouse_dy = 0.0

        if self.mouseWatcherNode.hasMouse():
            mouse = self.mouseWatcherNode.getMouse()

            # マウス座標は画面中央が (0, 0)
            mouse_dx = mouse.x
            mouse_dy = mouse.y

            # 次のフレームに向けて中央に戻す
            self.centerMouse()

        # 左右の回転：矢印キー + マウス
        rotate_input = (
            int(self.keys["right_arrow"])
            - int(self.keys["left_arrow"])
            
        )

        self.camera_angle += (
            rotate_input * self.camera_rotate_speed * dt
        )
        self.camera_angle += mouse_dx * self.mouse_sensitivity

        # 上下の回転：矢印キー + マウス
        pitch_input = (
            int(self.keys["up_arrow"])
            - int(self.keys["down_arrow"])
        )

        self.camera_pitch -= (
            pitch_input * self.camera_pitch_speed * dt
        )
        self.camera_pitch -= mouse_dy * self.mouse_sensitivity

        # 上下の角度を制限
        self.camera_pitch = max(
            self.camera_min_pitch,
            min(self.camera_pitch, self.camera_max_pitch),
        )

        # プレイヤーのワールド座標
        player_pos = self.player.node.getPos(self.render)

        angle = math.radians(self.camera_angle)
        pitch = math.radians(self.camera_pitch)

        horizontal_distance = self.camera_distance * math.cos(pitch)
        vertical_offset = self.camera_distance * math.sin(pitch)

        offset_x = -horizontal_distance * math.sin(angle)
        offset_y = -horizontal_distance * math.cos(angle)

        desired_camera_pos = Point3(
            player_pos.x + offset_x,
            player_pos.y + offset_y,
            player_pos.z + self.camera_height + vertical_offset,
        )

        # プレイヤーの少し上を、レイの始点にする
        target = Point3(
            player_pos.x,
            player_pos.y,
            player_pos.z + 0.5,
        )

        # 始点からカメラの通常位置までの方向と距離
        direction = desired_camera_pos - target
        max_distance = direction.length()
        direction.normalize()

        self.camera_ray.setOrigin(target)
        self.camera_ray.setDirection(direction)

        # 障害物を検出
        self.camera_ray_queue.clearEntries()
        self.camera_ray_traverser.traverse(self.render)
        self.camera_ray_queue.sortEntries()

        # 通常時のカメラ距離を目標値とする
        target_distance = max_distance

        if self.camera_ray_queue.getNumEntries() > 0:
            entry = self.camera_ray_queue.getEntry(0)

            # 衝突位置をワールド座標で取得
            hit_pos = entry.getSurfacePoint(self.render)

            # レイの始点から障害物までの距離
            hit_distance = (hit_pos - target).length()

            # 障害物の手前に余白を確保
            target_distance = min(
                max_distance,
                max(
                    0.5,
                    hit_distance - self.camera_collision_margin,
                ),
            )

        # 障害物がある場合は即座に近づく。
        # 障害物がない場合は徐々に通常距離まで戻す。
        if target_distance < self.camera_current_distance:
            self.camera_current_distance = target_distance
        else:
            self.camera_current_distance = min(
                target_distance,
                self.camera_current_distance
                + self.camera_return_speed * dt,
            )

        # 調整した距離にカメラを配置
        camera_pos = target + direction * self.camera_current_distance
        self.cam.setPos(self.render, camera_pos)

        # 常にプレイヤーを向く
        target_point = self.player.getPos()
        target_point.z += 0.5
        self.cam.lookAt(target_point)

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
        if not self.clear:
            self.game_time += dt

        if self.jump_cooltime >= 0:
            self.jump_cooltime -= dt

        self.collision_end_detect -= dt
        if self.collision_end_detect > 0 and self.collision_end_detect - dt <= 0:
            self.normal.x = 0.0
            self.normal.y = 0.0

        player_pos = self.player.getPos()
                
        if player_pos.z < -5:
            self.playerRespown()

        self.cTrav.traverse(self.render)

        self.cTravEvent.traverse(self.render)

        self.player.update(dt)

        self.terrain.update(dt)
        self.playerMove(dt)
        self.playerShadow(dt)
        self.cameraMove(dt)

        return Task.cont

    def setKey(self, key, value):
        self.keys[key] = value
    

    def exit(self):
        self.taskMgr.remove(self.taskMgr.getAllTasks())
        self.destroy()
