"""Standalone developer room for inspecting Aetherveil enemy profiles.

Run from the project root:
    python enemy_test.py

This uses the same TiledMap, Player, Enemy, EntityDatabase, spritesheets,
collision boxes, and animation classes as the main game. It does not modify
story state, mission state, or the main menu.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

from camera import Camera
from enemy import Enemy
from font_manager import FontManager
from player import Player
from pointer import Pointer
from tiled_map import TiledMap


SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
MAP_PATH = Path("assets/maps/prologue_first_assault.tmx")
MAP_SCALE = 2
FONT_PATH = "assets/fonts/PixelifySans-Regular.ttf"

PANEL_BG = (12, 15, 22, 222)
PANEL_BORDER = (119, 105, 82)
TEXT = (235, 231, 218)
MUTED = (167, 171, 180)
ACCENT = (235, 197, 126)
FRAME_COLOR = (190, 190, 190)
VISIBLE_COLOR = (65, 225, 205)
HP_COLOR = (225, 92, 82)


class EnemyTestRoom:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Aetherveil — Enemy Test Room")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), display=1)
        self.clock = pygame.time.Clock()
        self.running = True

        if not MAP_PATH.exists():
            raise FileNotFoundError(
                f"Test map not found: {MAP_PATH}. Run this script from the Aetherveil project root."
            )

        # The database loads the same JSON profiles used by the missions.
        self.tilemap = TiledMap(str(MAP_PATH), scale=MAP_SCALE)
        self.database = self.tilemap.entity_database
        self.collisions = self.tilemap.load_collisions()

        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.camera.set_bounds(self.tilemap.width, self.tilemap.height)

        self.fonts = FontManager()
        self.fonts.load("main", FONT_PATH)
        self.font = self.fonts.get("main", 19)
        self.small_font = self.fonts.get("main", 15)
        self.tiny_font = self.fonts.get("main", 13)
        self.heading_font = self.fonts.get("main", 25)

        self.pointer = Pointer()
        self.pointer.is_active = False
        self.pointer.ranged = False
        pygame.mouse.set_visible(True)

        self.player_config = self.database.get("player", "leonhard")
        spawn = self.tilemap.get_spawn("PlayerSpawn")
        self.player = Player(
            spawn.x,
            spawn.y,
            self.pointer,
            character="leonhard",
            config=self.player_config,
        )
        self.player.set_bounds(self.tilemap.width, self.tilemap.height)
        self.player.set_collisions(self.collisions)
        self.player.set_npcs([])

        self.camera.follow(self.player.rect)

        self.enemy_profiles = []
        self.refresh_profiles()
        self.selected_index = self.find_initial_enemy()
        self.enemy = None
        self.enemy_config = None
        self.default_scale = 3
        self.preview_scale = 3
        self.ai_enabled = False
        self.debug_enabled = True
        self.show_measurements = True
        self.status_message = "Ready — enemy profiles loaded from JSON"
        self.status_timer = 3.0
        self.spawn_selected_enemy()

    def refresh_profiles(self):
        """Re-read profile JSON so F5 can pick up edits without restarting."""
        # Reconstructing EntityDatabase through TiledMap would also reload the
        # map. Instead, reload its categories in place from the same folder.
        from entity_database import EntityDatabase

        self.database = EntityDatabase()
        profiles = []
        for category in ("enemy", "boss"):
            definitions = self.database.entities.get(category, {})
            for entity_id, config in definitions.items():
                if config.get("sprite"):
                    profiles.append((category, entity_id, config))
        profiles.sort(key=lambda item: (item[0] != "enemy", item[1]))
        self.enemy_profiles = profiles

        # Keep the current player profile in sync with the latest player JSON.
        self.player_config = self.database.get("player", "leonhard")

    def find_initial_enemy(self):
        for index, (category, entity_id, _) in enumerate(self.enemy_profiles):
            if entity_id == "orc_assault_minion":
                return index
        return 0

    def set_status(self, message, seconds=2.0):
        self.status_message = message
        self.status_timer = seconds

    def _candidate_position(self, config):
        body = config.get("body_collider", {})
        body_w = int(body.get("width", 24))
        body_h = int(body.get("height", 16))
        offset = body.get("offset", (0, 25))
        ox, oy = float(offset[0]), float(offset[1])

        directions = [
            (230, 0), (-230, 0), (0, 230), (0, -230),
            (190, 150), (-190, 150), (190, -150), (-190, -150),
            (300, 0), (-300, 0), (0, 300), (0, -300),
        ]

        for dx, dy in directions:
            x = self.player.pos.x + dx
            y = self.player.pos.y + dy
            rect = pygame.Rect(0, 0, body_w, body_h)
            rect.center = (round(x + ox), round(y + oy))

            if not (40 <= x <= self.tilemap.width - 40 and 40 <= y <= self.tilemap.height - 40):
                continue
            if rect.colliderect(self.player.body_collider.rect.inflate(80, 80)):
                continue
            if any(collision.collides(rect) for collision in self.collisions):
                continue
            return pygame.Vector2(x, y)

        # Fallback: put it to the player's right. The test room is not a
        # mission spawn simulation; this is only a visual inspection point.
        return self.player.pos + pygame.Vector2(230, 0)

    def spawn_selected_enemy(self):
        if not self.enemy_profiles:
            raise RuntimeError("No enemy or boss profiles were found in data/entities.")

        category, entity_id, source_config = self.enemy_profiles[self.selected_index]
        config = dict(source_config)
        self.default_scale = max(1, int(config.get("sprite_scale", 3)))
        self.preview_scale = self.default_scale
        config["sprite_scale"] = self.preview_scale
        config["aggro_mode"] = config.get("aggro_mode", "always")
        config["is_boss"] = category == "boss"

        position = self._candidate_position(config)
        self.enemy = Enemy(
            x=position.x,
            y=position.y,
            name=entity_id,
            config=config,
        )
        self.enemy.set_collisions(self.collisions)
        self.enemy.set_player(self.player if self.ai_enabled else None)
        self.enemy.is_boss = category == "boss"
        self.enemy.enemy_type = entity_id
        self.enemy_config = config
        self.player.set_enemies([self.enemy])

        self.camera.follow(self.player.rect)
        self.set_status(f"Loaded {category.upper()}: {entity_id}")

    def change_selection(self, direction):
        if not self.enemy_profiles:
            return
        self.selected_index = (self.selected_index + direction) % len(self.enemy_profiles)
        self.spawn_selected_enemy()

    def adjust_scale(self, amount):
        new_scale = max(1, min(12, self.preview_scale + amount))
        if new_scale == self.preview_scale:
            return
        self.preview_scale = new_scale
        self.enemy_config["sprite_scale"] = new_scale
        self.spawn_selected_enemy_with_scale(new_scale)

    def spawn_selected_enemy_with_scale(self, scale):
        category, entity_id, source_config = self.enemy_profiles[self.selected_index]
        config = dict(source_config)
        config["sprite_scale"] = scale
        config["aggro_mode"] = config.get("aggro_mode", "always")
        config["is_boss"] = category == "boss"
        position = self._candidate_position(config)
        self.enemy = Enemy(position.x, position.y, entity_id, config)
        self.enemy.set_collisions(self.collisions)
        self.enemy.set_player(self.player if self.ai_enabled else None)
        self.enemy.is_boss = category == "boss"
        self.enemy.enemy_type = entity_id
        self.enemy_config = config
        self.player.set_enemies([self.enemy])
        self.set_status(f"Preview scale: {scale}× (profile default: {self.default_scale}×)")

    def reload_profiles(self):
        current_id = self.enemy_profiles[self.selected_index][1] if self.enemy_profiles else None
        self.refresh_profiles()
        self.selected_index = next(
            (i for i, (_, entity_id, _) in enumerate(self.enemy_profiles) if entity_id == current_id),
            self.find_initial_enemy(),
        )
        self.ai_enabled = False
        self.spawn_selected_enemy()
        self.set_status("JSON profiles reloaded from disk")

    def toggle_ai(self):
        self.ai_enabled = not self.ai_enabled
        self.enemy.set_player(self.player if self.ai_enabled else None)
        self.set_status("Enemy AI: ON" if self.ai_enabled else "Enemy AI: OFF — stationary preview")

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.key in (pygame.K_RIGHT, pygame.K_PERIOD, pygame.K_KP6):
            self.change_selection(1)
        elif event.key in (pygame.K_LEFT, pygame.K_COMMA, pygame.K_KP4):
            self.change_selection(-1)
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.adjust_scale(1)
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.adjust_scale(-1)
        elif event.key == pygame.K_0:
            self.spawn_selected_enemy()
            self.set_status("Restored profile's default sprite scale")
        elif event.key == pygame.K_r:
            self.spawn_selected_enemy()
        elif event.key == pygame.K_F1:
            self.toggle_ai()
        elif event.key == pygame.K_F2:
            self.debug_enabled = not self.debug_enabled
            self.set_status("Collision debug: ON" if self.debug_enabled else "Collision debug: OFF")
        elif event.key == pygame.K_F3:
            self.show_measurements = not self.show_measurements
        elif event.key == pygame.K_F5:
            self.reload_profiles()

    def update(self, dt):
        self.player.update(dt, self.camera)
        self.camera.follow(self.player.rect)

        if self.enemy and self.enemy.alive:
            self.enemy.update(dt)

        self.status_timer = max(0.0, self.status_timer - dt)

    def draw_measurement(self, entity, color):
        image = entity.animator.image
        screen_rect = self.camera.apply(entity.rect)
        visible_rect = image.get_bounding_rect(min_alpha=1)

        # Frame outline shows the complete sprite cell; cyan shows only the
        # non-transparent pixels currently visible inside that frame.
        pygame.draw.rect(self.screen, FRAME_COLOR, screen_rect, 1)
        if visible_rect.width and visible_rect.height:
            visible_screen_rect = visible_rect.move(screen_rect.topleft)
            pygame.draw.rect(self.screen, color, visible_screen_rect, 2)

        return screen_rect.size, visible_rect.size

    def draw_character_layer(self):
        entities = [self.player]
        if self.enemy and self.enemy.alive:
            entities.append(self.enemy)
        entities.sort(key=lambda entity: entity.body_collider.rect.bottom)

        for entity in entities:
            if entity is self.player:
                self.player.draw_sprites(self.screen, self.camera)
            else:
                self.enemy.draw(self.screen, self.camera)

        self.player.draw_attack(self.screen, self.camera)

    def draw_panel(self, rect, border=PANEL_BORDER):
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill(PANEL_BG)
        self.screen.blit(panel, rect.topleft)
        pygame.draw.rect(self.screen, border, rect, 1)

    def draw_text(self, text, x, y, font=None, color=TEXT):
        font = font or self.font
        self.screen.blit(font.render(str(text), True, color), (x, y))

    def draw_hud(self):
        if not self.show_measurements:
            return

        left_panel = pygame.Rect(18, 16, 370, 254)
        self.draw_panel(left_panel)

        category, entity_id, profile = self.enemy_profiles[self.selected_index]
        frame_size, visible_size = self.draw_measurement(self.enemy, VISIBLE_COLOR) if self.enemy else ((0, 0), (0, 0))
        player_frame, player_visible = self.draw_measurement(self.player, ACCENT)

        self.draw_text("ENEMY TEST ROOM", 32, 27, self.heading_font, ACCENT)
        self.draw_text(
            f"Profile {self.selected_index + 1}/{len(self.enemy_profiles)}  ·  {category.upper()}",
            32, 63, self.small_font, MUTED,
        )
        self.draw_text(entity_id, 32, 85, self.font, TEXT)
        self.draw_text(f"Sprite: {profile.get('sprite', '?')}", 32, 113, self.small_font)
        self.draw_text(
            f"Frame: {frame_size[0]}×{frame_size[1]} px  |  Visible: {visible_size[0]}×{visible_size[1]} px",
            32, 137, self.small_font,
        )
        self.draw_text(
            f"Scale: {self.preview_scale}×  (profile: {self.default_scale}×)",
            32, 161, self.small_font, ACCENT if self.preview_scale != self.default_scale else TEXT,
        )
        self.draw_text(
            f"Leonhard visible: {player_visible[0]}×{player_visible[1]} px",
            32, 185, self.small_font, MUTED,
        )

        if self.enemy:
            self.draw_text(
                f"HP: {self.enemy.hp}/{self.enemy.max_hp}   Damage: {self.enemy.damage:g}   Speed: {self.enemy.speed:g}",
                32, 211, self.small_font,
            )

        right_panel = pygame.Rect(SCREEN_WIDTH - 310, 16, 292, 254)
        self.draw_panel(right_panel)
        self.draw_text("CONTROLS", right_panel.x + 14, 27, self.heading_font, ACCENT)
        controls = [
            ("← / →", "Previous / next enemy"),
            ("+ / -", "Preview sprite scale"),
            ("0 / R", "Default scale / respawn"),
            ("F1", "Toggle enemy AI"),
            ("F2", "Collision + hurtbox debug"),
            ("F3", "Hide / show measurements"),
            ("F5", "Reload JSON profiles"),
            ("W A S D", "Move Leonhard"),
            ("Mouse 1", "Melee attack"),
            ("Esc", "Exit test room"),
        ]
        y = right_panel.y + 64
        for key, label in controls:
            self.draw_text(key, right_panel.x + 14, y, self.tiny_font, ACCENT)
            self.draw_text(label, right_panel.x + 86, y, self.tiny_font)
            y += 18

        # Small player HP indicator, useful while testing enemy AI.
        hp_text = f"LEONHARD  {self.player.stats['hp']} / {self.player.stats['max_hp']} HP"
        self.draw_text(hp_text, SCREEN_WIDTH // 2 - 110, 20, self.small_font, TEXT)

        if self.status_timer > 0:
            status = self.small_font.render(self.status_message, True, ACCENT)
            status_rect = status.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 18))
            bg_rect = status_rect.inflate(28, 14)
            self.draw_panel(bg_rect)
            self.screen.blit(status, status_rect)

    def draw_debug(self):
        if not self.debug_enabled:
            return
        self.player.draw_collision_debug(self.screen, self.camera)
        if self.enemy and self.enemy.alive:
            self.enemy.draw_collision_debug(self.screen, self.camera)

    def draw(self):
        self.screen.fill((18, 22, 27))
        self.tilemap.draw(self.screen, self.camera)
        self.draw_character_layer()
        self.draw_debug()
        self.draw_hud()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)

            if not self.running:
                break

            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.mouse.set_visible(True)
        pygame.quit()


def main():
    try:
        EnemyTestRoom().run()
    except Exception as exc:
        pygame.quit()
        print(f"[Enemy Test Room] {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()
