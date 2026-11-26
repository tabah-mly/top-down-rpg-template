"""Small, visual-only pixel particles used by Leonhard's attacks."""

from functools import lru_cache
import math
import random

import pygame


@lru_cache(maxsize=512)
def _particle_sprite(color, diameter, alpha):
    """Return a cached, pixel-crisp diamond particle sprite."""
    diameter = max(2, int(diameter))
    alpha = max(0, min(255, int(alpha)))
    sprite = pygame.Surface((diameter + 2, diameter + 2), pygame.SRCALPHA)
    center = (diameter + 2) // 2
    radius = max(1, diameter // 2)
    points = [
        (center, center - radius),
        (center + radius, center),
        (center, center + radius),
        (center - radius, center),
    ]
    pygame.draw.polygon(sprite, (*color, alpha), points)

    # A tiny bright core makes larger particles read as light, not debris.
    if diameter >= 4:
        core_alpha = min(255, alpha + 25)
        sprite.set_at((center, center), (255, 252, 238, core_alpha))
    return sprite


class Particle:
    def __init__(self, position, velocity, color, size, lifetime, drag=5.5):
        self.pos = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.color = tuple(int(max(0, min(255, channel))) for channel in color[:3])
        self.size = max(0.5, float(size))
        self.lifetime = max(0.01, float(lifetime))
        self.age = 0.0
        self.drag = max(0.0, float(drag))

    @property
    def alive(self):
        return self.age < self.lifetime

    def update(self, dt):
        if not self.alive:
            return
        dt = max(0.0, float(dt))
        self.age += dt
        self.pos += self.velocity * dt
        if self.drag:
            self.velocity *= math.exp(-self.drag * dt)

    def draw(self, surface, camera_offset):
        if not self.alive:
            return

        remaining = max(0.0, 1.0 - self.age / self.lifetime)
        # Smoothly fade and shrink while preserving a crisp pixel shape.
        alpha = int(255 * remaining * remaining)
        diameter = max(2, int(round(self.size * (0.45 + 0.55 * remaining) * 2)))
        sprite = _particle_sprite(self.color, diameter, alpha)
        screen_pos = self.pos - camera_offset
        rect = sprite.get_rect(center=(round(screen_pos.x), round(screen_pos.y)))
        surface.blit(sprite, rect)


class ParticleEffect:
    """Configurable particle emitter with a hard per-effect particle limit."""

    def __init__(self, config=None):
        config = config or {}
        self.enabled = bool(config.get("enabled", False))
        self.spawn_interval = max(0.005, float(config.get("spawn_interval", 0.03)))
        self.particles_per_spawn = max(1, int(config.get("particles_per_spawn", 1)))
        self.lifetime_range = self._read_range(config.get("lifetime"), (0.12, 0.24))
        self.size_range = self._read_range(config.get("size"), (1.0, 2.5))
        self.speed_range = self._read_range(config.get("speed"), (20.0, 60.0))
        self.spread_degrees = max(0.0, min(360.0, float(config.get("spread_degrees", 140))))
        self.drag = max(0.0, float(config.get("drag", 6.0)))
        self.max_particles = max(1, int(config.get("max_particles", 40)))

        configured_colors = config.get("colors", [
            [255, 250, 232],
            [232, 202, 137],
            [216, 232, 246],
        ])
        self.colors = []
        if isinstance(configured_colors, list):
            for color in configured_colors:
                if isinstance(color, (list, tuple)) and len(color) >= 3:
                    self.colors.append(tuple(int(c) for c in color[:3]))
        if not self.colors:
            self.colors = [(255, 250, 232), (232, 202, 137)]

        self.particles = []
        self.accumulator = 0.0

    @staticmethod
    def _read_range(value, default):
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            value = default
        low, high = float(value[0]), float(value[1])
        return (min(low, high), max(low, high))

    def emit(self, position, direction=None):
        if not self.enabled:
            return

        position = pygame.Vector2(position)
        base_angle = None
        if direction is not None:
            direction = pygame.Vector2(direction)
            if direction.length_squared() > 0:
                base_angle = math.atan2(direction.y, direction.x)

        for _ in range(self.particles_per_spawn):
            if base_angle is None or self.spread_degrees >= 359.0:
                angle = random.uniform(0.0, math.tau)
            else:
                spread = math.radians(self.spread_degrees) * 0.5
                angle = base_angle + random.uniform(-spread, spread)

            speed = random.uniform(*self.speed_range)
            velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
            particle = Particle(
                position=position,
                velocity=velocity,
                color=random.choice(self.colors),
                size=random.uniform(*self.size_range),
                lifetime=random.uniform(*self.lifetime_range),
                drag=self.drag,
            )
            self.particles.append(particle)

        overflow = len(self.particles) - self.max_particles
        if overflow > 0:
            del self.particles[:overflow]

    def update(self, dt):
        for particle in self.particles:
            particle.update(dt)
        self.particles = [particle for particle in self.particles if particle.alive]

    def draw(self, surface, camera_offset):
        if not self.particles:
            return
        for particle in self.particles:
            particle.draw(surface, camera_offset)

    def clear(self):
        self.particles.clear()
        self.accumulator = 0.0

    @property
    def has_particles(self):
        return bool(self.particles)
