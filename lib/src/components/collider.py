from panda3d.core import (
    CollisionNode,
    CollisionSphere,
    CollisionBox,
    Point3,
    NodePath,
    BitMask32,
)

class Collider:
    def __init__(
        self,
        parent: NodePath,
        name: str,
        collision_type: str,
        debug: bool,
        sphere_size: tuple = (0, 0, 0.5, 0.45),
        box_size: tuple = (-1.0, -1.0, -1.0, 1.0, 1.0, 1.0),
        into_mask: BitMask32 = BitMask32.bit(1),
    ):
        self.collision_node = CollisionNode(name)

        if collision_type == "sphere":
            self.solid = CollisionSphere(
                sphere_size[0],
                sphere_size[1],
                sphere_size[2],
                sphere_size[3],
            )
        elif collision_type == "box":
            p1 = Point3(*box_size[:3])
            p2 = Point3(*box_size[3:])
            self.solid = CollisionBox(p1, p2)
        else:
            raise ValueError(
                f"Unsupported collision type: {collision_type}"
            )

        self.collision_node.addSolid(self.solid)
        self.collision_node.setIntoCollideMask(into_mask)
        self.collision_np = parent.attachNewNode(
            self.collision_node
        )

        if debug:
            self.collision_np.show()