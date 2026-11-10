import pygame
from spritesheet import SpriteSheet


class Player:
    def __init__(self, x, y, pointer):
        self.animations = {
            "idle_down": SpriteSheet(
                "assets/imgs/sprites/leonardo/idle_down.png", 20, 26, 3, 0.1
            ),
            "walk_down": SpriteSheet(
                "assets/imgs/sprites/leonardo/walk_down.png", 20, 26, 3, 0.1
            ),
            "idle_up": SpriteSheet(
                "assets/imgs/sprites/leonardo/idle_up.png", 20, 26, 3, 0.1
            ),
            "walk_up": SpriteSheet(
                "assets/imgs/sprites/leonardo/walk_up.png", 20, 26, 3, 0.1
            ),
            "idle_left": SpriteSheet(
                "assets/imgs/sprites/leonardo/idle_left.png", 20, 26, 3, 0.1
            ),
            "walk_left": SpriteSheet(
                "assets/imgs/sprites/leonardo/walk_left.png", 20, 26, 3, 0.1
            ),
            "idle_right": SpriteSheet(
                "assets/imgs/sprites/leonardo/idle_right.png", 20, 26, 3, 0.1
            ),
            "walk_right": SpriteSheet(
                "assets/imgs/sprites/leonardo/walk_right.png", 20, 26, 3, 0.1
            ),
        }

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

        self.pointer = pointer

        self.aiming = False

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        self.aiming = pygame.mouse.get_pressed()[0]

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

    def draw(self, surface, camera):
        self.draw_sprites(surface, camera)

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
            self.pos += direction * self.stats["speed"] * dt
            self.rect.center = self.pos

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
