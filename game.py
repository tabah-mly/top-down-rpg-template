import pygame
import sys
from opening import OpeningSequence
from camera import Camera
from font_manager import FontManager
from player import Player
from pointer import Pointer
from tiled_map import TiledMap
from dialog import DialogWindow
from main_menu import MainMenu
from dialogue_database import DialogueDatabase
from story_database import StoryDatabase
from event_manager import EventManager
from quest_manager import QuestManager
from quest_database import QuestDatabase
from dialogue_manager import DialogueManager
from story_state import StoryState


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

        # Shared systems
        self.font_manager = FontManager()
        self.font_manager.load(
            "main",
            "assets/fonts/PixelifySans-Regular.ttf",
        )

        self.dialogue_database = DialogueDatabase()
        self.dialogue_manager = DialogueManager(self.dialogue_database)

        self.active_dialogue_context = None
        self.story_database = StoryDatabase()
        self.event_manager = EventManager()
        self.story_state = StoryState(self.event_manager)

        self.quest_database = QuestDatabase()

        self.quest_manager = QuestManager(
            self.quest_database,
            self.event_manager,
        )

        self.pointer = Pointer()
        self.camera = Camera(self.screen_width, self.screen_height)

        # UI
        self.dialog = DialogWindow(
            self.screen_width,
            self.screen_height,
            self.font_manager,
        )

        interact_icon = pygame.image.load(
            "assets/imgs/system/interact.png"
        ).convert_alpha()

        self.interact_icon = pygame.transform.scale_by(interact_icon, 2)
        self.hud_font = self.font_manager.get("main", 20)
        self.hud_small_font = self.font_manager.get("main", 15)

        # Application state
        self.state = "menu"

        prologue = self.story_database.get_prologue("main_prologue")

        self.opening = OpeningSequence(
            self.screen_width,
            self.screen_height,
            self.font_manager,
            prologue,
        )

        self.main_menu = MainMenu(
            self.screen_width,
            self.screen_height,
            self.font_manager,
        )

        # Gameplay objects are initialized only when starting a game
        self.tilemap = None
        self.triggers = []
        self.collisions = []
        self.npcs = []
        self.enemies = []
        self.player = None
        self.mission_complete = False
        self.mission_phase = "idle"

        self.debug_collisions = False

    # ========================================================
    # GAME STATE
    # ========================================================

    def start_new_game(self):
        """Start the first playable prologue mission as Leonhard."""

        self.tilemap = TiledMap(
            "assets/maps/prologue_first_assault.tmx",
            scale=2,
        )

        self.triggers = self.tilemap.load_triggers()
        self.collisions = self.tilemap.load_collisions()
        self.npcs = self.tilemap.load_npcs()
        self.enemies = self.tilemap.load_enemies()

        self.camera.set_bounds(
            self.tilemap.width,
            self.tilemap.height,
        )

        spawn_position = self.tilemap.get_spawn("PlayerSpawn")

        self.player = Player(
            spawn_position.x,
            spawn_position.y,
            self.pointer,
            character="leonhard",
        )
        self.camera.follow(self.player.rect)

        self.pointer.ranged = False
        self.pointer.is_active = True

        self.player.set_bounds(self.tilemap.width, self.tilemap.height)
        self.player.set_collisions(self.collisions)
        self.player.set_npcs(self.npcs)
        self.player.set_enemies(self.enemies)

        for npc in self.npcs:
            npc.set_player(self.player)

        for enemy in self.enemies:
            enemy.set_player(self.player)
            enemy.set_collisions(self.collisions)

        self.dialog.active = False
        self.active_dialogue_context = None

        # These systems remain available for later story missions, but the
        # first combat slice does not start the unrelated forest quest.
        self.quest_manager.reset()
        self.story_state.reset()
        self.dialogue_manager.seen_dialogues.clear()

        self.mission_complete = False
        self.mission_phase = "briefing"
        self.debug_collisions = False
        self.state = "playing"

    def handle_menu_action(self, action):
        if action == "new_game":
            self.opening.reset()
            self.state = "opening"

        elif action == "continue":
            pass

        elif action == "exit":
            self.running = False

    # ========================================================
    # MAP MANAGEMENT
    # ========================================================

    def change_map(self, map_path, spawn_name):
        new_map = TiledMap(
            f"assets/maps/{map_path}",
            scale=2,
        )

        spawn = new_map.tmx.get_object_by_name(spawn_name)

        if spawn is None:
            raise ValueError(f"Spawn point '{spawn_name}' not found!")

        self.tilemap = new_map
        self.triggers = self.tilemap.load_triggers()
        self.collisions = new_map.load_collisions()
        self.npcs = self.tilemap.load_npcs()
        self.enemies = self.tilemap.load_enemies()

        self.camera.set_bounds(new_map.width, new_map.height)

        self.player.pos = pygame.Vector2(
            spawn.x * new_map.scale,
            spawn.y * new_map.scale,
        )
        self.player.rect.center = self.player.pos
        self.player.update_collision_boxes()
        self.camera.follow(self.player.rect)
        self.player.set_bounds(new_map.width, new_map.height)
        self.player.set_collisions(self.collisions)
        self.player.set_npcs(self.npcs)
        self.player.set_enemies(self.enemies)
        self.mission_complete = False
        self.mission_phase = "active"

        for npc in self.npcs:
            npc.set_player(self.player)

        for enemy in self.enemies:
            enemy.set_player(self.player)
            enemy.set_collisions(self.collisions)

    # ========================================================
    # INTERACTION
    # ========================================================

    def interact_with_npc(self):
        npc = self.get_nearby_npc()

        if not npc:
            return

        dialogue = self.dialogue_manager.get_dialogue(
            npc,
            self.quest_manager,
            self.story_state,
        )

        if not dialogue:
            return

        self.event_manager.emit(
            "npc_interacted",
            target=npc.entity_id,
        )

        self.active_dialogue_context = {
            "npc_id": npc.entity_id,
            "dialogue_id": dialogue["id"],
        }

        self.dialog.open(dialogue["content"])

    def get_nearby_npc(self):
        nearby_npcs = [npc for npc in self.npcs if npc.can_interact(self.player.rect)]

        if not nearby_npcs:
            return None

        player_pos = pygame.Vector2(self.player.rect.center)

        return min(
            nearby_npcs,
            key=lambda npc: player_pos.distance_to(npc.rect.center),
        )

    # ========================================================
    # EVENTS
    # ========================================================

    def event_listener(self):
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                self.running = False
                continue

            if self.state == "opening":
                finished = self.opening.handle_event(event)

                if finished:
                    self.start_new_game()

            elif self.state == "menu":
                action = self.main_menu.handle_event(event)

                if action:
                    self.handle_menu_action(action)

            elif self.state == "playing":
                self.handle_game_event(event)

            elif self.state == "game_over" and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.start_new_game()
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"

    def handle_game_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        # Mission briefing pauses gameplay until the player is ready.
        if self.mission_phase == "briefing":
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.mission_phase = "active"
            return

        # Keep the completed mission on screen until the player chooses what to do.
        if self.mission_phase == "complete":
            if event.key == pygame.K_r:
                self.start_new_game()
            elif event.key == pygame.K_ESCAPE:
                self.state = "menu"
            return

        if self.dialog.active:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                was_active = self.dialog.active
                self.dialog.advance()

                if was_active and not self.dialog.active:
                    self.on_dialogue_completed()

        elif event.key == pygame.K_e:
            self.interact_with_npc()

    def on_dialogue_completed(self):
        context = self.active_dialogue_context

        if not context:
            return

        self.event_manager.emit(
            "dialogue_completed",
            target=context["npc_id"],
            dialogue_id=context["dialogue_id"],
        )
        self.dialogue_manager.mark_as_seen(context["dialogue_id"])

        print(f"[DIALOGUE] Completed: " f"{context['dialogue_id']}")

        self.active_dialogue_context = None

    # ========================================================
    # GAMEPLAY
    # ========================================================

    def restart(self):
        self.start_new_game()

    def set_fps(self, frame=60):
        dt = self.clock.tick(frame) / 1000
        return min(dt, 0.05)

    def update(self, dt):
        if self.state == "opening":
            self.opening.update(dt)

            if self.opening.finished:
                self.start_new_game()

            return

        if self.state != "playing":
            return

        if self.dialog.active or self.mission_phase != "active":
            return

        self.player.update(dt, self.camera)
        self.camera.follow(self.player.rect)

        for enemy in self.enemies:
            enemy.update(dt)

        for npc in self.npcs:
            npc.update(dt)

        if self.player.stats["hp"] <= 0:
            self.state = "game_over"
            return

        if self.enemies and not any(enemy.alive for enemy in self.enemies):
            self.mission_complete = True
            self.mission_phase = "complete"

        for trigger in self.triggers:
            if trigger.update(self.player.body_collider.rect):

                if trigger.quest_event:
                    self.event_manager.emit(
                        trigger.quest_event,
                        target=trigger.quest_target,
                    )

                if trigger.action == "print":
                    print(f"[TRIGGER] {trigger.name}: " f"{trigger.message}")

                if trigger.action == "transition":
                    self.change_map(
                        trigger.target_map,
                        trigger.target_spawn,
                    )
                    break

                elif trigger.action == "dialog":
                    self.dialog.open(trigger.message)
                    break

    # ========================================================
    # DRAWING
    # ========================================================

    def draw(self):
        if self.state == "opening":
            self.opening.draw(self.screen)

        elif self.state == "menu":
            self.main_menu.draw(self.screen)

        elif self.state == "playing":
            self.draw_gameplay()

        elif self.state == "game_over":
            self.draw_game_over()

    def draw_gameplay(self):
        self.screen.fill((0, 0, 0))
        self.tilemap.draw(self.screen, self.camera)

        for enemy in self.enemies:
            enemy.draw(self.screen, self.camera)

        nearby_npc = None
        if not self.dialog.active:
            nearby_npc = self.get_nearby_npc()

        for npc in self.npcs:
            npc.draw(
                self.screen,
                self.camera,
                interact_icon=(self.interact_icon if npc == nearby_npc else None),
            )

        self.player.draw(self.screen, self.camera)

        player_screen_pos = self.camera.apply(self.player.rect).center
        self.pointer.draw(self.screen, player_screen_pos)

        for trigger in self.triggers:
            trigger.draw_debug(self.screen, self.camera)

        self.dialog.draw(self.screen)
        self.draw_hud()

        if self.mission_phase in ("briefing", "complete"):
            self.draw_mission_overlay()

        if self.debug_collisions:
            for collision in self.collisions:
                collision.draw_debug(self.screen, self.camera)

            self.player.draw_collision_debug(self.screen, self.camera)

            for npc in self.npcs:
                npc.draw_collision_debug(self.screen, self.camera)

            for enemy in self.enemies:
                enemy.draw_collision_debug(self.screen, self.camera)

    def draw_hud(self):
        panel = pygame.Surface((330, 92), pygame.SRCALPHA)
        panel.fill((12, 14, 20, 210))
        self.screen.blit(panel, (20, 18))

        title = self.hud_font.render("LEONHARD VON EVERMONT", True, (238, 226, 190))
        self.screen.blit(title, (32, 26))

        hp = self.player.stats["hp"]
        max_hp = self.player.stats["max_hp"]
        pygame.draw.rect(self.screen, (65, 35, 38), (32, 58, 220, 13))
        hp_width = int(220 * hp / max_hp) if max_hp else 0
        pygame.draw.rect(self.screen, (177, 61, 65), (32, 58, hp_width, 13))
        hp_text = self.hud_small_font.render(f"NYAWA {hp}/{max_hp}", True, (245, 240, 230))
        self.screen.blit(hp_text, (260, 55))

        remaining = sum(1 for enemy in self.enemies if enemy.alive)
        objective = f"SASARAN: Usir para penyerbu ({remaining} tersisa)"
        objective_surface = self.hud_small_font.render(objective, True, (238, 232, 215))
        self.screen.blit(objective_surface, (24, self.screen_height - 34))

        controls = self.hud_small_font.render(
            "WASD: GERAK   KLIK KIRI: SERANG",
            True,
            (205, 205, 195),
        )
        self.screen.blit(
            controls,
            controls.get_rect(bottomright=(self.screen_width - 22, self.screen_height - 18)),
        )

    def draw_mission_overlay(self):
        overlay = pygame.Surface(
            (self.screen_width, self.screen_height),
            pygame.SRCALPHA,
        )
        overlay.fill((5, 7, 12, 175))
        self.screen.blit(overlay, (0, 0))

        panel_width = min(660, self.screen_width - 48)
        panel_height = 250
        panel = pygame.Rect(0, 0, panel_width, panel_height)
        panel.center = (self.screen_width // 2, self.screen_height // 2)

        pygame.draw.rect(
            self.screen,
            (18, 22, 30),
            panel,
            border_radius=12,
        )
        pygame.draw.rect(
            self.screen,
            (190, 158, 91),
            panel,
            width=2,
            border_radius=12,
        )

        if self.mission_phase == "briefing":
            eyebrow = "PROLOG  /  MISI 01"
            title = "PENYERBUAN PERTAMA"
            description = "Usir empat penyerbu dari persimpangan kota luar."
            prompt = "TEKAN ENTER ATAU SPASI UNTUK MEMULAI"
        else:
            eyebrow = "PROLOG  /  MISI 01 SELESAI"
            title = "KOTA LUAR AMAN"
            description = "Para penyerbu berhasil dipukul mundur. Persimpangan kini aman."
            prompt = "R: ULANGI MISI     ESC: KEMBALI KE MENU"

        eyebrow_font = self.font_manager.get("main", 17)
        title_font = self.font_manager.get("main", 43)
        description_font = self.font_manager.get("main", 19)
        prompt_font = self.font_manager.get("main", 16)

        eyebrow_surface = eyebrow_font.render(eyebrow, True, (202, 178, 126))
        title_surface = title_font.render(title, True, (244, 232, 204))
        description_surface = description_font.render(
            description,
            True,
            (220, 220, 214),
        )
        prompt_surface = prompt_font.render(prompt, True, (232, 196, 120))

        self.screen.blit(
            eyebrow_surface,
            eyebrow_surface.get_rect(center=(panel.centerx, panel.top + 42)),
        )
        self.screen.blit(
            title_surface,
            title_surface.get_rect(center=(panel.centerx, panel.top + 96)),
        )
        self.screen.blit(
            description_surface,
            description_surface.get_rect(center=(panel.centerx, panel.top + 158)),
        )
        self.screen.blit(
            prompt_surface,
            prompt_surface.get_rect(center=(panel.centerx, panel.bottom - 38)),
        )

    def draw_game_over(self):
        self.screen.fill((14, 12, 18))
        title = self.font_manager.get("main", 54).render(
            "LEONHARD TELAH GUGUR", True, (220, 190, 170)
        )
        prompt = self.hud_font.render(
            "Tekan R untuk mencoba lagi  |  ESC untuk kembali ke menu",
            True,
            (225, 220, 205),
        )
        self.screen.blit(title, title.get_rect(center=(self.screen_width // 2, self.screen_height // 2 - 35)))
        self.screen.blit(prompt, prompt.get_rect(center=(self.screen_width // 2, self.screen_height // 2 + 35)))

    # ========================================================
    # MAIN LOOP
    # ========================================================

    def start(self):
        while self.running:
            dt = self.set_fps(60)

            self.event_listener()
            self.update(dt)
            self.draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()
