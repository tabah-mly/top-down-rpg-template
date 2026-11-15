import pygame


class Attack:
    def __init__(self, offset=(0, 8)):
        self.color = (255, 255, 255)
        self.angle = 0
        self.offset = pygame.Vector2(offset)

        self.progress = 0
        self.duration = 0.15
        self.active = False

        # Attack properties
        self.hit_radius = 60
        self.hit_range = 80

        # Attack position
        self.hit_pos = pygame.Vector2(0, 0)
        self.visual_pos = pygame.Vector2(0, 0)

        self.has_hit = False
        self.hit_targets = set()

        self.is_debug = False

    def start(self):
        self.progress = 0
        self.active = True
        self.has_hit = False
        self.hit_targets.clear()

        surface = pygame.display.get_surface()
        center = pygame.Vector2(surface.get_width() // 2, surface.get_height() // 2)

        mx, my = pygame.mouse.get_pos()
        vec = pygame.Vector2(mx, my) - center

        if vec.length_squared() == 0:
            vec = pygame.Vector2(0, -1)

        self.direction = vec.normalize()
        self.base_angle = vec.angle_to(pygame.Vector2(0, -1))

    def update(self, dt, player_pos):
        if not self.active:
            return

        self.progress += dt / self.duration
        self.progress = min(self.progress, 1)

        # Calculate attack position in world coordinates
        t = self.progress

        distance = self.hit_range * (1 - (1 - t) ** 2) - 60

        self.visual_pos = pygame.Vector2(player_pos) + self.direction * distance

        self.hit_pos = self.visual_pos + self.direction * 60

        # Only allow hits near the peak of the attack
        self.has_hit = 0.2 < t < 0.8

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

    def draw_cres(self, surface, t, pos=(0, 0), size=(100, 150), angle=0):
        w, h = size
        x, y = pygame.Vector2(pos) - self.offset

        attack_surface = pygame.Surface((w, 200), pygame.SRCALPHA)

        pygame.draw.ellipse(attack_surface, self.color, (0, 0, w, h))

        pygame.draw.ellipse(attack_surface, (0, 255, 0, 0), (0, w / 2, w, h))

        rotated = pygame.transform.rotate(attack_surface, angle)
        rotated_rect = rotated.get_rect(center=(x, y))

        surface.blit(rotated, rotated_rect)

    def draw(self, surface, camera, player_pos):
        if not self.active:
            return

        t = self.progress

        curve = (t**2) * (1 - t)
        base = 1.3 * ((1 - t) ** 2)

        raw_scale = base + curve * self.map_size()

        min_scale = 0.5
        scale = min_scale + raw_scale * (1 - min_scale)

        size = (int(120 * scale), int(160 * scale))

        # Use the position calculated by update()
        screen_pos = self.visual_pos - camera.offset

        self.draw_cres(surface, t, screen_pos, size=size, angle=self.base_angle)

        if self.is_debug:
            debug_pos = self.hit_pos - camera.offset

            pygame.draw.circle(
                surface,
                (255, 0, 0),
                (round(debug_pos.x), round(debug_pos.y)),
                self.hit_radius,
                2,
            )
