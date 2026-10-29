from direct.gui.OnscreenText import OnscreenText
import inspect
import direct.gui.OnscreenText
from panda3d.core import (

    TextNode,
)

class TitleScreen():
    def __init__(self, game):
        self.game = game
        self.game.playTitle()
        self.title_text = OnscreenText(
            text=f"Athletic Stroll",
            parent=self.game.foreground1,
            pos=(0, 0.7),
            scale=0.2,
            fg=(1, 0.5, 0, 1),
            font=self.game.game_font,
            align=TextNode.ACenter,
            mayChange=True,
        )
        start_text = OnscreenText(
            text=f"Start",
            parent=self.game.foreground1,
            pos=(0, -0.2),
            scale=0.07,
            fg=(1, 1, 0, 1),
            font=self.game.game_font,
            align=TextNode.ACenter,
            mayChange=True,
        )
        debug_mode_text = OnscreenText(
            text=f"Displaying hitboxes: {"ON" if self.game.debug else "OFF"}",
            parent=self.game.foreground1,
            pos=(0, -0.4),
            scale=0.07,
            fg=(1, 0, 0, 1),
            font=self.game.game_font,
            align=TextNode.ACenter,
            mayChange=True,
        )
        bulk_load_text = OnscreenText(
            text=f"Bulk loading of terrain: {"ON" if self.game.bulk_load else "OFF"}",
            parent=self.game.foreground1,
            pos=(0, -0.3),
            scale=0.07,
            fg=(1, 0, 0, 1),
            font=self.game.game_font,
            align=TextNode.ACenter,
            mayChange=True,
        )
        self.options = [start_text, bulk_load_text, debug_mode_text]
        self.upkey_down = False
        self.downkey_down = False
        self.leftkey_down = False
        self.rightkey_down = False
        self.pointer = 0

    def detectKeyDown(self) -> None:
        """
        update関数で呼ばれる

        キーの押された瞬間だけ実行させるための関数
        """
        if self.game.keys["up"] and not self.upkey_down:
            self.selectText(-1)
            self.upkey_down = True
        elif not self.game.keys["up"] and self.upkey_down:
            self.upkey_down = False

        if self.game.keys["down"] and not self.downkey_down:
            self.selectText(1)
            self.downkey_down = True
        elif not self.game.keys["down"] and self.downkey_down:
            self.downkey_down = False

        if self.game.keys["left"] and not self.leftkey_down:
            self.changeContent()
            self.leftkey_down = True
        elif not self.game.keys["left"] and self.leftkey_down:
            self.leftkey_down = False

        if self.game.keys["right"] and not self.rightkey_down:
            self.changeContent()
            self.rightkey_down = True
        elif not self.game.keys["right"] and self.rightkey_down:
            self.rightkey_down = False

        if self.game.keys["space"] and self.pointer == 0:
            self.game.playSave()
            self.title_text.hide()
            for text in self.options:
                text.hide()
            self.game.title = False
            self.game.stopTitle()
            self.game.startGame()

    def selectText(self, dp: int) -> None:
        """
        WキーとSキーで呼ばれる
        """
        self.game.playJump()
        self.options[self.pointer].setFg((1, 0, 0, 1))

        self.pointer = (
            self.pointer + dp + len(self.options)
        ) % len(self.options)

        self.options[self.pointer].setFg((1, 1, 0, 1))

    def changeContent(self) -> None:
        """
        AキーとDキーで呼ばれる
        """
        if self.pointer == 0:
            return
        elif self.pointer == 1:
            self.game.playJump()
            self.options[self.pointer].setText(f"Bulk loading of terrain: {"ON" if self.game.changeBulkLoad() else "OFF"}")
        elif self.pointer == 2:
            self.game.playJump()
            self.options[self.pointer].setText(f"Displaying hitboxes: {"ON" if self.game.changeDebug() else "OFF"}")

    def update(self):
        """
        game.pyのupdate関数内で呼ばれる
        """
        self.detectKeyDown()