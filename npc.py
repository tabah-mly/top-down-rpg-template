import os
import pygame

from animated_sprite import AnimatedSprite
from spritesheet import SpriteSheet


class NPC:
    def __init__(self, x, y, name, sprite, direction="down", dialogue=""):
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

    def update(self, dt):
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

        prompt_rect = pygame.Rect(
            0,
            0,
            26,
            24,
        )

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

    def can_interact(self, player_rect, distance=90):
        player_pos = pygame.Vector2(player_rect.center)
        npc_pos = pygame.Vector2(self.rect.center)

        return player_pos.distance_to(npc_pos) <= distance
