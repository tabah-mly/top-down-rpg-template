import pygame
from animated_sprite import AnimatedSprite
from spritesheet import SpriteSheet
from collision import CollisionBox
from projectile import Projectile
from attack import Attack


class Player:
    def __init__(self, x, y, pointer):
        self.animations = {}

        directions = ["up", "down", "left", "right"]
        states = ["idle", "walk"]

        for state in states:
            for direction in directions:
                key = f"{state}_{direction}"
                frames = SpriteSheet(
                    f"assets/imgs/sprites/leonardo/{key}.png", 20, 26, scale=3
                ).frames
                self.animations[key] = AnimatedSprite(frames, speed=0.1)

        self.stats = {
            "max_hp": 100,
            "hp": 100,
            "speed": 250,
            "damage": 20,
            "knockback": 20,
            "stun": 0,
        }

        self.state = "idle"
        self.facing = "down"
        self.animator = self.animations[f"{self.state}_{self.facing}"]
        self.pos = pygame.Vector2(x, y)
        self.rect = self.animator.image.get_rect(center=(x, y))

        # Physical collision area
        self.body_collider = CollisionBox(width=24, height=16, offset=(0, 25))

        # Area that can receive damage
        self.hurtbox = CollisionBox(width=30, height=42, offset=(0, 10))

        self.update_collision_boxes()

        self.pointer = pointer

        self.aiming = False
        self.bounds = None

        self.collisions = []
        self.npcs = []

        self.is_attack = False
        self.attack_timer = 0
        self.attack_duration = 0.15

        self.prev_mouse_left = False
        self.prev_mouse_right = False

        self.projectiles = []
        self.attack = Attack()
        self.attack.is_debug = True

        self.can_attack = True

    def set_npcs(self, npcs):
        self.npcs = npcs

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

        return npc_collision

    def set_bounds(self, width, height):
        self.bounds = pygame.Rect(0, 0, width, height)

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        self.aiming = pygame.mouse.get_pressed()[0]
        self.mouse_handler()

        direction = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w],
        )
        self.move(direction, dt)

    def update(self, dt, camera):
        self.handle_input(dt)

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
        self.body_collider.draw_debug(surface, camera, (0, 255, 0))

        self.hurtbox.draw_debug(surface, camera, (255, 0, 255))

    def mouse_handler(self):
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
                self.attack.start()

        self.prev_mouse_left = mouse[0]

        self.projectiles = [p for p in self.projectiles if p.alive]

    def update_projectiles(self, dt):
        for projectile in self.projectiles:
            projectile.update(dt)

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
        for npc in self.npcs:
            if self.attack.collides_with(npc):
                print(f"Hit NPC: {npc.name}")
