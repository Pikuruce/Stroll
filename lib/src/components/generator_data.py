import lib.src.components.game_object as go
from typing import Any

from panda3d.core import (
    NodePath,
    CardMaker,
    TransparencyAttrib,
)

def plane(offset: tuple[float, float, float],
        point1: tuple[float, float, float],
        point2: tuple[float, float, float], 
        parent: NodePath,
        loader: Any,
        name: str,
        is_3d: bool = True,
        use_gravity: bool = False,
        physics_mgr=None,
        gravity_force=None) -> list[go.GameObject]:
    obj_list = []
    for x in range(offset[0], offset[0] + int(point2[0] - point1[0]), 2):
        for y in range(offset[1], offset[1] + int(point2[1] - point1[1]), 2):
            for z in range(offset[2], offset[2] + int(point2[2] - point1[2]), 2):
                obj = go.GameObject(parent=parent, loader=loader, name=name, is_3d=is_3d, use_gravity=use_gravity, physics_mgr=physics_mgr, gravity_force=gravity_force)
                obj.setPos(x, y, z)
                obj_list.append(obj)
    return obj_list
# list[tuple[float: x, float: y, float: z, int]] int: 0: Grass
planes = [(0, 0, 0, 0), (2, 0, 0, 0), (0, 2, 0, 0), (0, -2, 0, 0), (2, 2, 0, 0), (2, -2, 0, 0)]