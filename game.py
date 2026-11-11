import pygame, sys
import pygame, random, math
from camera import Camera
from player import Player
from pointer import Pointer
from tiled_map import TiledMap


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
        self.tilemap = TiledMap("assets/maps/level_0/map.tmx", scale=2)

        self.camera.set_bounds(self.tilemap.width, self.tilemap.height)

        self.player = Player(
            self.tilemap.width // 2, self.tilemap.height // 2, self.pointer
        )
        self.player.set_bounds(self.tilemap.width, self.tilemap.height)

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

        self.tilemap.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)

        player_screen_pos = self.camera.apply(self.player.rect).center
        self.pointer.draw(self.screen, player_screen_pos)

    def start(self):
        while self.running:
            dt = self.set_fps(60)

            self.event_listener()
            self.update(dt)
            self.draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()
