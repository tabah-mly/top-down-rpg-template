import os
import pygame

from animated_sprite import AnimatedSprite
from spritesheet import SpriteSheet
from collision import CollisionBox
from debug import DEBUG, BODY_COLLISION_COLOR, HURTBOX_COLOR, ENEMY_ATTACK_RANGE_COLOR


class Enemy:
    # Share immutable sprite frames between enemies of the same visual type.
    # This prevents loading and slicing the same PNG hundreds of times in waves.
    _frame_cache = {}

    def __init__(self, x, y, name, config, path=None):
        self.name = name
        self.config = config

        # --------------------------------------------------
        # Basic properties
        # --------------------------------------------------

        self.pos = pygame.Vector2(x, y)

        # Mission files use the explicit fixed value "hp". Older Tiled/entity
        # definitions can continue using "max_hp" for backward compatibility.
        self.max_hp = int(config.get("hp", config.get("max_hp", 100)))
        self.hp = self.max_hp
        self.is_boss = bool(config.get("is_boss", False))

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
            sheet_path = os.path.abspath(os.path.join(sprite_path, f"{state}.png"))
            cache_key = (sheet_path, frame_width, frame_height, sprite_scale)
            frames = self._frame_cache.get(cache_key)

            if frames is None:
                frames = SpriteSheet(
                    sheet_path,
                    frame_width,
                    frame_height,
                    scale=sprite_scale,
                ).frames
                self._frame_cache[cache_key] = frames

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

        self.aggro_range = float(config.get("aggro_range", 280))
        self.aggro_mode = str(config.get("aggro_mode", "proximity")).lower()
        if self.aggro_mode not in ("proximity", "always"):
            self.aggro_mode = "proximity"
        self.attack_range = float(config.get("attack_range", 48))
        # Offset is relative to the enemy's sprite center. The horizontal
        # component mirrors when the enemy faces left, keeping the range
        # centered in front of the enemy when its facing direction changes.
        self.attack_range_offset = pygame.Vector2(
            config.get("attack_range_offset", (0, 0))
        )
        self.attack_cooldown = float(config.get("attack_cooldown", 1.4))
        self.attack_timer = 0.0

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
        self.is_debug = DEBUG

    # ======================================================
    # Update
    # ======================================================

    def update(self, dt):
        if not self.alive:
            return

        self.attack_timer = max(0.0, self.attack_timer - dt)

        # Finish the current attack animation before choosing another action.
        if self.state == "attack":
            self.animator.update(dt)
            if self.animator.finished:
                self.set_animation("idle")
            return

        if self.movement == "chase" and self.player is not None:
            self.update_chase_movement(dt)
        elif self.movement == "path":
            self.update_path_movement(dt)
        elif self.movement == "patrol":
            self.update_patrol_movement(dt)
        else:
            self.set_animation("idle")

        self.animator.update(dt)

    def update_chase_movement(self, dt):
        direction = self.player.pos - self.pos
        distance = direction.length()

        # Proximity enemies wait until Leonhard enters their aggro radius.
        # Always-aggressive enemies pursue him from any distance.
        if self.aggro_mode == "proximity" and distance > self.aggro_range:
            self.set_animation("idle")
            return

        if abs(direction.x) > 1:
            self.set_facing("right" if direction.x > 0 else "left")

        # Measure attack distance from the configurable attack-range origin,
        # not necessarily from the center of the sprite.
        attack_center = self.get_attack_range_center()
        attack_distance = self.player.pos.distance_to(attack_center)

        if attack_distance <= self.attack_range:
            self.set_animation("idle")
            if self.attack_timer <= 0:
                self.start_attack()
                self.player.take_damage(self.damage)
                self.attack_timer = self.attack_cooldown
            return

        direction = direction.normalize()
        moved = self.move(direction * self.speed * dt)
        self.set_animation("walk" if moved else "idle")

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

    def get_attack_range_center(self):
        """Return the world-space center of the enemy's attack range."""
        offset = self.attack_range_offset.copy()
        if self.facing == "left":
            offset.x *= -1
        return self.pos + offset

    def draw_collision_debug(self, surface, camera):
        if not self.alive:
            return

        self.body_collider.draw_debug(surface, camera, BODY_COLLISION_COLOR)
        self.hurtbox.draw_debug(surface, camera, HURTBOX_COLOR)

        # Enemy melee damage is applied when the player center is within
        # attack_range of the enemy center. Show the range during its attack
        # animation so large waves do not become cluttered with range circles.
        if self.state == "attack":
            range_center = self.get_attack_range_center()
            screen_pos = range_center - camera.offset
            pygame.draw.circle(
                surface,
                ENEMY_ATTACK_RANGE_COLOR,
                (round(screen_pos.x), round(screen_pos.y)),
                round(self.attack_range),
                2,
            )

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

        self.hp = max(0, self.hp - int(amount))

        print(f"{self.name} took {amount} damage. " f"HP: {self.hp}/{self.max_hp}")

        if self.hp <= 0:
            self.die()

    def die(self):
        self.alive = False
        self.can_be_damaged = False
        print(f"{self.name} died.")

    def start_attack(self):
        if not self.alive:
            return

        if self.state == "attack":
            return

        self.set_animation("attack")