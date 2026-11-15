import pygame
import pytmx
import xml.etree.ElementTree as ET
from collision import CollisionShape
from trigger import Trigger
from npc import NPC
from entity_database import EntityDatabase


class TiledMap:
    def __init__(self, filename, scale=4):
        self.filename = filename

        self.tmx = pytmx.load_pygame(filename)

        self.scale = scale

        self.entity_database = EntityDatabase()

        self.width = self.tmx.width * self.tmx.tilewidth * self.scale

        self.height = self.tmx.height * self.tmx.tileheight * self.scale

        self.scaled_tiles = {}

        # Read ellipse markers directly from TMX XML.
        root = ET.parse(filename).getroot()

        self.ellipse_ids = {
            int(obj.get("id"))
            for obj in root.findall(".//object")
            if obj.find("ellipse") is not None
        }

        self.object_classes = {
            int(obj.get("id")): obj.get("class", obj.get("type", ""))
            for obj in root.findall(".//object")
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
            shape = self.load_object_shape(obj)

            trigger = Trigger(
                shape=shape,
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
            shape = self.load_object_shape(obj)
            collisions.append(shape)

        return collisions

    def get_spawn(self, name="PlayerSpawn"):
        spawn = self.tmx.get_object_by_name(name)

        if spawn is None:
            raise ValueError(f"Spawn point '{name}' not found in {self.filename}")

        return pygame.Vector2(spawn.x * self.scale, spawn.y * self.scale)

    def load_object_shape(self, obj):
        x = obj.x * self.scale
        y = obj.y * self.scale
        width = obj.width * self.scale
        height = obj.height * self.scale

        # Ellipse
        if obj.id in self.ellipse_ids:
            return CollisionShape(
                shape_type="ellipse",
                rect=(
                    round(x),
                    round(y),
                    round(width),
                    round(height),
                ),
            )

        # Polygon
        elif hasattr(obj, "points") and obj.closed:
            transformed_points = obj.apply_transformations()

            points = [
                (
                    round(point[0] * self.scale),
                    round(point[1] * self.scale),
                )
                for point in transformed_points
            ]

            return CollisionShape(
                shape_type="polygon",
                points=points,
            )

        # Rectangle
        return CollisionShape(
            shape_type="rect",
            rect=(
                round(x),
                round(y),
                round(width),
                round(height),
            ),
        )

    def load_npcs(self):
        npcs = []
        paths = self.load_npc_paths()

        try:
            layer = self.tmx.get_layer_by_name("Entities")
        except ValueError:
            return npcs

        for obj in layer:
            object_class = self.object_classes.get(obj.id, "")

            if object_class != "NPC":
                continue

            entity_id = obj.properties.get("entity_id")

            if not entity_id:
                raise ValueError(f"NPC '{obj.name}' has no entity_id property!")

            # Tiled properties override the JSON definition.
            overrides = {
                key: value
                for key, value in obj.properties.items()
                if key != "entity_id"
            }

            config = self.entity_database.get("npc", entity_id, overrides)

            sprite = config.get("sprite")

            if not sprite:
                raise ValueError(f"NPC '{entity_id}' has no sprite configured!")

            path_name = config.get("path", "")

            if config.get("movement") == "path":
                if path_name not in paths:
                    raise ValueError(
                        f"NPC '{entity_id}' references " f"missing path '{path_name}'"
                    )

            npc = NPC(
                x=obj.x * self.scale,
                y=obj.y * self.scale,
                name=obj.name or entity_id,
                sprite=sprite,
                direction=config.get("direction", "down"),
                dialogue=config.get("dialogue", ""),
                movement=config.get("movement", "static"),
                speed=float(config.get("speed", 60)),
                patrol_distance=float(config.get("patrol_distance", 64)) * self.scale,
                pause_duration=float(config.get("pause_duration", 1.5)),
                path=paths.get(path_name, []),
                can_be_damaged=config.get("can_be_damaged", False),
                max_hp=int(config.get("max_hp", 100)),
                interact_range=float(config.get("interact_range", 48)) * self.scale,
            )

            npcs.append(npc)

        return npcs

    def load_npc_paths(self):
        paths = {}

        root = ET.parse(self.filename).getroot()

        layer = root.find("./objectgroup[@name='NPCPaths']")

        if layer is None:
            return paths

        for obj in layer.findall("object"):
            # Check Polyline first
            path_element = obj.find("polyline")

            # If not a Polyline, check Polygon
            if path_element is None:
                path_element = obj.find("polygon")

            if path_element is None:
                continue

            name = obj.get("name", "")

            if not name:
                continue

            origin_x = float(obj.get("x", 0))
            origin_y = float(obj.get("y", 0))

            points = []

            for pair in path_element.get("points", "").split():
                x, y = map(float, pair.split(","))

                points.append(
                    pygame.Vector2(
                        (origin_x + x) * self.scale,
                        (origin_y + y) * self.scale,
                    )
                )

            if len(points) >= 2:
                paths[name] = points

        return paths
