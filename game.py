import pygame, sys
import pygame, random, math
from camera import Camera
from font_manager import FontManager
from player import Player
from pointer import Pointer
from tiled_map import TiledMap
from dialog import DialogWindow
from enemy import Enemy


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

        self.font_manager = FontManager()
        self.font_manager.load("main", "assets/fonts/PixelifySans-Regular.ttf")

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
        self.player.set_npcs(self.npcs)

        enemy_config = self.tilemap.entity_database.get("enemy", "skeleton")

        self.enemies = [
            Enemy(900, 300, "Skeleton", enemy_config)
        ]

        for enemy in self.enemies:
            enemy.set_player(self.player)
            enemy.set_collisions(self.collisions)

        for npc in self.npcs:
            npc.set_player(self.player)

        self.dialog = DialogWindow(self.screen_width, self.screen_height, self.font_manager)

        interact_icon = pygame.image.load(
            "assets/imgs/system/interact.png"
        ).convert_alpha()

        self.interact_icon = pygame.transform.scale_by(interact_icon, 2)

        self.debug_collisions = True

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
        self.player.set_npcs(self.npcs)

        for npc in self.npcs:
            npc.set_player(self.player)

    def interact_with_npc(self):
        npc = self.get_nearby_npc()

        if npc and npc.dialogue:
            self.dialog.open(npc.dialogue)

    def get_nearby_npc(self):
        nearby_npcs = [npc for npc in self.npcs if npc.can_interact(self.player.rect)]

        if not nearby_npcs:
            return None

        player_pos = pygame.Vector2(self.player.rect.center)

        return min(nearby_npcs, key=lambda npc: player_pos.distance_to(npc.rect.center))

    def event_listener(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if self.dialog.active:
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.dialog.advance()

                elif event.key == pygame.K_e:
                    self.interact_with_npc()

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

        for enemy in self.enemies:
            enemy.update(dt)

        for trigger in self.triggers:
            if trigger.update(self.player.body_collider.rect):
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
        nearby_npc = None

        if not self.dialog.active:
            nearby_npc = self.get_nearby_npc()

        for npc in self.npcs:
            npc.draw(
                self.screen,
                self.camera,
                interact_icon=(self.interact_icon if npc == nearby_npc else None),
            )
        
        for enemy in self.enemies:
            enemy.draw(self.screen, self.camera)

            if self.debug_collisions and enemy.is_debug:
                enemy.draw_collision_debug(self.screen, self.camera)

        self.player.draw(self.screen, self.camera)

        player_screen_pos = self.camera.apply(self.player.rect).center
        self.pointer.draw(self.screen, player_screen_pos)

        for trigger in self.triggers:
            trigger.draw_debug(self.screen, self.camera)

        self.dialog.draw(self.screen)

        # Collision debug
        for collision in self.collisions:
            collision.draw_debug(self.screen, self.camera)

        if self.debug_collisions:
            self.player.draw_collision_debug(self.screen, self.camera)

            for npc in self.npcs:
                npc.draw_collision_debug(self.screen, self.camera)

    def start(self):
        while self.running:
            dt = self.set_fps(60)

            self.event_listener()
            self.update(dt)
            self.draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()
