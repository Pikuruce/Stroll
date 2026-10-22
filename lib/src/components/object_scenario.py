import lib.src.components.game_object as go

def straight(target: go.GameObject, x, y, z, s):
    pos = target.getPos()
    target.setPos(pos.x + x * s, pos.y + y * s, pos.z + z * s)
