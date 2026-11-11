import pygame
import pytmx
from trigger import Trigger


class TiledMap:
    def __init__(self, filename, scale=4):
        self.tmx = pytmx.load_pygame(filename)

        self.scale = scale

        self.width = self.tmx.width * self.tmx.tilewidth * self.scale

        self.height = self.tmx.height * self.tmx.tileheight * self.scale

        self.scaled_tiles = {}

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

    def load_triggers(self):
        triggers = []

        layer = self.tmx.get_layer_by_name("Triggers")

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
            )

            triggers.append(trigger)

        return triggers
