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

    def draw(self, surface, camera):
        surface.blit(self.animator.image, camera.apply(self.rect))
