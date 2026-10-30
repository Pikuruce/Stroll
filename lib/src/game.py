from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.ShowBase import ShowBase
import lib.utils.asset_path as path
import lib.utils.app_config as ac
import lib.src.components.game_object as go
import lib.src.components.terrain as terrain
import lib.src.components.title_screen as ts
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
    FontPool,
    CollisionBox
)

from panda3d.physics import PhysicsCollisionHandler, ForceNode, LinearVectorForce

class Stroll(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.exitFunc=self.exit
        self.title = True

        # システム設定
        system_config = ac.getSystemConfig()
        self.debug = system_config["debug_mode"]

        self.terrain_mask = BitMask32.bit(1)
        self.flower_mask = BitMask32.bit(2)

        self.game_text = "WASD: move   SPACE: jump   ARROW or MOUSE: camera   F11: fullscreen   C: switch camera mode"
        self.title_text = "WASD: select   SPACE: decide"

        # フォント読み込み
        self.game_font = FontPool.loadFont(path.font_file())

        # 画面設定
        window_config = ac.getWindowConfig()
        self.window_width = window_config["width"]
        self.window_height = window_config["height"]
        self.full_screen = window_config["fullscreen"]
        self.setupScreen()

        # カメラ設定
        camera_config = ac.getCameraConfig()
        self.camera_rotate_speed = camera_config["rotate_speed"]
        self.camera_distance = camera_config["distance"]
        self.camera_height = camera_config["height"]
        self.camera_pitch_speed = camera_config["pitch_speed"]
        self.camera_min_pitch = camera_config["min_pitch"]
        self.camera_max_pitch = camera_config["max_pitch"]
        self.camera_collision_margin = camera_config["collision_margin"]
        self.camera_return_speed = camera_config["return_speed"]
        self.mouse_sensitivity = camera_config["mouse_sensitivity"]
        self.camera_constant_distance = camera_config["constant_distance"]
        self.camera_angle = 0.0
        self.camera_pitch = 0.0
        self.mouse_center_x = 0
        self.mouse_center_y = 0
        self.centerMouse()
        self.disableMouse()
        self.setupCamera()

        # 重力設定
        gravity_config = ac.getGravityConfig()
        self.force = gravity_config["force"]
        self.setupGravity()

        # オーディオ設定
        audio_config = ac.getAudioConfig()
        self.master_volume = audio_config["master_volume"]
        self.bgm_volume = audio_config["bgm_volume"]
        self.se_volume = audio_config["se_volume"]
        self.setupAudio()

        # バックグラウンド設定
        background_config = ac.getBackgroundConfig()
        self.background_start_x = background_config["start_x"]
        self.background_start_z = background_config["start_z"]
        self.background_data = path.background_data()
        self.setupBackgroundEtc()

        # プレイヤー設定
        player_config = ac.getPlayerConfig()
        self.move_speed = player_config["move_speed"]
        self.max_fall_speed = player_config["max_fall_speed"]
        self.jump_power = player_config["jump_power"]
        self.inertia = player_config["inertia"]
        self.jump = False
        self.jump_count = 2
        self.jump_cooltime = 0.3
        self.dx = 0.0
        self.dy = 0.0
        self.ground_pos = LVector3f(0, 0, 0)
        self.player_pos = LVector3f(0, 0, 0)
        self.is_ground = False
        self.is_wall = False
        self.wall_normal = None

        # マップ設定
        map_config = ac.getMapConfig()
        self.save_span = map_config["save_span"]
        self.bulk_load = map_config["bulk_load"]
        self.flower = None

        # 操作キー設定
        self.setupKey()

        # タイトル画面操作用クラス
        self.title_screen_controller = ts.TitleScreen(self)

        # タスクスタート
        self.taskMgr.add(self.update, "update")

    def startGame(self) -> None:
        """
        タイトル画面からゲーム開始するときに呼ばれる関数
        """
        self.clear = False
        self.game_time = 0.0

        self.explain_text.setText(self.game_text)
        # 背景変更
        self.setBackground(0)
        # プレイヤー生成
        self.setupPlayer()
        # 当たり判監視定設定
        self.setupCollision()
        # マップ生成
        self.terrain = terrain.Terrain(self)
        self.game_bgm.play()

    def changeBulkLoad(self) -> bool:
        """
        タイトル画面の設定で使う関数
        """
        self.bulk_load = not self.bulk_load
        return self.bulk_load

    def changeDebug(self) -> bool:
        """
        タイトル画面の設定で使う関数
        """
        self.debug = not self.debug
        return self.debug

    def setupScreen(self) -> None:
        """
        init関数で最初に呼ばれる
        """
        properties = WindowProperties()
        properties.setFullscreen(self.full_screen)
        properties.setCursorHidden(True)

        if self.full_screen:
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
        """
        init関数で最初に呼ばれる
        """
        # BGM・SEを読み込む
        self.game_bgm = self.loader.loadSfx(path.bgm_path("marble soda.wav"))
        self.title_bgm = self.loader.loadSfx(path.bgm_path("title.wav"))
        self.clear_bgm = self.loader.loadSfx(path.bgm_path("clear.wav"))
        self.se_back = self.loader.loadSfx(path.se_path("se_back.wav"))
        self.se_jump = self.loader.loadSfx(path.se_path("se_jump.wav"))
        self.se_save = self.loader.loadSfx(path.se_path("se_save.wav"))

        # BGM設定
        self.game_bgm.setLoop(True)
        self.game_bgm.setVolume(self.master_volume * self.bgm_volume)
        self.title_bgm.setLoop(True)
        self.title_bgm.setVolume(self.master_volume * self.bgm_volume)
        self.clear_bgm.setLoop(False)
        self.clear_bgm.setVolume(self.master_volume * self.bgm_volume)

        # SE設定
        self.se_back.setLoop(False)
        self.se_back.setVolume(self.master_volume * self.se_volume)
        self.se_jump.setLoop(False)
        self.se_jump.setVolume(self.master_volume * self.se_volume)
        self.se_save.setLoop(False)
        self.se_save.setVolume(self.master_volume * self.se_volume)

    def setupCamera(self) -> None:
        """
        init関数で最初に呼ばれる
        """
        # カメラの障害物検出用レイ
        self.camera_ray = CollisionRay()

        self.camera_ray_node = CollisionNode("camera-ray")
        self.camera_ray_node.addSolid(self.camera_ray)

        # 壁や床など、bit(1) のオブジェクトを検出
        self.camera_ray_node.setFromCollideMask(self.terrain_mask)
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

    def setupBackgroundEtc(self) -> None:
        """
        init関数で最初に呼ばれる
        """
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


        self.background = self.loadImage("Stroll_Title_Screen.png", scale=(1.0, 1.0, 1.0))
        self.background.reparentTo(self.bgnp)

        self.foreground1 = self.loadImage("Furvival_Foreground1.png", scale=(1.0, 1.0, 1.05))
        self.foreground1.reparentTo(fgnp)
        self.foreground1.setTransparency(True)

        self.explain_text = OnscreenText(
            text=self.title_text,
            parent=self.foreground1,
            pos=(-0.3, -0.93),
            scale=0.03,
            fg=(1, 1, 0, 0.5),
            font=self.game_font,
            align=TextNode.ACenter,
            mayChange=True,
        )

    def setupGravity(self) -> None:
        """
        init関数で最初に呼ばれる
        """
        # 物理システムの更新を有効化
        self.enableParticles()

        gravity_node = ForceNode("world-gravity")
        gravity_np = self.render.attachNewNode(gravity_node)

        self.gravity_force = LinearVectorForce(0, 0, self.force)
        gravity_node.addForce(self.gravity_force)

    def setupKey(self) -> None:
        """
        init関数で最初に呼ばれる
        """
        self.keys = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
            "space": False,
            "arrow_right": False,
            "arrow_left": False,
            "arrow_up": False,
            "arrow_down": False,
            "c": False
        }

        self.respown_point = self.player_pos

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

        self.accept("arrow_right", self.setKey, ["arrow_right", True])
        self.accept("arrow_right-up", self.setKey, ["arrow_right", False])

        self.accept("arrow_left", self.setKey, ["arrow_left", True])
        self.accept("arrow_left-up", self.setKey, ["arrow_left", False])

        self.accept("arrow_up", self.setKey, ["arrow_up", True])
        self.accept("arrow_up-up", self.setKey, ["arrow_up", False])

        self.accept("arrow_down", self.setKey, ["arrow_down", True])
        self.accept("arrow_down-up", self.setKey, ["arrow_down", False])

        self.accept("c", self.switchCameraMode)
        self.accept("f11", self.switchFullscreen)
        self.accept('escape',self.userExit)

    def setupPlayer(self) -> None:
        """
        startGame関数で呼ばれる
        
        着地判定や空中での壁衝突判定にはRayを使っているためその初期化も行う
        """
        # プレイヤーの半分の幅・奥行きと高さ
        half_x = 0.25
        half_y = 0.25
        height = 0.9
        padding = 0.05
        self.player = go.GameObject(parent=self.render, name="Furvival_Foco32", loader=self.loader, is_3d=False, use_gravity=True, physics_mgr=self.physicsMgr, gravity_force=self.gravity_force)
        self.player.setPos(0, 0, 2)
        self.player.createCollider("box", debug=self.debug, box_size=(-half_x, -half_y, 0, half_x, half_y, height))
        self.player.setCamera(self.cam)
        self.player_pos = self.player.getPos()

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

        # Ray による衝突判定
        # 16本の横向き Ray + 5本の下向き Ray
        self.ray_nodes = {}
        self.ray_queues = {}
        self.ray_traverser = CollisionTraverser()

        # Ray の定義: (名前, 原点オフセット, 方向)
        ray_defs = []

        # 横向き Ray：各側面の四隅
        for side_x, direction_x, label in [
            (half_x - padding, 1, "right"),
            (-half_x + padding, -1, "left"),
        ]:
            for y in (-half_y + padding, half_y - padding):
                for z in (0.05, height - 0.05):
                    ray_defs.append((
                        f"{label}_{y}_{z}",
                        (side_x, y, z),
                        (direction_x, 0, 0),
                    ))

        # Y方向の側面
        for side_y, direction_y, label in [
            (half_y - padding, 1, "front"),
            (-half_y + padding, -1, "back"),
        ]:
            for x in (-half_x + padding, half_x - padding):
                for z in (0.05, height - 0.05):
                    ray_defs.append((
                        f"{label}_{x}_{z}",
                        (x, side_y, z),
                        (0, direction_y, 0),
                    ))

        # 下向き Ray：四隅 + 中央
        for x, y, label in [
            (-half_x, -half_y, "bottom_bl"),
            (-half_x,  half_y, "bottom_tl"),
            ( half_x, -half_y, "bottom_br"),
            ( half_x,  half_y, "bottom_tr"),
            (0, 0, "bottom_center"),
        ]:
            ray_defs.append((
                label,
                (x, y, 0.1),
                (0, 0, -1),
            ))

        # Ray の生成と Traverser への登録
        for name, origin, direction in ray_defs:
            ray = CollisionRay()
            ray.setOrigin(*origin)
            ray.setDirection(*direction)

            node = CollisionNode(f"player-{name}")
            node.addSolid(ray)
            node.setFromCollideMask(self.terrain_mask)
            node.setIntoCollideMask(BitMask32.allOff())

            node_path = self.render.attachNewNode(node)
            queue = CollisionHandlerQueue()

            self.ray_nodes[name] = {
                "ray": ray,
                "node_path": node_path,
                "origin": origin,
                "direction": direction,
            }
            self.ray_queues[name] = queue

            self.ray_traverser.addCollider(node_path, queue)

        # 既存の影判定コードとの互換性を維持
        self.shadow_ray = self.ray_nodes["bottom_center"]["ray"]
        self.shadow_ray_np = self.ray_nodes["bottom_center"]["node_path"]
        self.shadow_queue = self.ray_queues["bottom_center"]
        self.shadow_traverser = self.ray_traverser

        # プレイヤー自身にはレイが当たらないようにする
        player_cnode = self.player.collider.collision_np.node()

        # プレイヤー自身は into 側として bit(0) を維持
        player_cnode.setIntoCollideMask(BitMask32.bit(0))

        # 物理衝突は地形だけを対象にする
        player_cnode.setFromCollideMask(self.terrain_mask)

        self.flower_sensor = CollisionNode("Furvival_Foco32")
        self.flower_sensor.addSolid(
            CollisionBox(
                Point3(-0.5, -0.5, 0),
                Point3(0.5, 0.5, 1.0),
            )
        )

        self.flower_sensor.setFromCollideMask(self.flower_mask)
        self.flower_sensor.setIntoCollideMask(BitMask32.allOff())

        self.flower_sensor_np = self.player.node.attachNewNode(
            self.flower_sensor
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

    def setupCollision(self) -> None:
        """
        startGame関数で呼ばれる
        """
        self.cTravEvent = CollisionTraverser()
        self.handler = CollisionHandlerEvent()

        self.handler.addInPattern("%fn-into")
        self.handler.addOutPattern("%fn-out")
        self.handler.addInPattern("%fn-into-%in")

        self.cTravEvent.addCollider(
            self.player.collider.collision_np,
            self.handler,
        )

        # 花検知センサーだけをイベント用に登録
        self.cTravEvent.addCollider(
            self.flower_sensor_np,
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
        self.accept(
            "Furvival_Foco32-out-Dance_Flower",
            self.onCollisionEndDanceFlower,
        )

        

    def switchFullscreen(self) -> None:
        """
        F11キーで呼ばれる関数
        """
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

    def switchCameraMode(self) -> None:
        """
        Cキーで呼ばれる関数
        """
        self.camera_constant_distance = not self.camera_constant_distance

    def onCollisionStartPlayer(self, entry):
        """
        プレイヤーとオブジェクトが衝突した時に呼ばれる関数
        """
        other = self.getGameObject(entry.getIntoNodePath())

        if other is None:
            return

        if self.is_wall:
            # 空中で壁に接触
            self.jump_count = max(self.jump_count, 1)
            self.player.setOnCollision(False)

        other.setOnCollision(True)

    def onCollisionEndPlayer(self, entry):
        """
        プレイヤーとオブジェクトがぶつかった状態から離れた時に呼ばれる関数
        """
        other = self.getGameObject(entry.getIntoNodePath())

        if other is None:
            return

        other.setOnCollision(False)

    def onCollisionRed(self, entry):
        """
        プレイヤーとRed(ゲームオブジェクト名)が衝突した時に呼ばれる関数
        """
        self.playerRespown()

    def onCollisionDanceFlower(self, entry):
        """
        プレイヤーとDanceFlower(ゲームオブジェクト)が衝突した時に呼ばれる関数
        """
        other = self.getGameObject(entry.getIntoNodePath())

        if other is None:
            return
        
        if self.flower is not None and self.flower != other:
            self.flower.sprite_animator.play(direction="front", motion="idle", loop=False)
            self.respown_point = other.getPos()
        if other.sprite_animator.play(direction="front", motion="dance", loop=True):
            self.flower = other
            self.flower.ignitionFunc()

        other.setOnCollision(True)

    def onCollisionEndDanceFlower(self, entry):
        """
        プレイヤーとDanceFlower(ゲームオブジェクト)が離れた時に呼ばれる関数
        """
        other = self.getGameObject(entry.getIntoNodePath())
        
        if other is None:
            return

        other.setOnCollision(False)

    def getRayDistance(self, name: str) -> float | None:
        """
        指定したレイの最も近い衝突位置までの距離を返す
        """
        queue = self.ray_queues[name]

        if queue.getNumEntries() == 0:
            return None

        entry = queue.getEntry(0)
        hit_pos = entry.getSurfacePoint(self.render)
        ray_origin = self.ray_nodes[name]["ray"].getOrigin()

        return (hit_pos - ray_origin).length()


    def classifyPlayerCollision(self) -> tuple[bool, bool, object | None]:
        """
        レイの結果から、地面・壁との接触を判定する
        """
        a = 0.125  # 水平方向のレイのしきい値
        b = 0.75  # 下方向のレイのしきい値

        horizontal_names = [
            name for name in self.ray_nodes
            if not name.startswith("bottom_")
        ]
        bottom_names = [
            name for name in self.ray_nodes
            if name.startswith("bottom_")
        ]

        # 水平方向のレイのうち、近くに衝突物があるもの
        near_wall_rays = [
            name for name in horizontal_names
            if (
                (distance := self.getRayDistance(name)) is not None
                and distance <= a
            )
        ]

        # 下向きのレイのうち、地面が近いもの
        near_ground_rays = [
            name for name in bottom_names
            if (
                (distance := self.getRayDistance(name)) is not None
                and distance <= b
            )
        ]

        # 中央の下向きレイが地面から遠いか
        center_distance = self.getRayDistance("bottom_center")
        center_far_from_ground = (
            center_distance is None or center_distance > b
        )

        # 中央の下向きレイが地面から近いか
        center_distance = self.getRayDistance("bottom_center")
        center_near_ground = (
            center_distance is not None and center_distance <= b
        )

        # 地面が近く、水平レイがすべて遠い場合
        # または中央の下向きレイが基準値以下の場合は着地
        is_ground = (
            (
                len(near_ground_rays) > 0
                and len(near_wall_rays) == 0
            )
            or center_near_ground
        )

        # 空中で壁に接触している場合
        is_wall = (
            len(near_wall_rays) > 0
            and center_far_from_ground
        )

        # 壁キック用の法線。レイの進行方向と逆向きにする
        wall_normal = None

        if is_wall:
            ray_data = self.ray_nodes[near_wall_rays[0]]
            dx, dy, dz = ray_data["direction"]

            wall_normal = Vec3(-dx, -dy, 0)
            wall_normal.normalize()

        return is_ground, is_wall, wall_normal

    def getGameObject(self, node: NodePath) -> go.GameObject | None:
        """
        NodePathからGameObjectを返す

        衝突判定で渡されるentryはNodePathでGameObjectインスタンスではないためこれを使う
        """
        while not node.isEmpty():
            if node.hasPythonTag("game_object"):
                return node.getPythonTag("game_object")
            node = node.getParent()

        return None

    def loadImage(self, image_name: str, scale: tuple[float, float, float]) -> OnscreenImage:
        """
        背景や前景読み込み用関数
        """
        img_path = path.image_path(image_name)
        if not img_path.exists():
            raise FileNotFoundError(f"Image file not found: {img_path}")

        texture = self.loader.loadTexture(img_path)
        if texture is None:
            raise RuntimeError(f"Texture loading failed: {img_path}")
        
        return OnscreenImage(image=texture, scale=scale)
        
    def setBackground(self, number: int) -> None:
        """
        背景を変更する際に使う関数
        """
        data = self.background_data["backgrounds"][str(number)]
        texture = self.loader.loadTexture(path.image_path(data["name"]))
        self.background.setTexture(texture, 1)
        self.background.setScale(tuple(data["scale"]))

        color = data["color"]
        self.light1.setColor((
            color["r"],
            color["g"],
            color["b"],
            color["a"],
        ))

    def playerRespown(self) -> None:
        """
        落下やRedに衝突した時に呼ばれる関数
        """
        self.player.setPos(self.respown_point.x, self.respown_point.y, self.respown_point.z)
        self.player.actor_node.getPhysicsObject().setVelocity(
        Vec3(0, 0, 0)
        )
        self.jump_count  = 2
        self.jump = False
        self.playBack()

    def playJump(self) -> None:
        """
        音を流す
        """
        self.se_jump.play()

    def playBack(self) -> None:
        """
        音を流す
        """
        self.se_back.play()

    def playSave(self) -> None:
        """
        音を流す
        """
        self.se_save.play()

    def playClear(self) -> None:
        """
        音を流す
        """
        self.clear_bgm.play()

    def playTitle(self) -> None:
        """
        音を流す
        """
        self.title_bgm.play()

    def stopTitle(self) -> None:
        """
        音を止める
        """
        self.title_bgm.stop()

    def playBGM(self) -> None:
        """
        音を流す
        """
        self.game_bgm.play()
    
    def stopBGM(self) -> None:
        """
        音を止める
        """
        self.game_bgm.stop()

    def gameClear(self) -> None:
        """
        クリア時の処理
        """
        self.disableMovementKeys()
        self.clear = True

        # BGMがなければ、そのままクリアSEを再生
        if self.game_bgm is None:
            self.playClear()
            return

        self.bgm_start_volume = self.game_bgm.getVolume()
        self.bgm_fade_duration = 2.0
        self.bgm_fade_elapsed = 0.0

        self.taskMgr.add(
            self.fadeOutBGM,
            "fadeOutBGM",
        )

    def showClearText(self) -> None:
        """
        クリア時にテキストを表示する
        """
        total_seconds = int(self.game_time)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        text = f"Finished!\nYour time: {hours} h {minutes} m {seconds} s!"
        self.clear_text = OnscreenText(
            text=text,
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
        """
        クリア時に移動系キー入力を無効化する
        """
        for key in ("w", "s", "a", "d", "space"):
            self.ignore(key)
            self.ignore(f"{key}-up")
        self.keys["up"] = False
        self.keys["down"] = False
        self.keys["left"] = False
        self.keys["right"] = False
        self.keys["space"] = False

    def centerMouse(self) -> None:
        """
        Panda3dのスクリーン内にあるマウスポインタを画面中央に移動させる
        """
        self.mouse_center_x = self.win.getXSize() // 2
        self.mouse_center_y = self.win.getYSize() // 2

        self.win.movePointer(
            0,
            self.mouse_center_x,
            self.mouse_center_y,
        )


    def fadeOutBGM(self, task: Task) -> int:
        """
        BGMを時間とともにフェードアウトさせる関数
        """
        dt = ClockObject.getGlobalClock().getDt()
        self.bgm_fade_elapsed += dt

        progress = min(
            self.bgm_fade_elapsed / self.bgm_fade_duration,
            1.0,
        )

        self.game_bgm.setVolume(
            self.bgm_start_volume * (1.0 - progress)
        )

        if progress >= 1.0:
            self.stopBGM()
            self.playClear()
            self.showClearText()
            return Task.done

        return Task.cont

    def updatePlayerContactState(self) -> None:
        """
        update関数で呼ばれる

        移動系処理に使う変数を更新する
        """
        is_ground, is_wall, wall_normal = self.classifyPlayerCollision()

        physical = self.player.actor_node.getPhysicsObject()
        velocity = physical.getVelocity()

        self.is_ground = is_ground
        self.is_wall = is_wall
        self.wall_normal = wall_normal

        # 地面が近く、上昇中ではない場合だけ着地を確定する
        landed = is_ground and velocity.z <= 0

        if landed:
            self.jump_count = 2
            self.jump = False
            self.player.setOnCollision(True)
        else:
            self.player.setOnCollision(False)

    def playerMove(self, dt: float) -> None:
        """
        update関数で呼ばれる

        カメラの方向に合わせた移動をさせる
        プレイヤーのモーションを更新する
        """
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
            # 壁に接触していて、移動入力がなければ停止
            if (
                self.is_wall
                and not self.keys["space"]
                and input_x == 0
                and input_y == 0
            ):
                self.dx = 0.0
                self.dy = 0.0
            else:
                next_dx = self.dx + move_x / self.inertia
                next_dy = self.dy + move_y / self.inertia

                speed = math.hypot(next_dx, next_dy)
                if speed > 1:
                    scale = 1 / speed
                    next_dx *= scale
                    next_dy *= scale

                self.dx = next_dx
                self.dy = next_dy

            # 壁に向かう移動成分を除去
            if self.is_wall and self.wall_normal is not None:
                normal = self.wall_normal

                move_dot = (
                    self.dx * normal.x
                    + self.dy * normal.y
                )

                if move_dot < 0:
                    self.dx -= move_dot * normal.x
                    self.dy -= move_dot * normal.y
        else:
            self.dx = move_x
            self.dy = move_y

        if (
            self.keys["space"]
            and self.jump_count > 0
            and self.jump_cooltime <= 0
        ):
            velocity.z = 0
            self.jump_count -= 1
            self.jump_cooltime = 0.3

            # 空中で壁に接触している場合は壁キック
            wall_jump = (
                self.jump
                and not self.is_ground
                and self.is_wall
                and self.wall_normal is not None
            )

            if wall_jump:
                normal = self.wall_normal

                # 壁から離れる方向へ蹴る
                self.dx = normal.x
                self.dy = normal.y
                dz = 0.8
            else:
                dz = 1.0

            self.jump = True

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
        """
        update関数で呼ばれる

        プレイヤーの足元の影の位置を更新したり、表示・非表示の切り替えを行う
        """
        if self.shadow_queue.getNumEntries() > 0:
            # 最も近い地面との交点を取得
            entry = self.shadow_queue.getEntry(0)
            self.ground_pos = entry.getSurfacePoint(self.render)

            # 影を地面の少し上に置く
            self.player.shadow_node.setPos(
                self.render,
                Point3(
                    self.player_pos.x,
                    self.player_pos.y,
                    self.ground_pos.z + 0.02,
                ),
            )

            self.player.shadow_node.show()
        else:
            # 地面がなければ影を消す
            self.player.shadow_node.hide()

    def updatePlayerRays(self) -> None:
        """
        update関数で呼ばれる

        Rayの更新
        """
        for data in self.ray_nodes.values():
            ox, oy, oz = data["origin"]

            data["ray"].setOrigin(
                self.player_pos.x + ox,
                self.player_pos.y + oy,
                self.player_pos.z + oz,
            )

        # 21本の Ray をまとめて判定
        for queue in self.ray_queues.values():
            queue.clearEntries()

        self.ray_traverser.traverse(self.render)

        for queue in self.ray_queues.values():
            queue.sortEntries()
    
    def cameraMove(self, dt: float):
        """
        update関数で呼ばれる

        カメラの位置や角度を更新
        """
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
            int(self.keys["arrow_right"])
            - int(self.keys["arrow_left"])
            
        )

        self.camera_angle += (
            rotate_input * self.camera_rotate_speed * dt
        )
        self.camera_angle += mouse_dx * self.mouse_sensitivity

        # 上下の回転：矢印キー + マウス
        pitch_input = (
            int(self.keys["arrow_up"])
            - int(self.keys["arrow_down"])
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
        angle = math.radians(self.camera_angle)
        pitch = math.radians(self.camera_pitch)

        horizontal_distance = self.camera_distance * math.cos(pitch)
        vertical_offset = self.camera_distance * math.sin(pitch)

        offset_x = -horizontal_distance * math.sin(angle)
        offset_y = -horizontal_distance * math.cos(angle)

        desired_camera_pos = Point3(
            self.player_pos.x + offset_x,
            self.player_pos.y + offset_y,
            self.player_pos.z + self.camera_height + vertical_offset,
        )

        # プレイヤーの少し上を、レイの始点にする
        target = Point3(
            self.player_pos.x,
            self.player_pos.y,
            self.player_pos.z + 0.5,
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
        if not self.camera_constant_distance:
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
        self.player_pos.z += 0.5
        self.cam.lookAt(self.player_pos)

        # 背景のスクロール
        offset_x = (
            self.player_pos.x - self.background_start_x
        ) * 0.005
        self.background.setX(-offset_x)

        offset_z = (
            self.player_pos.z - self.background_start_z
        ) * 0.005
        self.background.setZ(-offset_z)


    def update(self, _task: Task) -> None:
        """
        startGame関数で呼ばれる

        更新が必要な関数を呼び出す
        title_screen_controller terrain playerのupdate関数もここで呼ぶ
        """
        if self.title:
            self.title_screen_controller.update()
        else:
            dt = ClockObject.getGlobalClock().getDt()
            if not self.clear:
                self.game_time += dt

            if self.jump_cooltime >= 0:
                self.jump_cooltime -= dt
                    
            if self.player_pos.z < -5:
                self.playerRespown()

            self.cTrav.traverse(self.render)
            self.cTravEvent.traverse(self.render)

            self.player.update(dt)
            self.terrain.update(dt)
            self.updatePlayerRays()
            self.updatePlayerContactState()
            self.playerShadow(dt)
            self.playerMove(dt)
            self.player_pos = self.player.getPos()
            self.cameraMove(dt)

        return Task.cont

    def setKey(self, key, value):
        self.keys[key] = value
    

    def exit(self):
        self.taskMgr.remove(self.taskMgr.getAllTasks())
        self.destroy()
