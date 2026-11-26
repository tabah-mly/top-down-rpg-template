from functools import lru_cache
import random
import math

import pygame

from debug import DEBUG, PLAYER_MELEE_HITBOX_COLOR
from particle_effects import ParticleEffect


@lru_cache(maxsize=96)
def _crescent_perimeter_geometry(width, height):
    """Return a cached mask and its outline for the exact crescent drawn below.

    The geometry mirrors draw_cres(): an outer ellipse with a transparent
    ellipse cutout that extends beyond the lower edge of the attack surface.
    Sampling its mask outline places sparks on both the outer arc and the
    inner/front edge, rather than only behind the slash.
    """
    width = max(1, int(width))
    height = max(1, int(height))
    shape = pygame.Surface((width, 200), pygame.SRCALPHA)
    pygame.draw.ellipse(shape, (255, 255, 255, 255), (0, 0, width, height))
    pygame.draw.ellipse(shape, (0, 0, 0, 0), (0, width / 2, width, height))
    mask = pygame.mask.from_surface(shape)
    outline = tuple(mask.outline(every=1))
    return mask, outline


class Attack:
    def __init__(self, offset=(0, 8), particle_config=None, layer_config=None):
        self.color = (255, 255, 255)
        self.angle = 0
        self.offset = pygame.Vector2(offset)

        self.progress = 0
        self.duration = 0.15
        self.active = False

        # Attack properties. These remain the source of hit detection geometry.
        self.hit_radius = 60
        self.hit_range = 80

        # Attack position
        self.hit_pos = pygame.Vector2(0, 0)
        self.visual_pos = pygame.Vector2(0, 0)

        self.has_hit = False
        self.hit_targets = set()
        self.is_debug = DEBUG

        # Layered copies are visual only; the original white crescent remains
        # the opaque core and keeps exactly the same shape and dimensions.
        self.layer_config = layer_config or {}
        self.layers_enabled = bool(self.layer_config.get("enabled", True))

        # The old continuous melee particle stream is replaced by a short,
        # one-shot spark burst around the slash. No particles affect collision.
        self.particles = ParticleEffect(particle_config)
        self.spark_trigger_progress = max(
            0.0, min(1.0, float((particle_config or {}).get("trigger_progress", 0.48)))
        )
        spark_config = particle_config or {}
        self.spark_count = max(0, int(spark_config.get("count", 8)))
        self.spark_placement = str(
            spark_config.get("placement", "crescent_perimeter")
        ).lower()
        self.spark_edge_offset = max(0.0, float(spark_config.get("edge_offset", 2.0)))
        self.spark_position_jitter = max(
            0.0, float(spark_config.get("position_jitter", 4.0))
        )
        self.spark_normal_jitter = max(
            0.0, float(spark_config.get("normal_jitter", 2.0))
        )
        self.sparks_emitted = False

        # Kept for compatibility with the transient-state reset path.
        self.particle_timer = 0.0
        self.direction = pygame.Vector2(0, -1)

    def start(self, origin=None):
        self.progress = 0
        self.active = True
        self.has_hit = False
        self.hit_targets.clear()
        self.particle_timer = 0.0
        self.sparks_emitted = False

        if origin is None:
            surface = pygame.display.get_surface()
            origin = (surface.get_width() // 2, surface.get_height() // 2)

        origin = pygame.Vector2(origin)
        mx, my = pygame.mouse.get_pos()
        vec = pygame.Vector2(mx, my) - origin

        if vec.length_squared() == 0:
            vec = pygame.Vector2(0, -1)

        self.direction = vec.normalize()
        self.base_angle = vec.angle_to(pygame.Vector2(0, -1))

    def _current_visual_size(self):
        """Return the exact crescent size used by the current attack frame."""
        t = self.progress
        curve = (t**2) * (1 - t)
        base = 1.3 * ((1 - t) ** 2)
        raw_scale = base + curve * self.map_size()
        min_scale = 0.5
        scale = min_scale + raw_scale * (1 - min_scale)
        return (max(1, int(120 * scale)), max(1, int(160 * scale)))

    @staticmethod
    def _mask_outward_normal(mask, x, y, fallback):
        """Estimate a boundary's outward normal from the local mask gradient."""
        width, height = mask.get_size()

        def filled(px, py):
            if px < 0 or py < 0 or px >= width or py >= height:
                return 0
            return 1 if mask.get_at((px, py)) else 0

        # The negative occupancy gradient points from filled pixels into
        # transparent space. This also handles the concave/front edge.
        normal = pygame.Vector2(
            filled(x - 1, y) - filled(x + 1, y),
            filled(x, y - 1) - filled(x, y + 1),
        )
        if normal.length_squared() <= 0:
            normal = pygame.Vector2(fallback)
        if normal.length_squared() <= 0:
            normal = pygame.Vector2(0, -1)
        return normal.normalize()

    @staticmethod
    def _rotate_local_vector(vector, angle_degrees):
        """Rotate a surface-local vector like pygame.transform.rotate()."""
        radians = math.radians(angle_degrees)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        vector = pygame.Vector2(vector)
        return pygame.Vector2(
            vector.x * cosine + vector.y * sine,
            -vector.x * sine + vector.y * cosine,
        )

    def _outer_spark_scale(self):
        """Use the outermost enabled slash layer as the particle boundary."""
        scale = 1.0
        if not self.layers_enabled:
            return scale

        for name in ("outer", "middle"):
            layer = self.layer_config.get(name, {})
            if layer.get("enabled", True):
                scale = max(scale, float(layer.get("scale", 1.0)))
        return scale

    def _emit_melee_sparks(self):
        """Place a one-shot spark burst around the actual crescent perimeter."""
        if not self.particles.enabled or self.spark_count <= 0:
            return

        base_width, base_height = self._current_visual_size()
        outer_scale = self._outer_spark_scale()
        width = max(1, round(base_width * outer_scale))
        height = max(1, round(base_height * outer_scale))
        mask, outline = _crescent_perimeter_geometry(width, height)

        if not outline:
            return

        # Pick independent random anchors over the complete outline. Sampling
        # without replacement avoids identical points within one burst while
        # still allowing natural clusters instead of a perfectly spaced ring.
        count = min(self.spark_count, len(outline))
        sampled_points = random.sample(outline, count)
        center_local = pygame.Vector2(width / 2, 100)
        world_center = self.visual_pos - self.offset

        for point in sampled_points:
            px, py = int(point[0]), int(point[1])

            radial_fallback = pygame.Vector2(px, py) - center_local
            normal = self._mask_outward_normal(mask, px, py, radial_fallback)
            tangent = pygame.Vector2(-normal.y, normal.x)

            # Randomize both the position along the contour and its distance
            # from the contour. A few sparks can sit just inside/outside the
            # crescent, making the energy feel less mechanically uniform.
            tangent_jitter = random.uniform(
                -self.spark_position_jitter, self.spark_position_jitter
            )
            normal_jitter = random.uniform(
                -self.spark_normal_jitter, self.spark_normal_jitter
            )
            normal_offset = self.spark_edge_offset + normal_jitter
            local_point = (
                pygame.Vector2(px, py)
                + normal * normal_offset
                + tangent * tangent_jitter
            )

            local_delta = local_point - center_local
            world_position = world_center + self._rotate_local_vector(
                local_delta, self.base_angle
            )
            world_direction = self._rotate_local_vector(normal, self.base_angle)
            self.particles.emit(world_position, world_direction)

    def update(self, dt, player_pos):
        # Spark particles continue fading after the swing itself ends.
        self.particles.update(dt)

        if not self.active:
            return

        self.progress += dt / self.duration
        self.progress = min(self.progress, 1)

        # Calculate attack position in world coordinates.
        t = self.progress
        distance = self.hit_range * (1 - (1 - t) ** 2) - 60
        self.visual_pos = pygame.Vector2(player_pos) + self.direction * distance
        self.hit_pos = self.visual_pos + self.direction * 30

        # Only allow hits near the peak of the attack. Hit geometry is unchanged.
        self.has_hit = 0.2 < t < 0.8

        if not self.sparks_emitted and t >= self.spark_trigger_progress:
            self._emit_melee_sparks()
            self.sparks_emitted = True

        if self.progress >= 1:
            self.active = False
            self.has_hit = False

    def collides_with(self, target):
        if not self.active or not self.has_hit:
            return False

        if not target.can_be_damaged:
            return False

        if target in self.hit_targets:
            return False

        rect = target.hurtbox.rect
        closest_x = max(rect.left, min(self.hit_pos.x, rect.right))
        closest_y = max(rect.top, min(self.hit_pos.y, rect.bottom))
        dx = self.hit_pos.x - closest_x
        dy = self.hit_pos.y - closest_y

        if dx * dx + dy * dy <= self.hit_radius**2:
            self.hit_targets.add(target)
            return True

        return False

    def map_size(self):
        min_radius, max_radius = 40, 100
        self.hit_radius = max(min_radius, min(max_radius, self.hit_radius))
        return round(1 + (self.hit_radius - min_radius) / 4)

    def draw_cres(self, surface, t, pos=(0, 0), size=(100, 150), angle=0, color=None):
        w, h = size
        x, y = pygame.Vector2(pos) - self.offset
        attack_surface = pygame.Surface((w, 200), pygame.SRCALPHA)

        slash_color = self.color if color is None else color
        pygame.draw.ellipse(attack_surface, slash_color, (0, 0, w, h))
        pygame.draw.ellipse(attack_surface, (0, 255, 0, 0), (0, w / 2, w, h))

        rotated = pygame.transform.rotate(attack_surface, angle)
        rotated_rect = rotated.get_rect(center=(x, y))
        surface.blit(rotated, rotated_rect)

    @staticmethod
    def _layer_rgba(layer, default_color, default_opacity):
        color = layer.get("color", default_color)
        if not isinstance(color, (list, tuple)) or len(color) < 3:
            color = default_color
        rgb = tuple(max(0, min(255, int(channel))) for channel in color[:3])
        opacity = max(0.0, min(1.0, float(layer.get("opacity", default_opacity))))
        return (*rgb, round(255 * opacity))

    def _draw_melee_layers(self, surface, t, screen_pos, size):
        if not self.layers_enabled:
            return

        # Draw the broadest and faintest aura first, then the tighter highlight.
        outer = self.layer_config.get("outer", {})
        if outer.get("enabled", True):
            scale = max(1.0, float(outer.get("scale", 1.24)))
            outer_size = (max(1, round(size[0] * scale)), max(1, round(size[1] * scale)))
            color = self._layer_rgba(outer, (232, 202, 137), 0.25)
            self.draw_cres(surface, t, screen_pos, size=outer_size, angle=self.base_angle, color=color)

        middle = self.layer_config.get("middle", {})
        if middle.get("enabled", True):
            scale = max(1.0, float(middle.get("scale", 1.12)))
            middle_size = (max(1, round(size[0] * scale)), max(1, round(size[1] * scale)))
            color = self._layer_rgba(middle, (216, 232, 246), 0.40)
            self.draw_cres(surface, t, screen_pos, size=middle_size, angle=self.base_angle, color=color)

    def draw(self, surface, camera, player_pos):
        if self.active:
            t = self.progress
            size = self._current_visual_size()

            # Preserve the original white crescent as the solid center layer.
            screen_pos = self.visual_pos - camera.offset
            self._draw_melee_layers(surface, t, screen_pos, size)
            self.draw_cres(surface, t, screen_pos, size=size, angle=self.base_angle)

            if self.is_debug and self.has_hit:
                debug_pos = self.hit_pos - camera.offset
                center = (round(debug_pos.x), round(debug_pos.y))
                pygame.draw.circle(surface, PLAYER_MELEE_HITBOX_COLOR, center, self.hit_radius, 2)
                pygame.draw.line(
                    surface, PLAYER_MELEE_HITBOX_COLOR,
                    (center[0] - 7, center[1]), (center[0] + 7, center[1]), 1
                )
                pygame.draw.line(
                    surface, PLAYER_MELEE_HITBOX_COLOR,
                    (center[0], center[1] - 7), (center[0], center[1] + 7), 1
                )

        # Sparks draw over the slash but remain entirely visual-only.
        self.particles.draw(surface, camera.offset)
