import os
import pygame

from animated_sprite import AnimatedSprite
from spritesheet import SpriteSheet
from collision import CollisionBox


class Enemy:
    def __init__(self, x, y, name, config, path=None):
        self.name = name
        self.config = config

        # --------------------------------------------------
        # Basic properties
        # --------------------------------------------------

        self.pos = pygame.Vector2(x, y)

        self.max_hp = int(config.get("max_hp", 100))
        self.hp = self.max_hp

        self.damage = float(config.get("damage", 10))
        self.speed = float(config.get("speed", 60))

        self.alive = True
        self.can_be_damaged = True

        # --------------------------------------------------
        # Sprite configuration
        # --------------------------------------------------

        sprite = config["sprite"]

        frame_width = int(config.get("frame_width", 20))
        frame_height = int(config.get("frame_height", 26))
        sprite_scale = int(config.get("sprite_scale", 3))

        animation_speed = float(config.get("animation_speed", 0.1))

        sprite_path = f"assets/imgs/sprites/{sprite}"

        self.animations = {}

        for state in ["idle", "walk", "attack"]:
            frames = SpriteSheet(
                os.path.join(sprite_path, f"{state}.png"),
                frame_width,
                frame_height,
                scale=sprite_scale,
            ).frames

            self.animations[state] = AnimatedSprite(
                frames, speed=animation_speed, loop=(state != "attack")
            )

        self.state = "idle"

        # Default direction: right
        self.facing = "right"

        self.animator = self.animations[self.state]

        self.rect = self.animator.image.get_rect(center=self.pos)

        # --------------------------------------------------
        # Collision configuration
        # --------------------------------------------------

        body_config = config.get("body_collider", {})
        hurtbox_config = config.get("hurtbox", {})

        self.body_collider = CollisionBox(
            width=int(body_config.get("width", 24)),
            height=int(body_config.get("height", 16)),
            offset=body_config.get("offset", (0, 25)),
        )

        self.hurtbox = CollisionBox(
            width=int(hurtbox_config.get("width", 30)),
            height=int(hurtbox_config.get("height", 42)),
            offset=hurtbox_config.get("offset", (0, 10)),
        )

        self.update_collision_boxes()

        # --------------------------------------------------
        # Movement configuration
        # --------------------------------------------------

        self.movement = config.get("movement", "static")

        self.patrol_distance = float(config.get("patrol_distance", 64))

        self.pause_duration = float(config.get("pause_duration", 1.5))

        self.pause_timer = 0

        self.start_pos = self.pos.copy()
        self.travelled = 0
        self.direction_sign = 1

        patrol_direction = config.get("patrol_direction", "right")

        self.movement_direction = {
            "up": pygame.Vector2(0, -1),
            "down": pygame.Vector2(0, 1),
            "left": pygame.Vector2(-1, 0),
            "right": pygame.Vector2(1, 0),
        }[patrol_direction]

        self.path = [pygame.Vector2(point) for point in (path or [])]

        self.path_index = 0

        # --------------------------------------------------
        # References
        # --------------------------------------------------

        self.player = None
        self.collisions = []

        # Debug
        self.is_debug = True

    # ======================================================
    # Update
    # ======================================================

    def update(self, dt):
        if not self.alive:
            return

        if self.state == "attack":
            self.animator.update(dt)

            if self.animator.finished:
                self.set_animation("idle")

            return

        if self.movement == "path":
            self.update_path_movement(dt)

        elif self.movement == "patrol":
            self.update_patrol_movement(dt)

        else:
            self.set_animation("idle")

        self.animator.update(dt)

    # ======================================================
    # Drawing
    # ======================================================

    def draw(self, surface, camera):
        if not self.alive:
            return

        image = self.animator.image

        if self.facing == "left":
            image = pygame.transform.flip(image, True, False)

        surface.blit(image, camera.apply(self.rect))

    # ======================================================
    # Animation
    # ======================================================

    def set_animation(self, state):
        if state == self.state:
            return

        self.state = state
        self.animator = self.animations[state]
        self.animator.reset()

    def set_facing(self, direction):
        if direction == "right":
            self.facing = "right"

        elif direction == "left":
            self.facing = "left"

        # Up/down intentionally do nothing.

    # ======================================================
    # Collision
    # ======================================================

    def update_collision_boxes(self):
        self.body_collider.update(self.pos)
        self.hurtbox.update(self.pos)

    def draw_collision_debug(self, surface, camera):
        self.body_collider.draw_debug(surface, camera, (0, 255, 0))

        self.hurtbox.draw_debug(surface, camera, (255, 0, 255))

    def set_player(self, player):
        self.player = player

    def set_collisions(self, collisions):
        self.collisions = collisions

    def can_move_to(self, position):
        candidate = self.body_collider.rect.copy()

        target_center = pygame.Vector2(position) + self.body_collider.offset

        candidate.center = (round(target_center.x), round(target_center.y))

        # Check map obstacles
        for collision in self.collisions:
            if collision.collides(candidate):
                return False

        # Check player
        if self.player is not None:
            if candidate.colliderect(self.player.body_collider.rect):
                return False

        return True

    def move(self, movement):
        target_position = self.pos + movement

        if not self.can_move_to(target_position):
            return False

        self.pos = target_position
        self.rect.center = self.pos

        self.update_collision_boxes()

        return True

    # ======================================================
    # Movement
    # ======================================================

    def update_patrol_movement(self, dt):
        if self.pause_timer > 0:
            self.pause_timer = max(0, self.pause_timer - dt)
            self.set_animation("idle")
            return

        direction = self.movement_direction * self.direction_sign
        movement = self.speed * dt

        if not self.move(direction * movement):
            self.direction_sign *= -1
            self.travelled = 0
            self.pause_timer = self.pause_duration
            self.set_animation("idle")
            return

        self.travelled += movement

        if self.travelled >= self.patrol_distance:
            self.direction_sign *= -1
            self.travelled = 0
            self.pause_timer = self.pause_duration
            self.set_animation("idle")
            return

        if direction.x > 0:
            self.set_facing("right")
        elif direction.x < 0:
            self.set_facing("left")

        self.set_animation("walk")

    def update_path_movement(self, dt):
        if not self.path:
            self.set_animation("idle")
            return

        if self.pause_timer > 0:
            self.pause_timer = max(0, self.pause_timer - dt)
            self.set_animation("idle")
            return

        target = self.path[self.path_index]

        direction = target - self.pos
        distance = direction.length()

        if distance <= 0.5:
            self.pos = target.copy()
            self.rect.center = self.pos
            self.update_collision_boxes()

            self.path_index = (self.path_index + 1) % len(self.path)

            self.pause_timer = self.pause_duration
            self.set_animation("idle")
            return

        movement = min(self.speed * dt, distance)

        if movement <= 0:
            self.set_animation("idle")
            return

        direction = direction.normalize()

        if not self.move(direction * movement):
            self.set_animation("idle")
            return

        if abs(direction.x) > abs(direction.y):
            self.set_facing("right" if direction.x > 0 else "left")

        self.set_animation("walk")

    # ======================================================
    # Combat
    # ======================================================

    def take_damage(self, amount):
        if not self.alive or not self.can_be_damaged:
            return

        self.hp = max(0, self.hp - amount)

        print(f"{self.name} took {amount} damage. " f"HP: {self.hp}/{self.max_hp}")

        if self.hp <= 0:
            self.die()

    def die(self):
        self.alive = False
        print(f"{self.name} died.")

    def start_attack(self):
        if not self.alive:
            return

        if self.state == "attack":
            return

        self.set_animation("attack")