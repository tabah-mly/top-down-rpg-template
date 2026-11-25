import pygame
import sys
import json
import random
import math
from pathlib import Path
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
from enemy import Enemy
from debug import DEBUG, BODY_COLLISION_COLOR, HURTBOX_COLOR, PLAYER_MELEE_HITBOX_COLOR, ENEMY_ATTACK_RANGE_COLOR, PROJECTILE_HITBOX_COLOR, MAP_RECT_COLOR, MAP_ELLIPSE_COLOR, MAP_POLYGON_COLOR


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
        self.scenes_by_number = {
            scene.get("number"): scene
            for scene in prologue.get("scenes", [])
            if scene.get("number") is not None
        }
        opening_data = {
            "title": prologue.get("title", "Runtuhnya Kerajaan Lumerian"),
            "pages": self.scenes_by_number.get(1, {}).get(
                "narration", prologue.get("pages", [])
            ),
        }
        self.opening = OpeningSequence(
            self.screen_width,
            self.screen_height,
            self.font_manager,
            opening_data,
        )
        self.active_narrative = None
        self.pending_narrative_action = None

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
        self.current_mission_id = None
        self.current_map_path = None
        self.ritual_rect = None

        # Wave-driven mission state. Mission rules live in data/missions/*.json.
        self.mission_config = None
        self.current_wave_index = -1
        self.wave_time_remaining = 0.0
        self.wave_spawn_timer = 0.0
        self.mission_failure_reason = None

        self.debug = DEBUG

    # ========================================================
    # GAME STATE
    # ========================================================

    def start_new_game(self):
        """Start the first playable prologue mission as Leonhard."""

        self.current_map_path = "prologue_first_assault.tmx"
        self.current_mission_id = "first_assault"
        self.ritual_rect = None

        self.tilemap = TiledMap(
            f"assets/maps/{self.current_map_path}",
            scale=2,
        )

        self.triggers = self.tilemap.load_triggers()
        self.collisions = self.tilemap.load_collisions()
        self.npcs = self.tilemap.load_npcs()
        # Mission enemies are spawned from the mission JSON, not fixed Tiled
        # EnemySpawn objects. Tiled still defines player, collision and map data.
        self.enemies = []

        self.camera.set_bounds(self.tilemap.width, self.tilemap.height)
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
        self.player.reset_transient_combat_state()
        self.load_mission_config("first_assault")
        self.reset_wave_state()

        for npc in self.npcs:
            npc.set_player(self.player)

        for enemy in self.enemies:
            enemy.set_player(self.player)
            enemy.set_collisions(self.collisions)

        self.dialog.active = False
        self.active_dialogue_context = None
        self.quest_manager.reset()
        self.story_state.reset()
        self.dialogue_manager.seen_dialogues.clear()

        self.mission_complete = False
        self.mission_phase = "briefing"
        self.mission_failure_reason = None
        self.debug = DEBUG
        self.state = "playing"

    def begin_narrative(self, scene_number, next_action, pages=None):
        """Play one scene's narration, then continue to its next story step."""
        if self.player is not None:
            self.player.reset_transient_combat_state()

        scene = self.scenes_by_number.get(scene_number)
        if scene is None:
            raise ValueError(f"Adegan prolog nomor {scene_number} tidak ditemukan.")

        narration_pages = pages if pages is not None else scene.get("narration", [])
        if not narration_pages:
            raise ValueError(f"Adegan '{scene.get('title', scene_number)}' tidak memiliki narasi.")

        self.active_narrative = OpeningSequence(
            self.screen_width,
            self.screen_height,
            self.font_manager,
            {
                "title": scene.get("title", ""),
                "pages": narration_pages,
            },
        )
        self.pending_narrative_action = next_action
        self.state = "cinematic"

    def complete_narrative(self):
        """Continue the prologue after a narration sequence has faded out."""
        action = self.pending_narrative_action
        self.active_narrative = None
        self.pending_narrative_action = None

        if action == "first_mission":
            self.start_new_game()
        elif action == "scene4":
            self.begin_narrative(4, "scene5")
        elif action == "scene5":
            self.begin_narrative(5, "battlefield")
        elif action == "battlefield":
            self.start_war_mission()
        elif action == "scene7_prelude":
            scene = self.scenes_by_number[7]
            self.begin_narrative(7, "village", scene["narration"][:3])
        elif action == "village":
            self.start_village_sequence()
        elif action == "scene7_ending":
            self.finish_prologue()
        else:
            raise ValueError(f"Aksi lanjutan narasi tidak dikenal: {action}")

    def start_war_mission(self):
        """Load Scene 5 and prepare its five configurable survival/elimination waves."""
        self.change_map("prologue_war_battlefield.tmx", "PlayerSpawn", load_enemies=False)
        self.current_mission_id = "war_battlefield"
        self.load_mission_config("war_of_fallen_skies")
        self.reset_wave_state()
        self.enemies = []
        self.player.set_enemies(self.enemies)
        self.mission_phase = "briefing"
        self.mission_complete = False
        self.mission_failure_reason = None
        # Treat each major playable sequence as a fresh mission attempt.
        self.player.stats["hp"] = self.player.stats["max_hp"]

    def start_village_sequence(self):
        """Load Scene 7 and register the Tiled ritual marker for interaction."""
        self.change_map("prologue_abandoned_village.tmx", "PlayerSpawn")
        self.current_mission_id = "abandoned_village"
        self.mission_config = None
        self.reset_wave_state()
        self.mission_phase = "active"
        self.mission_complete = False

        marker = self.tilemap.tmx.get_object_by_name("RitualPoint")
        if marker is None:
            raise ValueError("Objek 'RitualPoint' tidak ditemukan di peta desa.")

        scale = self.tilemap.scale
        self.ritual_rect = pygame.Rect(
            round(marker.x * scale),
            round(marker.y * scale),
            round(marker.width * scale),
            round(marker.height * scale),
        ).inflate(64, 64)

    def is_near_ritual(self):
        return (
            self.ritual_rect is not None
            and self.player is not None
            and self.ritual_rect.colliderect(self.player.body_collider.rect)
        )

    def continue_after_mission(self):
        if self.current_mission_id == "first_assault":
            self.begin_narrative(3, "scene4")
        elif self.current_mission_id == "war_battlefield":
            self.begin_narrative(6, "scene7_prelude")

    def restart_current_mission(self):
        if self.current_mission_id == "first_assault":
            self.start_new_game()
            return

        if self.current_mission_id == "war_battlefield":
            self.start_war_mission()
            return

        if self.current_mission_id == "abandoned_village":
            self.start_village_sequence()
            self.player.stats["hp"] = self.player.stats["max_hp"]
            return

        if not self.current_map_path:
            self.start_new_game()

    def finish_prologue(self):
        self.ritual_rect = None
        self.mission_config = None
        self.state = "ending"

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

    def change_map(self, map_path, spawn_name, load_enemies=True):
        self.current_map_path = map_path
        new_map = TiledMap(
            f"assets/maps/{map_path}",
            scale=2,
        )

        spawn = new_map.tmx.get_object_by_name(spawn_name)
        if spawn is None:
            raise ValueError(f"Spawn point '{spawn_name}' tidak ditemukan!")

        self.tilemap = new_map
        self.triggers = self.tilemap.load_triggers()
        self.collisions = new_map.load_collisions()
        self.npcs = self.tilemap.load_npcs()
        self.enemies = self.tilemap.load_enemies() if load_enemies else []

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
        self.player.reset_transient_combat_state()
        self.mission_complete = False
        self.mission_phase = "active"

        for npc in self.npcs:
            npc.set_player(self.player)

        for enemy in self.enemies:
            enemy.set_player(self.player)
            enemy.set_collisions(self.collisions)

        # A successful map change enters gameplay. This is important when
        # leaving a cinematic, restarting a mission, or following a map trigger.
        self.state = "playing"

    # ========================================================
    # MISSION CONFIGURATION AND WAVE SPAWNING
    # ========================================================

    def load_mission_config(self, mission_id):
        """Load fixed-value mission settings from data/missions/<id>.json."""
        path = Path(__file__).resolve().parent / "data" / "missions" / f"{mission_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Konfigurasi misi tidak ditemukan: {path}")

        with path.open("r", encoding="utf-8") as file:
            config = json.load(file)

        waves = config.get("waves")
        if not isinstance(waves, list) or not waves:
            raise ValueError(f"Misi '{mission_id}' harus memiliki daftar waves.")

        self.mission_config = config

    def reset_wave_state(self):
        self.current_wave_index = -1
        self.wave_time_remaining = 0.0
        self.wave_spawn_timer = 0.0
        self.mission_failure_reason = None

    def get_current_wave(self):
        if self.mission_config is None or self.current_wave_index < 0:
            return None
        waves = self.mission_config.get("waves", [])
        if self.current_wave_index >= len(waves):
            return None
        return waves[self.current_wave_index]

    def start_mission_waves(self):
        """Begin the first wave after the player confirms the mission briefing."""
        if self.mission_config is None:
            self.mission_phase = "active"
            return

        self.current_wave_index = 0
        self.mission_failure_reason = None
        self.mission_phase = "active"
        self.start_current_wave()

    def start_current_wave(self):
        """Start a wave using enemy IDs from the entity database.

        Entity visuals, sizes, combat defaults, collision boxes, and hurtboxes
        live in data/entities/enemies.json. Mission files only select IDs and
        define encounter-level values such as counts, weights, and timing.
        """
        wave = self.get_current_wave()
        if wave is None:
            self.complete_wave_mission()
            return

        # Remove dead objects, but never recreate or heal surviving enemies.
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        self.player.set_enemies(self.enemies)
        self.wave_time_remaining = float(wave.get("duration", 0))
        self.wave_spawn_timer = float(wave.get("spawn_interval", 0.75))

        if self.mission_config.get("mode") == "elimination":
            boss_ref = wave.get("boss", {})
            minion_ref = wave.get("minions", {})
            boss_id = boss_ref.get("id")
            minion_id = minion_ref.get("id")

            if not boss_id or not minion_id:
                raise ValueError(
                    f"Wave {wave.get('wave')} must define boss.id and minions.id."
                )

            # One boss profile per wave. A boss may share its sprite with a
            # minion while keeping independent scale/collider/hurtbox settings.
            self.spawn_mission_enemy(
                boss_id,
                name=f"Boss_Wave_{wave.get('wave', self.current_wave_index + 1)}",
                is_boss=True,
            )

            count = int(minion_ref.get("count", 0))
            for number in range(count):
                self.spawn_mission_enemy(
                    minion_id,
                    name=f"{minion_id.title()}_W{self.current_wave_index + 1}_{number + 1:02d}",
                    is_boss=False,
                )
            return

        wave_mode = wave.get("mode", "survival")
        if wave_mode == "survival":
            # Add the full wave's reinforcement quota even when survivors
            # remain from the previous wave. After this initial addition,
            # replenishment only targets active_target total living enemies.
            initial_count = int(wave.get("active_target", 0))
            for number in range(initial_count):
                self.spawn_random_wave_enemy(wave, suffix=f"Opening_{number + 1:03d}")

        # Final elimination wave intentionally spawns nothing.

    def build_enemy_config(self, enemy_id, is_boss=False):
        """Resolve an enemy ID into its single source-of-truth entity profile."""
        config = self.tilemap.entity_database.get("enemy", enemy_id)

        # Aggression is intentionally mission-specific: First Assault uses
        # proximity aggro, while War of Fallen Skies uses always-on pursuit.
        mission_behavior = self.mission_config.get("enemy_behavior", {})
        config["aggro_mode"] = mission_behavior.get(
            "aggro_mode", config.get("aggro_mode", "proximity")
        )
        config["is_boss"] = bool(is_boss)
        return config

    def find_enemy_spawn_position(self, config):
        """Choose a safe spawn point, optionally spreading enemies across map zones."""
        spawn_settings = self.mission_config.get("spawn", {})
        min_distance = float(spawn_settings.get("min_distance_from_player", 240))
        max_distance = float(spawn_settings.get("max_distance_from_player", 760))
        attempts = max(1, int(spawn_settings.get("attempts", 220)))
        min_gap = int(spawn_settings.get("min_gap", 18))
        distribution = str(spawn_settings.get("distribution", "ring")).lower()
        map_width = self.tilemap.width
        map_height = self.tilemap.height

        body = config.get("body_collider", {})
        body_width = int(body.get("width", 24))
        body_height = int(body.get("height", 16))
        offset = body.get("offset", (0, 25))
        offset_x, offset_y = float(offset[0]), float(offset[1])
        padding = max(body_width, body_height) + 12
        player_center = pygame.Vector2(self.player.pos)

        def valid_position(x, y):
            if not (padding <= x <= map_width - padding and padding <= y <= map_height - padding):
                return None

            if pygame.Vector2(x, y).distance_to(player_center) < min_distance:
                return None

            body_rect = pygame.Rect(0, 0, body_width, body_height)
            body_rect.center = (round(x + offset_x), round(y + offset_y))

            if any(collision.collides(body_rect) for collision in self.collisions):
                return None

            if body_rect.colliderect(self.player.body_collider.rect.inflate(100, 100)):
                return None

            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                if body_rect.colliderect(enemy.body_collider.rect.inflate(min_gap, min_gap)):
                    return None

            return pygame.Vector2(round(x), round(y))

        if distribution == "spread":
            # Divide the map into zones and prefer the least-populated zone.
            # During an opening wave this distributes spawns over the entire
            # battlefield; later reinforcements tend to enter from less crowded
            # parts of the map instead of clustering around Leonhard.
            columns = max(1, int(spawn_settings.get("grid_columns", 4)))
            rows = max(1, int(spawn_settings.get("grid_rows", 4)))
            cell_counts = [0] * (columns * rows)

            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                col = min(columns - 1, max(0, int(enemy.pos.x / map_width * columns)))
                row = min(rows - 1, max(0, int(enemy.pos.y / map_height * rows)))
                cell_counts[row * columns + col] += 1

            cell_order = list(range(columns * rows))
            random.shuffle(cell_order)
            cell_order.sort(key=lambda index: cell_counts[index])
            attempts_per_cell = max(12, math.ceil(attempts / len(cell_order)))

            for cell_index in cell_order:
                col = cell_index % columns
                row = cell_index // columns
                cell_left = col * map_width / columns
                cell_right = (col + 1) * map_width / columns
                cell_top = row * map_height / rows
                cell_bottom = (row + 1) * map_height / rows

                left = max(padding, cell_left + padding)
                right = min(map_width - padding, cell_right - padding)
                top = max(padding, cell_top + padding)
                bottom = min(map_height - padding, cell_bottom - padding)
                if right <= left or bottom <= top:
                    continue

                for _ in range(attempts_per_cell):
                    x = random.uniform(left, right)
                    y = random.uniform(top, bottom)
                    position = valid_position(x, y)
                    if position is not None:
                        return position

            # A few maps have heavily obstructed zones. Fall back to uniform
            # map-wide sampling while keeping every safety/spacing constraint.
            for _ in range(attempts):
                x = random.uniform(padding, max(padding + 1, map_width - padding))
                y = random.uniform(padding, max(padding + 1, map_height - padding))
                position = valid_position(x, y)
                if position is not None:
                    return position

        else:
            # Legacy ring distribution remains available for future missions.
            for attempt in range(attempts):
                if attempt < attempts * 0.8:
                    angle = random.random() * math.tau
                    distance = random.uniform(min_distance, max_distance)
                    x = player_center.x + math.cos(angle) * distance
                    y = player_center.y + math.sin(angle) * distance
                else:
                    x = random.uniform(padding, max(padding + 1, map_width - padding))
                    y = random.uniform(padding, max(padding + 1, map_height - padding))

                position = valid_position(x, y)
                if position is not None:
                    return position

        raise RuntimeError(
            "Tidak menemukan posisi spawn yang aman. Periksa area terbuka pada peta "
            "atau naikkan nilai spawn.attempts/min_distance_from_player."
        )

    def spawn_mission_enemy(self, enemy_id, name, is_boss=False):
        config = self.build_enemy_config(enemy_id, is_boss=is_boss)
        position = self.find_enemy_spawn_position(config)
        enemy = Enemy(
            x=position.x,
            y=position.y,
            name=name,
            config=config,
        )
        enemy.set_player(self.player)
        enemy.set_collisions(self.collisions)
        enemy.is_boss = is_boss
        enemy.enemy_type = enemy_id
        self.enemies.append(enemy)
        self.player.set_enemies(self.enemies)
        return enemy

    def choose_wave_enemy(self, wave):
        pool = wave.get("enemies", [])
        if not pool:
            raise ValueError(f"Wave {wave.get('wave')} tidak memiliki enemy pool.")
        weights = [max(0, float(entry.get("weight", 1))) for entry in pool]
        if not any(weights):
            raise ValueError(f"Wave {wave.get('wave')} memiliki semua weight nol.")
        return random.choices(pool, weights=weights, k=1)[0]

    def spawn_random_wave_enemy(self, wave, suffix="Reinforcement"):
        entry = self.choose_wave_enemy(wave)
        # `id` is the canonical mission field. `type` remains accepted for
        # backward compatibility with older mission JSON files.
        enemy_id = entry.get("id", entry.get("type"))
        if not enemy_id:
            raise ValueError(
                f"Wave {wave.get('wave')} enemy entry is missing its 'id'."
            )
        name = f"{enemy_id.title()}_W{self.current_wave_index + 1}_{suffix}"
        return self.spawn_mission_enemy(enemy_id, name, is_boss=False)

    def complete_wave_mission(self):
        self.mission_complete = True
        self.mission_phase = "complete"
        self.wave_time_remaining = 0.0

    def fail_mission(self, reason):
        self.mission_failure_reason = reason
        self.state = "game_over"

    def update_wave_mission(self, dt):
        """Update elimination waves or timed survival waves for the active mission."""
        if self.mission_config is None or self.mission_phase != "active":
            return

        wave = self.get_current_wave()
        if wave is None:
            self.complete_wave_mission()
            return

        living = sum(1 for enemy in self.enemies if enemy.alive)
        mission_mode = self.mission_config.get("mode")

        if mission_mode == "elimination":
            if living == 0:
                if self.current_wave_index + 1 < len(self.mission_config["waves"]):
                    self.current_wave_index += 1
                    self.start_current_wave()
                else:
                    self.complete_wave_mission()
            return

        wave_mode = wave.get("mode", "survival")
        if wave_mode == "survival":
            self.wave_time_remaining = max(0.0, self.wave_time_remaining - dt)
            if self.wave_time_remaining <= 0:
                if self.current_wave_index + 1 < len(self.mission_config["waves"]):
                    self.current_wave_index += 1
                    self.start_current_wave()
                else:
                    self.complete_wave_mission()
                return

            target = int(wave.get("active_target", 0))
            interval = max(0.05, float(wave.get("spawn_interval", 0.75)))

            if living < target:
                self.wave_spawn_timer -= dt
                if self.wave_spawn_timer <= 0:
                    self.spawn_random_wave_enemy(wave, suffix="Reinforcement")
                    self.wave_spawn_timer = interval
            else:
                self.wave_spawn_timer = interval
            return

        if wave_mode == "elimination":
            # The final phase has no spawning; every survivor from earlier waves
            # remains in the world and must be defeated before the countdown ends.
            if living == 0:
                self.complete_wave_mission()
                return

            self.wave_time_remaining = max(0.0, self.wave_time_remaining - dt)
            if self.wave_time_remaining <= 0 and living > 0:
                self.fail_mission("final_wave_timeout")

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
                self.opening.handle_event(event)

            elif self.state == "cinematic":
                if self.active_narrative:
                    self.active_narrative.handle_event(event)

            elif self.state == "menu":
                action = self.main_menu.handle_event(event)
                if action:
                    self.handle_menu_action(action)

            elif self.state == "playing":
                self.handle_game_event(event)

            elif self.state == "game_over" and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.restart_current_mission()
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"

            elif self.state == "ending" and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                    self.state = "menu"

    def handle_game_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.mission_phase == "briefing":
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                if self.mission_config is not None:
                    self.start_mission_waves()
                else:
                    self.mission_phase = "active"
            return

        if self.mission_phase == "complete":
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.continue_after_mission()
            elif event.key == pygame.K_r:
                self.restart_current_mission()
            elif event.key == pygame.K_ESCAPE:
                self.state = "menu"
            return

        if self.dialog.active:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                was_active = self.dialog.active
                self.dialog.advance()
                if was_active and not self.dialog.active:
                    self.on_dialogue_completed()
            return

        if event.key == pygame.K_e:
            if self.current_mission_id == "abandoned_village":
                if self.is_near_ritual():
                    scene = self.scenes_by_number[7]
                    self.begin_narrative(7, "scene7_ending", scene["narration"][3:])
                return

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
                self.begin_narrative(2, "first_mission")
            return

        if self.state == "cinematic":
            if self.active_narrative:
                self.active_narrative.update(dt)
                if self.active_narrative.finished:
                    self.complete_narrative()
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
            self.fail_mission("player_defeated")
            return

        if self.mission_config is not None and self.mission_phase == "active":
            self.update_wave_mission(dt)
            if self.state != "playing" or self.mission_phase != "active":
                return
        elif self.enemies and not any(enemy.alive for enemy in self.enemies):
            self.mission_complete = True
            self.mission_phase = "complete"
            return

        for trigger in self.triggers:
            if trigger.update(self.player.body_collider.rect):
                if trigger.quest_event:
                    self.event_manager.emit(
                        trigger.quest_event,
                        target=trigger.quest_target,
                    )

                if trigger.action == "print":
                    print(f"[TRIGGER] {trigger.name}: {trigger.message}")
                elif trigger.action == "transition":
                    self.change_map(trigger.target_map, trigger.target_spawn)
                    break
                elif trigger.action == "dialog":
                    self.dialog.open(trigger.message)
                    break

    def sync_cursor_visibility(self):
        """Show the system cursor outside active gameplay, including mission overlays."""
        mission_overlay_visible = self.mission_phase in ("briefing", "complete")
        should_be_visible = self.state != "playing" or mission_overlay_visible
        if pygame.mouse.get_visible() != should_be_visible:
            pygame.mouse.set_visible(should_be_visible)

    def draw(self):
        # Cursor visibility follows the current game state, not the lifetime
        # of the custom in-game pointer. This also restores the system cursor
        # when returning to cinematics, menus, the game-over screen, or ending.
        self.sync_cursor_visibility()

        if self.state == "opening":
            self.opening.draw(self.screen)
        elif self.state == "cinematic":
            if self.active_narrative:
                self.active_narrative.draw(self.screen)
            else:
                self.screen.fill((0, 0, 0))
        elif self.state == "menu":
            self.main_menu.draw(self.screen)
        elif self.state == "playing":
            self.draw_gameplay()
        elif self.state == "game_over":
            self.draw_game_over()
        elif self.state == "ending":
            self.draw_ending_screen()

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
        if self.mission_phase == "active":
            player_screen_pos = self.camera.apply(self.player.rect).center
            self.pointer.draw(self.screen, player_screen_pos)

        if self.debug:
            for trigger in self.triggers:
                trigger.draw_debug(self.screen, self.camera)

        self.dialog.draw(self.screen)
        self.draw_hud()

        if self.mission_phase in ("briefing", "complete"):
            self.draw_mission_overlay()

        if self.current_mission_id == "abandoned_village" and self.is_near_ritual():
            prompt = self.hud_font.render(
                "TEKAN E UNTUK MEMULAI RITUAL PENYEGELAN",
                True,
                (246, 220, 165),
            )
            prompt_rect = prompt.get_rect(center=(self.screen_width // 2, self.screen_height - 72))
            panel = prompt_rect.inflate(28, 18)
            pygame.draw.rect(self.screen, (12, 14, 20), panel, border_radius=6)
            self.screen.blit(prompt, prompt_rect)

        if self.debug:
            for collision in self.collisions:
                collision.draw_debug(self.screen, self.camera)

            self.player.draw_collision_debug(self.screen, self.camera)
            for npc in self.npcs:
                npc.draw_collision_debug(self.screen, self.camera)
            for enemy in self.enemies:
                enemy.draw_collision_debug(self.screen, self.camera)

            self.draw_debug_legend()

    def draw_debug_legend(self):
        """Display the meaning of debug outlines in the top-right corner."""
        rows = [
            ("Body collision", BODY_COLLISION_COLOR),
            ("Hurtbox", HURTBOX_COLOR),
            ("Player melee hitbox", PLAYER_MELEE_HITBOX_COLOR),
            ("Enemy melee range (while attacking)", ENEMY_ATTACK_RANGE_COLOR),
            ("Projectile hitbox", PROJECTILE_HITBOX_COLOR),
        ]

        panel_width = 236
        row_height = 19
        panel_height = 12 + row_height * (len(rows) + 1)
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((8, 12, 18, 205))
        pygame.draw.rect(panel, (180, 190, 205), panel.get_rect(), 1, border_radius=5)

        title = self.hud_small_font.render("DEBUG COLLISION", True, (245, 235, 205))
        panel.blit(title, (9, 6))

        for index, (label, color) in enumerate(rows):
            y = 27 + index * row_height
            pygame.draw.rect(panel, color, (10, y + 3, 13, 13), 2)
            text = self.hud_small_font.render(label, True, (225, 230, 238))
            panel.blit(text, (31, y))

        # Map collision objects use different colors according to their shape.
        y = 27 + len(rows) * row_height
        pygame.draw.rect(panel, MAP_RECT_COLOR, (10, y + 3, 8, 13), 2)
        pygame.draw.ellipse(panel, MAP_ELLIPSE_COLOR, (21, y + 3, 8, 13), 2)
        pygame.draw.polygon(panel, MAP_POLYGON_COLOR, [(36, y + 3), (43, y + 16), (29, y + 16)], 2)
        text = self.hud_small_font.render("Map collision shapes", True, (225, 230, 238))
        panel.blit(text, (49, y))

        self.screen.blit(panel, (self.screen_width - panel_width - 18, 18))

    def draw_hud(self):
        panel = pygame.Surface((430, 118), pygame.SRCALPHA)
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
        if self.current_mission_id == "first_assault":
            objective = f"SASARAN: Usir penyerbu dari persimpangan ({remaining} tersisa)"
        elif self.current_mission_id == "war_battlefield":
            objective = f"SASARAN: Hadapi pasukan iblis ({remaining} tersisa)"
        else:
            objective = "SASARAN: Temukan tempat ritual penyegelan"

        if self.mission_config is not None and self.current_wave_index >= 0:
            total_waves = len(self.mission_config.get("waves", []))
            wave = self.get_current_wave() or {}
            wave_label = f"GELOMBANG {self.current_wave_index + 1}/{total_waves}"
            if self.mission_config.get("mode") == "survival_then_elimination":
                seconds = max(0, int(math.ceil(self.wave_time_remaining)))
                timer = f"{seconds // 60:02d}:{seconds % 60:02d}"
                phase_label = "ELIMINASI" if wave.get("mode") == "elimination" else "BERTAHAN"
                wave_label = f"{wave_label}  |  {phase_label}  |  {timer}"
            objective = f"{wave_label}  |  MUSUH TERSISA: {remaining}"
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

        panel_width = min(700, self.screen_width - 48)
        panel_height = 250
        panel = pygame.Rect(0, 0, panel_width, panel_height)
        panel.center = (self.screen_width // 2, self.screen_height // 2)

        pygame.draw.rect(self.screen, (18, 22, 30), panel, border_radius=12)
        pygame.draw.rect(self.screen, (190, 158, 91), panel, width=2, border_radius=12)

        if self.current_mission_id == "war_battlefield":
            if self.mission_phase == "briefing":
                eyebrow = "PROLOG  /  MISI 02"
                title = "PERANG LANGIT YANG RUNTUH"
                description = "Hadapi lima gelombang: bertahan dari empat serangan, lalu habisi semua musuh tersisa dalam 10 detik."
                prompt = "TEKAN ENTER ATAU SPASI UNTUK MEMULAI"
            else:
                eyebrow = "PROLOG  /  MISI 02 SELESAI"
                title = "JALUR MUNDUR TERBUKA"
                description = "Pasukan yang tersisa mulai mundur. Leonhard harus menyusul."
                prompt = "SPASI: LANJUTKAN   R: ULANGI MISI   ESC: MENU"
        else:
            if self.mission_phase == "briefing":
                eyebrow = "PROLOG  /  MISI 01"
                title = "PENYERBUAN PERTAMA"
                description = "Kalahkan empat komandan iblis beserta pasukan mereka dalam empat gelombang."
                prompt = "TEKAN ENTER ATAU SPASI UNTUK MEMULAI"
            else:
                eyebrow = "PROLOG  /  MISI 01 SELESAI"
                title = "KOTA LUAR AMAN"
                description = "Keempat komandan dan seluruh pasukannya berhasil dikalahkan. Kota luar aman."
                prompt = "SPASI: LANJUTKAN   R: ULANGI MISI   ESC: MENU"

        eyebrow_font = self.font_manager.get("main", 17)
        title_font = self.font_manager.get("main", 39)
        description_font = self.font_manager.get("main", 19)
        prompt_font = self.font_manager.get("main", 15)

        eyebrow_surface = eyebrow_font.render(eyebrow, True, (202, 178, 126))
        title_surface = title_font.render(title, True, (244, 232, 204))
        description_surface = description_font.render(description, True, (220, 220, 214))
        prompt_surface = prompt_font.render(prompt, True, (232, 196, 120))

        self.screen.blit(eyebrow_surface, eyebrow_surface.get_rect(center=(panel.centerx, panel.top + 42)))
        self.screen.blit(title_surface, title_surface.get_rect(center=(panel.centerx, panel.top + 96)))
        self.screen.blit(description_surface, description_surface.get_rect(center=(panel.centerx, panel.top + 158)))
        self.screen.blit(prompt_surface, prompt_surface.get_rect(center=(panel.centerx, panel.bottom - 38)))

    def draw_game_over(self):
        self.screen.fill((14, 12, 18))
        if self.mission_failure_reason == "final_wave_timeout":
            title_text = "WAKTU HABIS"
            detail_text = "Musuh masih tersisa ketika waktu 10 detik berakhir."
        else:
            title_text = "LEONHARD TELAH GUGUR"
            detail_text = "Leonhard tidak mampu bertahan di medan perang."

        title = self.font_manager.get("main", 54).render(
            title_text, True, (220, 190, 170)
        )
        prompt = self.hud_font.render(
            "Tekan R untuk mengulang misi  |  ESC untuk kembali ke menu",
            True,
            (225, 220, 205),
        )
        detail = self.hud_small_font.render(detail_text, True, (225, 220, 205))
        self.screen.blit(title, title.get_rect(center=(self.screen_width // 2, self.screen_height // 2 - 55)))
        self.screen.blit(detail, detail.get_rect(center=(self.screen_width // 2, self.screen_height // 2)))
        self.screen.blit(prompt, prompt.get_rect(center=(self.screen_width // 2, self.screen_height // 2 + 42)))

    def draw_ending_screen(self):
        self.screen.fill((8, 9, 14))
        title = self.font_manager.get("main", 52).render(
            "PENGORBANAN TERAKHIR", True, (238, 220, 185)
        )
        story = self.font_manager.get("main", 23).render(
            "Kisah Leonhard berakhir. Kisah Leonardo dimulai sepuluh tahun kemudian.",
            True,
            (215, 211, 198),
        )
        prompt = self.font_manager.get("main", 17).render(
            "TEKAN ENTER UNTUK KEMBALI KE MENU UTAMA",
            True,
            (190, 164, 118),
        )

        self.screen.blit(title, title.get_rect(center=(self.screen_width // 2, self.screen_height // 2 - 80)))
        self.screen.blit(story, story.get_rect(center=(self.screen_width // 2, self.screen_height // 2)))
        self.screen.blit(prompt, prompt.get_rect(center=(self.screen_width // 2, self.screen_height // 2 + 90)))

    def start(self):
        while self.running:
            dt = self.set_fps(60)

            self.event_listener()
            self.update(dt)
            self.draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()
