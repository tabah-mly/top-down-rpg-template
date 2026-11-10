import pygame, sys
from background import InfiniteBackground
from camera import Camera
from player import Player
import pygame, random, math

from pointer import Pointer


class Game:
    def __init__(self, width, height, title):
        pygame.init()
        self.screen_width = width
        self.screen_height = height
        self.screen_title = title

        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), display=1
        )
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()

        self.running = True

        self.pointer = Pointer()
        self.camera = Camera(self.screen_width, self.screen_height)
        self.background = InfiniteBackground("assets/imgs/bg.png", 5)

        self.player = Player(width // 2, height // 2, self.pointer)

    def event_listener(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def restart(self):
        self.__init__(self.screen_width, self.screen_height, self.screen_title)

    def set_fps(self, frame=60):
        dt = self.clock.tick(frame) / 1000
        return min(dt, 0.05)

    def update(self, dt):
        self.player.update(dt, self.camera)
        self.camera.follow(self.player.rect)

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.background.draw(self.screen, self.camera.offset)
        self.player.draw(self.screen, self.camera)
        self.pointer.draw(self.screen)

    def start(self):
        while self.running:
            dt = self.set_fps(60)

            self.event_listener()
            self.update(dt)
            self.draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()
