import pygame

from debug import DEBUG, PROJECTILE_HITBOX_COLOR
from particle_effects import ParticleEffect


class Projectile:
    def __init__(self, pos, direction, player_speed, speed=500, max_range=250, trail_config=None):
        self.pos = pygame.Vector2(pos)

        dir_vec = pygame.Vector2(direction)

        if dir_vec.length_squared() == 0:
            dir_vec = pygame.Vector2(1, 0)

        self.dir = dir_vec.normalize()

        self.speed = speed + player_speed
        self.radius = 6
        self.debug = DEBUG

        self.alive = True
        self.distance_travelled = 0
        self.max_range = max_range

        # A visual-only tail. It persists briefly after the projectile expires
        # or hits something so the trail does not disappear abruptly.
        self.trail = ParticleEffect(trail_config)
        self.trail_timer = 0.0

    def update(self, dt):
        dt = max(0.0, float(dt))
        self.trail.update(dt)

        if not self.alive:
            return

        old_pos = self.pos.copy()
        remaining_range = self.max_range - self.distance_travelled
        movement = self.dir * min(self.speed * dt, remaining_range)
        self.pos += movement
        self.distance_travelled += movement.length()

        if self.trail.enabled and movement.length_squared() > 0:
            self.trail_timer += dt
            interval = self.trail.spawn_interval
            while self.trail_timer >= interval:
                self.trail_timer -= interval
                # Interpolate emission along this frame's movement so the tail
                # remains continuous even when frame time varies slightly.
                fraction = min(1.0, max(0.0, 1.0 - self.trail_timer / max(dt, 0.0001)))
                trail_pos = old_pos.lerp(self.pos, fraction) - self.dir * (self.radius * 0.4)
                self.trail.emit(trail_pos, -self.dir)

        if self.distance_travelled >= self.max_range:
            self.alive = False

    @property
    def has_trail(self):
        return self.trail.has_particles

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
        # Draw the fading tail first so the projectile remains visually crisp.
        self.trail.draw(surface, camera.offset)

        if not self.alive:
            return

        screen_pos = self.pos - camera.offset
        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (round(screen_pos.x), round(screen_pos.y)),
            self.radius,
        )

        # The outline is the exact circular radius used by collides_with().
        if self.debug:
            pygame.draw.circle(
                surface,
                PROJECTILE_HITBOX_COLOR,
                (round(screen_pos.x), round(screen_pos.y)),
                self.radius,
                2,
            )
