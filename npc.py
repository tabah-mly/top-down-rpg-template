import os
import pygame

from animated_sprite import AnimatedSprite
from spritesheet import SpriteSheet
from collision import CollisionBox


class NPC:
    def __init__(
        self,
        x,
        y,
        name,
        sprite,
        direction="down",
        dialogue="",
        movement="static",
        speed=60,
        patrol_distance=64,
        pause_duration=1.5,
        path=None,
        can_be_damaged=False,
        max_hp=100,
        interact_range=48,
    ):
        self.name = name
        self.sprite = sprite
        self.dialogue = dialogue

        self.animations = {}

        directions = ["up", "down", "left", "right"]
        states = ["idle", "walk"]

        sprite_path = f"assets/imgs/sprites/{sprite}"

        for state in states:
            for direction_name in directions:
                key = f"{state}_{direction_name}"

                frames = SpriteSheet(
                    os.path.join(sprite_path, f"{key}.png"), 20, 26, scale=3
                ).frames

                self.animations[key] = AnimatedSprite(frames, speed=0.1)

        self.state = "idle"
        self.facing = direction if direction in directions else "down"

        self.animator = self.animations[f"{self.state}_{self.facing}"]

        self.pos = pygame.Vector2(x, y)

        self.rect = self.animator.image.get_rect(center=(x, y))

        self.body_collider = CollisionBox(width=24, height=16, offset=(0, 25))

        self.hurtbox = CollisionBox(width=30, height=42, offset=(0, 10))

        self.update_collision_boxes()

        self.movement = movement
        self.speed = speed
        self.patrol_distance = patrol_distance
        self.pause_duration = pause_duration

        self.path = [pygame.Vector2(point) for point in (path or [])]

        self.path_index = 0

        self.start_pos = self.pos.copy()
        self.travelled = 0
        self.direction_sign = 1
        self.pause_timer = 0

        self.movement_direction = {
            "up": pygame.Vector2(0, -1),
            "down": pygame.Vector2(0, 1),
            "left": pygame.Vector2(-1, 0),
            "right": pygame.Vector2(1, 0),
        }[self.facing]

        self.player = None

        # Combat properties
        self.can_be_damaged = can_be_damaged
        self.max_hp = max_hp
        self.hp = max_hp

        # Interaction
        self.interact_range = interact_range

    def update(self, dt):
        if self.movement == "path":
            self.update_path_movement(dt)
        else:
            self.update_movement(dt)
        self.animator.update(dt)

    def draw(self, surface, camera, interact_icon=None):
        screen_rect = camera.apply(self.rect)

        # Draw NPC
        surface.blit(self.animator.image, screen_rect)

        # Draw interaction icon
        if interact_icon:
            icon_rect = interact_icon.get_rect(
                midbottom=(screen_rect.centerx, screen_rect.top - 5)
            )

            surface.blit(interact_icon, icon_rect)

    def draw_interaction_prompt(self, surface, npc_rect):
        font = pygame.font.Font(None, 20)

        text = font.render("E", True, (255, 255, 255))

        prompt_rect = pygame.Rect(0, 0, 26, 24)

        prompt_rect.midbottom = (
            npc_rect.centerx,
            npc_rect.top - 8,
        )

        # Background
        pygame.draw.rect(
            surface,
            (35, 28, 48),
            prompt_rect,
            border_radius=5,
        )

        # Border
        pygame.draw.rect(
            surface,
            (255, 200, 100),
            prompt_rect,
            width=2,
            border_radius=5,
        )

        surface.blit(
            text,
            text.get_rect(center=prompt_rect.center),
        )

    def can_interact(self, player_rect):
        player_pos = pygame.Vector2(player_rect.center)
        npc_pos = pygame.Vector2(self.rect.center)

        return player_pos.distance_to(npc_pos) <= self.interact_range

    def set_animation(self, state, facing=None):
        if facing is None:
            facing = self.facing

        if state != self.state or facing != self.facing:
            self.state = state
            self.facing = facing

            self.animator = self.animations[f"{self.state}_{self.facing}"]
            self.animator.reset()

    def update_movement(self, dt):
        if self.movement != "patrol":
            self.set_animation("idle")
            return

        # Pause at patrol endpoints
        if self.pause_timer > 0:
            self.pause_timer -= dt
            self.set_animation("idle")
            return

        direction = self.movement_direction * self.direction_sign
        movement = self.speed * dt

        if not self.move(direction * movement):
            self.set_animation("idle")
            return

        self.travelled += movement

        if self.travelled >= self.patrol_distance:
            self.direction_sign *= -1
            self.travelled = 0
            self.pause_timer = self.pause_duration

        facing = self.facing

        if direction.x > 0:
            facing = "right"
        elif direction.x < 0:
            facing = "left"
        elif direction.y > 0:
            facing = "down"
        elif direction.y < 0:
            facing = "up"

        self.set_animation("walk", facing)

    def update_path_movement(self, dt):
        if not self.path:
            self.set_animation("idle")
            return

        # Wait at each waypoint
        if self.pause_timer > 0:
            self.pause_timer = max(0, self.pause_timer - dt)
            self.set_animation("idle")
            return

        target = self.path[self.path_index]
        direction = target - self.pos
        distance = direction.length()

        # Reached the waypoint
        if distance <= 0.5:
            self.pos = target.copy()
            self.rect.center = self.pos
            self.update_collision_boxes()

            self.path_index = (self.path_index + 1) % len(self.path)

            self.pause_timer = self.pause_duration
            self.set_animation("idle")
            return

        # Move without overshooting the target
        movement = min(self.speed * dt, distance)

        if movement <= 0:
            self.set_animation("idle")
            return

        direction = direction.normalize()

        if not self.move(direction * movement):
            self.set_animation("idle")
            return

        # Determine facing direction
        if abs(direction.x) > abs(direction.y):
            facing = "right" if direction.x > 0 else "left"
        else:
            facing = "down" if direction.y > 0 else "up"

        self.set_animation("walk", facing)

    def update_collision_boxes(self):
        self.body_collider.update(self.pos)
        self.hurtbox.update(self.pos)

    def draw_collision_debug(self, surface, camera):
        self.body_collider.draw_debug(surface, camera, (0, 255, 0))

        self.hurtbox.draw_debug(surface, camera, (255, 0, 255))

    def set_player(self, player):
        self.player = player

    def can_move_to(self, position):
        if self.player is None:
            return True

        candidate = self.body_collider.rect.copy()

        target_center = pygame.Vector2(position) + self.body_collider.offset
        candidate.center = round(target_center.x), round(target_center.y)

        return not candidate.colliderect(self.player.body_collider.rect)

    def move(self, movement):
        target_position = self.pos + movement

        if not self.can_move_to(target_position):
            return False

        self.pos = target_position
        self.rect.center = self.pos
        self.update_collision_boxes()

        return True
