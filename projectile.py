import pygame


class Projectile:
    def __init__(self, pos, direction, player_speed, speed=500, max_range=250):
        self.pos = pygame.Vector2(pos)

        dir_vec = pygame.Vector2(direction)

        if dir_vec.length_squared() == 0:
            dir_vec = pygame.Vector2(1, 0)

        self.dir = dir_vec.normalize()

        self.speed = speed + player_speed
        self.radius = 6

        self.alive = True
        self.distance_travelled = 0
        self.max_range = max_range

    def update(self, dt):
        if not self.alive:
            return

        remaining_range = self.max_range - self.distance_travelled
        movement = self.dir * min(self.speed * dt, remaining_range)

        self.pos += movement
        self.distance_travelled += movement.length()

        if self.distance_travelled >= self.max_range:
            self.alive = False

    def collides_with(self, target):
        if not self.alive:
            return False

        if not target.can_be_damaged:
            return False

        rect = target.hurtbox.rect

        closest_x = max(rect.left, min(self.pos.x, rect.right))
        closest_y = max(rect.top, min(self.pos.y, rect.bottom))

        dx = self.pos.x - closest_x
        dy = self.pos.y - closest_y

        return dx * dx + dy * dy <= self.radius**2

    def draw(self, surface, camera):
        screen_pos = self.pos - camera.offset

        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (round(screen_pos.x), round(screen_pos.y)),
            self.radius,
        )

        # Debug collision radius
        pygame.draw.circle(
            surface,
            (255, 0, 0),
            (round(screen_pos.x), round(screen_pos.y)),
            self.radius,
            1,
        )
