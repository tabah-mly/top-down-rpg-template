import pygame


class Trigger:
    def __init__(
        self,
        rect,
        name="",
        event="enter",
        action="print",
        message="",
        once=False,
    ):
        self.rect = pygame.Rect(rect)
        self.name = name
        self.event = event
        self.action = action
        self.message = message
        self.once = once

        self.inside = False
        self.activated = False

    def update(self, target_rect):
        is_inside = self.rect.colliderect(target_rect)

        entered = is_inside and not self.inside
        exited = self.inside and not is_inside

        activated = False

        if not (self.once and self.activated):
            if self.event == "enter" and entered:
                activated = True
            elif self.event == "exit" and exited:
                activated = True
            elif self.event == "stay" and is_inside:
                activated = True

        self.inside = is_inside

        if activated:
            self.activated = True

        return activated

    def draw_debug(self, surface, camera):
        rect = camera.apply(self.rect)

        pygame.draw.rect(surface, (255, 200, 0), rect, 2)
