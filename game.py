import pygame, sys
import pygame, random, math
from camera import Camera
from player import Player
from pointer import Pointer
from tiled_map import TiledMap
from dialog import DialogWindow


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
        self.tilemap = TiledMap("assets/maps/level0.tmx", scale=2)
        self.triggers = self.tilemap.load_triggers()

        self.camera.set_bounds(self.tilemap.width, self.tilemap.height)

        self.player = Player(
            self.tilemap.width // 2, self.tilemap.height // 2, self.pointer
        )
        self.player.set_bounds(self.tilemap.width, self.tilemap.height)

        self.dialog = DialogWindow(self.screen_width, self.screen_height)

    def change_map(self, map_path, spawn_name):
        new_map = TiledMap(f"assets/maps/{map_path}", scale=2)

        spawn = new_map.tmx.get_object_by_name(spawn_name)

        if spawn is None:
            raise ValueError(f"Spawn point '{spawn_name}' not found!")

        self.tilemap = new_map
        self.triggers = self.tilemap.load_triggers()

        self.camera.set_bounds(self.tilemap.width, self.tilemap.height)

        self.player.pos = pygame.Vector2(
            spawn.x * self.tilemap.scale, spawn.y * self.tilemap.scale
        )

        self.player.rect.center = self.player.pos

    def event_listener(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if self.dialog.active:
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.dialog.advance()

    def restart(self):
        self.__init__(self.screen_width, self.screen_height, self.screen_title)

    def set_fps(self, frame=60):
        dt = self.clock.tick(frame) / 1000
        return min(dt, 0.05)

    def update(self, dt):
        if self.dialog.active:
            return

        self.player.update(dt, self.camera)
        self.camera.follow(self.player.rect)

        for trigger in self.triggers:
            if trigger.update(self.player.rect):
                if trigger.action == "print":
                    print(f"[TRIGGER] {trigger.name}: " f"{trigger.message}")
                if trigger.action == "transition":
                    self.change_map(trigger.target_map, trigger.target_spawn)
                    break
                elif trigger.action == "dialog":
                    self.dialog.open(trigger.message)
                    break

    def draw(self):
        self.screen.fill((0, 0, 0))

        self.tilemap.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)

        player_screen_pos = self.camera.apply(self.player.rect).center
        self.pointer.draw(self.screen, player_screen_pos)

        for trigger in self.triggers:
            trigger.draw_debug(self.screen, self.camera)

        self.dialog.draw(self.screen)

    def start(self):
        while self.running:
            dt = self.set_fps(60)

            self.event_listener()
            self.update(dt)
            self.draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()
