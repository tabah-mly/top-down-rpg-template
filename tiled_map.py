
import pygame
import pytmx
import xml.etree.ElementTree as ET

from collision import CollisionShape
from trigger import Trigger


class TiledMap:
    def __init__(self, filename, scale=4):
        self.filename = filename

        self.tmx = pytmx.load_pygame(filename)

        self.scale = scale

        self.width = (
            self.tmx.width *
            self.tmx.tilewidth *
            self.scale
        )

        self.height = (
            self.tmx.height *
            self.tmx.tileheight *
            self.scale
        )

        self.scaled_tiles = {}

        # Read ellipse markers directly from TMX XML.
        root = ET.parse(filename).getroot()

        self.ellipse_ids = {
            int(obj.get("id"))
            for obj in root.findall(".//object")
            if obj.find("ellipse") is not None
        }

    # ========================================================
    # Draw Map
    # ========================================================

    def draw(self, surface, camera):
        for layer in self.tmx.visible_layers:

            if isinstance(layer, pytmx.TiledTileLayer):

                for x, y, gid in layer:

                    if gid == 0:
                        continue

                    image = self.tmx.get_tile_image_by_gid(gid)

                    if image is None:
                        continue

                    if gid not in self.scaled_tiles:
                        self.scaled_tiles[gid] = pygame.transform.scale(
                            image,
                            (
                                image.get_width() * self.scale,
                                image.get_height() * self.scale,
                            ),
                        )

                    image = self.scaled_tiles[gid]

                    rect = image.get_rect(
                        topleft=(
                            x * self.tmx.tilewidth * self.scale,
                            y * self.tmx.tileheight * self.scale,
                        )
                    )

                    surface.blit(image, camera.apply(rect))

    # ========================================================
    # Load Triggers
    # ========================================================

    def load_triggers(self):
        triggers = []

        try:
            layer = self.tmx.get_layer_by_name("Triggers")
        except ValueError:
            return triggers

        for obj in layer:

            rect = pygame.Rect(
                round(obj.x * self.scale),
                round(obj.y * self.scale),
                round(obj.width * self.scale),
                round(obj.height * self.scale),
            )

            trigger = Trigger(
                rect=rect,
                name=obj.name or "",
                event=obj.properties.get("event", "enter"),
                action=obj.properties.get("action", "print"),
                message=obj.properties.get("message", ""),
                once=obj.properties.get("once", False),
                target_map=obj.properties.get("target_map"),
                target_spawn=obj.properties.get("target_spawn"),
            )

            triggers.append(trigger)

        return triggers

    # ========================================================
    # Load Collisions
    # ========================================================

    def load_collisions(self):
        collisions = []

        try:
            layer = self.tmx.get_layer_by_name("Collisions")
        except ValueError:
            return collisions

        for obj in layer:

            x = obj.x * self.scale
            y = obj.y * self.scale
            width = obj.width * self.scale
            height = obj.height * self.scale

            # --------------------------------------------
            # Ellipse
            # --------------------------------------------

            if obj.id in self.ellipse_ids:

                shape = CollisionShape(
                    shape_type="ellipse",
                    rect=(
                        round(x),
                        round(y),
                        round(width),
                        round(height),
                    ),
                )

            # --------------------------------------------
            # Polygon
            # --------------------------------------------

            elif hasattr(obj, "points") and obj.closed:

                # apply_transformations() returns absolute
                # coordinates and accounts for rotation.
                transformed_points = obj.apply_transformations()

                points = [
                    (
                        round(point[0] * self.scale),
                        round(point[1] * self.scale),
                    )
                    for point in transformed_points
                ]

                shape = CollisionShape(
                    shape_type="polygon",
                    points=points,
                )

            # --------------------------------------------
            # Rectangle
            # --------------------------------------------

            else:

                shape = CollisionShape(
                    shape_type="rect",
                    rect=(
                        round(x),
                        round(y),
                        round(width),
                        round(height),
                    ),
                )

            collisions.append(shape)

        return collisions
