import pygame


class AnimatedSprite:
    def __init__(self, frames, speed=0.2, loop=True):
        self.frames = frames
        self.speed = speed
        self.loop = loop

        self.frame_index = 0
        self.timer = 0

        self.image = self.frames[0]
        self.finished = False

    def update(self, dt):
        if self.finished:
            return

        self.timer += dt

        while self.timer >= self.speed:
            self.timer -= self.speed

            if self.frame_index < len(self.frames) - 1:
                self.frame_index += 1
            elif self.loop:
                self.frame_index = 0
            else:
                self.finished = True
                self.timer = 0
                break

            self.image = self.frames[self.frame_index]

    def reset(self):
        self.frame_index = 0
        self.timer = 0
        self.image = self.frames[0]
        self.finished = False

    @property
    def mask(self):
        return pygame.mask.from_surface(self.image)
