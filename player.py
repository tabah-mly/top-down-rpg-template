import pygame
from animated_sprite import AnimatedSprite
from spritesheet import SpriteSheet
from collision import CollisionBox
from projectile import Projectile
from attack import Attack
from debug import DEBUG, BODY_COLLISION_COLOR, HURTBOX_COLOR


class Player:
    def __init__(self, x, y, pointer, character="leonardo", config=None):
        """Create a player from a profile loaded by EntityDatabase.

        ``character`` remains as a fallback sprite-folder name for compatibility,
        while the JSON profile is the source of truth for configurable values.
        """
        self.config = config or {}
        self.character = self.config.get("sprite", character)
        self.animations = {}

        frame_width = int(self.config.get("frame_width", 20))
        frame_height = int(self.config.get("frame_height", 26))
        sprite_scale = int(self.config.get("sprite_scale", 3))
        animation_speed = float(self.config.get("animation_speed", 0.1))

        directions = ["up", "down", "left", "right"]
        states = ["idle", "walk"]

        for state in states:
            for direction in directions:
                key = f"{state}_{direction}"
                frames = SpriteSheet(
                    f"assets/imgs/sprites/{self.character}/{key}.png",
                    frame_width,
                    frame_height,
                    scale=sprite_scale,
                ).frames
                self.animations[key] = AnimatedSprite(frames, speed=animation_speed)

        default_stats = {
            "max_hp": 100,
            "hp": 100,
            "speed": 250,
            "damage": 20,
            "knockback": 20,
            "stun": 0,
        }
        self.stats = {**default_stats, **self.config.get("stats", {})}
        self.stats["max_hp"] = max(1, int(self.stats["max_hp"]))
        self.stats["hp"] = max(0, min(self.stats["max_hp"], int(self.stats["hp"])))
        self.stats["speed"] = float(self.stats["speed"])
        self.stats["damage"] = float(self.stats["damage"])

        self.invulnerability_timer = 0.0
        self.invulnerability_duration = max(
            0.0, float(self.config.get("invulnerability_duration", 0.65))
        )

        self.state = "idle"
        self.facing = "down"
        self.animator = self.animations[f"{self.state}_{self.facing}"]
        self.pos = pygame.Vector2(x, y)
        self.rect = self.animator.image.get_rect(center=(x, y))

        # Physical collision and damage-receiving areas come from the player profile.
        body_config = self.config.get("body_collider", {})
        hurtbox_config = self.config.get("hurtbox", {})
        self.body_collider = CollisionBox(
            width=int(body_config.get("width", 24)),
            height=int(body_config.get("height", 16)),
            offset=body_config.get("offset", (0, 25)),
        )
        self.hurtbox = CollisionBox(
            width=int(hurtbox_config.get("width", 30)),
            height=int(hurtbox_config.get("height", 42)),
            offset=hurtbox_config.get("offset", (0, 10)),
        )

        self.update_collision_boxes()

        self.pointer = pointer

        self.aiming = False
        self.bounds = None

        self.collisions = []
        self.npcs = []
        self.enemies = []

        self.is_attack = False
        self.attack_timer = 0
        attack_config = self.config.get("attack", {})
        self.attack_duration = max(0.01, float(attack_config.get("duration", 0.15)))

        self.prev_mouse_left = False
        self.prev_mouse_right = False

        self.projectiles = []
        self.attack = Attack(offset=attack_config.get("offset", (0, 8)))
        self.attack.duration = max(0.01, float(attack_config.get("duration", 0.15)))
        self.attack.hit_radius = max(1, int(attack_config.get("hit_radius", 60)))
        self.attack.hit_range = float(attack_config.get("hit_range", 80))
        self.attack.is_debug = DEBUG

        self.can_attack = True

    def set_npcs(self, npcs):
        self.npcs = npcs

    def set_enemies(self, enemies):
        self.enemies = enemies

    def reset_transient_combat_state(self):
        """Clear attack/input state before leaving or entering a scene."""
        # An attack can be interrupted when gameplay pauses for a cinematic.
        # Cancel it so the old swing does not resume on the next map.
        self.attack.active = False
        self.attack.progress = 0
        self.attack.has_hit = False
        self.attack.hit_targets.clear()

        # Do not carry projectiles into another scene or map.
        self.projectiles.clear()

        # Synchronize the edge detector with the current mouse state. If a
        # button is held during a transition, it must be released and pressed
        # again before it can trigger an attack or toggle attack mode.
        mouse = pygame.mouse.get_pressed()
        self.prev_mouse_left = bool(mouse[0])
        self.prev_mouse_right = bool(mouse[2])
        self.aiming = False

    def set_collisions(self, collisions):
        self.collisions = collisions

    def is_colliding(self):
        # Check map obstacles
        map_collision = any(
            collision.collides(self.body_collider.rect) for collision in self.collisions
        )

        if map_collision:
            return True

        # Check NPC body colliders
        npc_collision = any(
            npc.body_collider.rect.colliderect(self.body_collider.rect)
            for npc in self.npcs
        )

        if npc_collision:
            return True

        enemy_collision = any(
            enemy.alive and enemy.body_collider.rect.colliderect(self.body_collider.rect)
            for enemy in self.enemies
        )

        return enemy_collision

    def set_bounds(self, width, height):
        self.bounds = pygame.Rect(0, 0, width, height)

    def handle_input(self, dt, camera):
        keys = pygame.key.get_pressed()
        self.aiming = pygame.mouse.get_pressed()[0]
        self.mouse_handler(camera)

        direction = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w],
        )
        self.move(direction, dt)

    def update(self, dt, camera):
        self.invulnerability_timer = max(0.0, self.invulnerability_timer - dt)
        self.handle_input(dt, camera)

        if self.aiming:
            self.update_facing_mouse(camera)

        self.animator.update(dt)
        self.update_projectiles(dt)

        self.attack.update(dt, self.pos)
        self.check_attack_collisions()

    def draw(self, surface, camera):
        self.draw_sprites(surface, camera)
        self.draw_attack(surface, camera)

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.update_animation()

    def set_facing(self, facing):
        if facing != self.facing:
            self.facing = facing
            self.update_animation()

    def update_animation(self):
        animation_key = f"{self.state}_{self.facing}"
        if self.animator != self.animations[animation_key]:
            self.animator = self.animations[animation_key]
            self.animator.reset()

    def move(self, direction, dt):
        if direction.length_squared() > 0:
            direction = direction.normalize()

            movement = direction * self.stats["speed"] * dt

            # --------------------------------
            # Horizontal movement
            # --------------------------------
            old_x = self.pos.x
            self.pos.x += movement.x

            if self.bounds:
                # half_width = self.rect.width / 2
                # self.pos.x = max(
                #     half_width, min(self.pos.x, self.bounds.width - half_width)
                # )
                half_width = self.body_collider.width / 2
                offset_x = self.body_collider.offset.x

                self.pos.x = max(
                    half_width - offset_x,
                    min(self.pos.x, self.bounds.width - half_width - offset_x),
                )

            self.rect.center = self.pos
            self.update_collision_boxes()

            if self.is_colliding():
                self.pos.x = old_x
                self.rect.center = self.pos
                self.update_collision_boxes()

            # --------------------------------
            # Vertical movement
            # --------------------------------
            old_y = self.pos.y
            self.pos.y += movement.y

            if self.bounds:
                # half_height = self.rect.height / 2
                # self.pos.y = max(
                #     half_height, min(self.pos.y, self.bounds.height - half_height)
                # )
                half_height = self.body_collider.height / 2
                offset_y = self.body_collider.offset.y

                self.pos.y = max(
                    half_height - offset_y,
                    min(self.pos.y, self.bounds.height - half_height - offset_y),
                )

            self.rect.center = self.pos
            self.update_collision_boxes()

            if self.is_colliding():
                self.pos.y = old_y
                self.rect.center = self.pos
                self.update_collision_boxes()

            # --------------------------------
            # Animation and facing
            # --------------------------------
            if not self.aiming:
                if abs(direction.x) > abs(direction.y):
                    self.set_facing("right" if direction.x > 0 else "left")
                else:
                    self.set_facing("down" if direction.y > 0 else "up")

            self.set_state("walk")

        else:
            self.set_state("idle")

    def update_facing_mouse(self, camera):
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        player_screen_pos = pygame.Vector2(camera.apply(self.rect).center)
        direction = mouse_pos - player_screen_pos

        if direction.length_squared() == 0:
            return
        if abs(direction.x) > abs(direction.y):
            self.set_facing("right" if direction.x > 0 else "left")
        else:
            self.set_facing("down" if direction.y > 0 else "up")

    def draw_sprites(self, surface, camera):
        image = self.animator.image
        player_rect = camera.apply(self.rect)
        surface.blit(image, player_rect)

    def update_collision_boxes(self):
        self.body_collider.update(self.pos)
        self.hurtbox.update(self.pos)

    def draw_collision_debug(self, surface, camera):
        self.body_collider.draw_debug(surface, camera, BODY_COLLISION_COLOR)
        self.hurtbox.draw_debug(surface, camera, HURTBOX_COLOR)

    def take_damage(self, amount):
        if self.invulnerability_timer > 0 or self.stats["hp"] <= 0:
            return False

        self.stats["hp"] = max(0, self.stats["hp"] - int(amount))
        self.invulnerability_timer = self.invulnerability_duration
        print(f"Leonhard took {amount} damage. HP: {self.stats['hp']}/{self.stats['max_hp']}")
        return True

    def mouse_handler(self, camera):
        mouse = pygame.mouse.get_pressed()

        # Change attack type
        if mouse[2] and not self.prev_mouse_right:
            self.pointer.ranged = not self.pointer.ranged

        self.prev_mouse_right = mouse[2]

        # Attack only when permitted
        if mouse[0] and not self.prev_mouse_left and self.can_attack:

            if self.pointer.ranged:
                if self.pointer.direction.length_squared() > 0:
                    projectile = Projectile(
                        self.pos, self.pointer.direction, self.stats["speed"]
                    )
                    self.projectiles.append(projectile)

            else:
                player_screen_pos = camera.apply(self.rect).center
                self.attack.start(player_screen_pos)

        self.prev_mouse_left = mouse[0]

        self.projectiles = [p for p in self.projectiles if p.alive]

    def update_projectiles(self, dt):
        for projectile in self.projectiles:
            projectile.update(dt)

            if not projectile.alive:
                continue

            for enemy in self.enemies:
                if projectile.collides_with(enemy):
                    enemy.take_damage(self.stats["damage"], source_position=self.pos)
                    projectile.alive = False
                    break

            if not projectile.alive:
                continue

            for npc in self.npcs:
                if projectile.collides_with(npc):
                    print(f"Projectile hit NPC: {npc.name}")
                    projectile.alive = False
                    break

        # Remove expired or hit projectiles
        self.projectiles = [
            projectile for projectile in self.projectiles if projectile.alive
        ]

    def draw_attack(self, surface, camera):
        for projectile in self.projectiles:
            projectile.draw(surface, camera)

        self.attack.draw(surface, camera, self.pos)

    def check_attack_collisions(self):
        for enemy in self.enemies:
            if self.attack.collides_with(enemy):
                enemy.take_damage(self.stats["damage"], source_position=self.pos)

        for npc in self.npcs:
            if self.attack.collides_with(npc):
                print(f"Hit NPC: {npc.name}")
