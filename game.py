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
        self.player = None

        self.debug_collisions = True

    # ========================================================
    # GAME STATE
    # ========================================================

    def start_new_game(self):
        """Initialize a fresh game world."""

        self.tilemap = TiledMap(
            "assets/maps/level0.tmx",
            scale=2,
        )

        self.triggers = self.tilemap.load_triggers()
        self.collisions = self.tilemap.load_collisions()
        self.npcs = self.tilemap.load_npcs()

        self.camera.set_bounds(
            self.tilemap.width,
            self.tilemap.height,
        )

        spawn_position = self.tilemap.get_spawn("PlayerSpawn")

        self.player = Player(
            spawn_position.x,
            spawn_position.y,
            self.pointer,
        )

        self.player.set_bounds(
            self.tilemap.width,
            self.tilemap.height,
        )

        self.player.set_collisions(self.collisions)
        self.player.set_npcs(self.npcs)

        for npc in self.npcs:
            npc.set_player(self.player)

        self.dialog.active = False
        self.active_dialogue_context = None

        self.quest_manager.reset()
        self.story_state.reset()
        self.dialogue_manager.seen_dialogues.clear()

        self.quest_manager.start_quest("survive_the_forest")
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

        self.camera.set_bounds(
            new_map.width,
            new_map.height,
        )

        self.player.pos = pygame.Vector2(
            spawn.x * new_map.scale,
            spawn.y * new_map.scale,
        )

        self.player.rect.center = self.player.pos

        self.player.set_bounds(
            new_map.width,
            new_map.height,
        )

        self.player.set_collisions(self.collisions)
        self.player.set_npcs(self.npcs)

        for npc in self.npcs:
            npc.set_player(self.player)

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

    def handle_game_event(self, event):
        if event.type == pygame.KEYDOWN:

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

        if self.dialog.active:
            return

        self.player.update(dt, self.camera)
        self.camera.follow(self.player.rect)

        for npc in self.npcs:
            npc.update(dt)

        for trigger in self.triggers:
            if trigger.update(self.player.body_collider.rect):

                # Notify the quest system
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

    def draw_gameplay(self):
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

        self.player.draw(self.screen, self.camera)

        player_screen_pos = self.camera.apply(self.player.rect).center

        self.pointer.draw(
            self.screen,
            player_screen_pos,
        )

        for trigger in self.triggers:
            trigger.draw_debug(
                self.screen,
                self.camera,
            )

        self.dialog.draw(self.screen)

        # Collision debug
        for collision in self.collisions:
            collision.draw_debug(
                self.screen,
                self.camera,
            )

        if self.debug_collisions:
            self.player.draw_collision_debug(
                self.screen,
                self.camera,
            )

            for npc in self.npcs:
                npc.draw_collision_debug(
                    self.screen,
                    self.camera,
                )

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
