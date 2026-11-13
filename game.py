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
        self.collisions = self.tilemap.load_collisions()
        self.npcs = self.tilemap.load_npcs()

        self.camera.set_bounds(self.tilemap.width, self.tilemap.height)

        spawn_position = self.tilemap.get_spawn("PlayerSpawn")

        self.player = Player(spawn_position.x, spawn_position.y, self.pointer)
        self.player.set_bounds(self.tilemap.width, self.tilemap.height)
        self.player.set_collisions(self.collisions)

        self.dialog = DialogWindow(self.screen_width, self.screen_height)

    def change_map(self, map_path, spawn_name):
        new_map = TiledMap(f"assets/maps/{map_path}", scale=2)

        spawn = new_map.tmx.get_object_by_name(spawn_name)

        if spawn is None:
            raise ValueError(f"Spawn point '{spawn_name}' not found!")

        self.tilemap = new_map
        self.triggers = self.tilemap.load_triggers()
        self.collisions = new_map.load_collisions()
        self.npcs = self.tilemap.load_npcs()

        self.camera.set_bounds(new_map.width, new_map.height)

        self.player.pos = pygame.Vector2(
            spawn.x * new_map.scale, spawn.y * new_map.scale
        )

        self.player.rect.center = self.player.pos
        self.player.set_bounds(new_map.width, new_map.height)
        self.player.set_collisions(self.collisions)

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

        for npc in self.npcs:
            npc.update(dt)

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
        for npc in self.npcs:
            npc.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)

        player_screen_pos = self.camera.apply(self.player.rect).center
        self.pointer.draw(self.screen, player_screen_pos)

        for trigger in self.triggers:
            trigger.draw_debug(self.screen, self.camera)

        self.dialog.draw(self.screen)

        # Collision debug
        for collision in self.collisions:
            collision.draw_debug(self.screen, self.camera)

    def start(self):
        while self.running:
            dt = self.set_fps(60)

            self.event_listener()
            self.update(dt)
            self.draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()
