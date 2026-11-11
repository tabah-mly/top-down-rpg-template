
import pygame


class Camera:
    def __init__(self, width, height):
        self.offset = pygame.Vector2(0, 0)
        self.width = width
        self.height = height

        self.bounds = None

    def set_bounds(self, map_width, map_height):
        self.bounds = pygame.Rect(
            0, 0,
            map_width,
            map_height
        )

    def follow(self, target_rect):
        self.offset.x = target_rect.centerx - self.width / 2
        self.offset.y = target_rect.centery - self.height / 2

        if self.bounds:
            # Horizontal boundaries
            if self.bounds.width <= self.width:
                self.offset.x = (self.bounds.width - self.width) / 2
            else:
                self.offset.x = max(
                    self.bounds.left,
                    min(self.offset.x, self.bounds.right - self.width)
                )

            # Vertical boundaries
            if self.bounds.height <= self.height:
                self.offset.y = (self.bounds.height - self.height) / 2
            else:
                self.offset.y = max(
                    self.bounds.top,
                    min(self.offset.y, self.bounds.bottom - self.height)
                )

    def apply(self, rect):
        return rect.move(
            -self.offset.x,
            -self.offset.y
        )
